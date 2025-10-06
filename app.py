"""
FastAPI + Hugging Face + Redis + RQ
-----------------------------------
Text Intelligence API — supports:
- Summarization
- Question Answering
- Tone Rewriting (Formal / Informal)
"""

import os
import hashlib
import uuid
from typing import Optional, Literal
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from transformers import pipeline
import redis
from rq import Queue

# ===== Configuration =====
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 1 day

redis_conn = redis.from_url(REDIS_URL)
queue = Queue("genai", connection=redis_conn)

# ===== Pipeline Cache =====
_pipelines = {}

def get_pipeline(task: str):
    """Lazy-load model based on task type"""
    if task not in _pipelines:
        if task == "summarization":
            _pipelines[task] = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
        elif task == "qa":
            _pipelines[task] = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
        elif task == "rewrite":
            _pipelines[task] = pipeline("text2text-generation", model="google/flan-t5-small")
        else:
            raise ValueError(f"Unsupported task: {task}")
    return _pipelines[task]

# ===== Helpers =====
def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def cache_key_for_input(text: str, task: str, extra: str = "") -> str:
    return f"cache:{task}:{extra}:{sha256_text(text)}"

# ===== FastAPI =====
app = FastAPI(title="Text Intelligence API", version="2.0")

# ===== Models =====
class SummarizeRequest(BaseModel):
    text: str
    max_length: Optional[int] = 150
    min_length: Optional[int] = 25

class QARequest(BaseModel):
    context: str
    question: str

class RewriteRequest(BaseModel):
    text: str
    tone: Literal["formal", "informal"]

class SubmitResponse(BaseModel):
    job_id: str
    status: str

# ===== Core Functions =====
def summarize_text(text: str, max_length: int, min_length: int):
    pipe = get_pipeline("summarization")
    res = pipe(text, max_length=max_length, min_length=min_length, truncation=True)
    return res[0]["summary_text"].strip()

def answer_question(context: str, question: str):
    pipe = get_pipeline("qa")
    res = pipe(question=question, context=context)
    return res["answer"]

def rewrite_tone(text: str, tone: str):
    pipe = get_pipeline("rewrite")
    prompt = f"Rewrite the following text in a {tone} tone:\n{text}"
    res = pipe(prompt, max_length=200)
    return res[0]["generated_text"].strip()

# ===== Synchronous Endpoints =====
@app.post("/summarize")
def summarize(req: SummarizeRequest):
    key = cache_key_for_input(req.text, "summarize")
    cached = redis_conn.get(key)
    if cached:
        return JSONResponse({"task": "summarization", "cached": True, "result": cached.decode("utf-8")})
    result = summarize_text(req.text, req.max_length, req.min_length)
    redis_conn.setex(key, CACHE_TTL, result)
    return {"task": "summarization", "cached": False, "result": result}

@app.post("/qa")
def qa(req: QARequest):
    combined_text = req.context + req.question
    key = cache_key_for_input(combined_text, "qa")
    cached = redis_conn.get(key)
    if cached:
        return JSONResponse({"task": "qa", "cached": True, "result": cached.decode("utf-8")})
    result = answer_question(req.context, req.question)
    redis_conn.setex(key, CACHE_TTL, result)
    return {"task": "qa", "cached": False, "result": result}

@app.post("/rewrite")
def rewrite(req: RewriteRequest):
    key = cache_key_for_input(req.text, "rewrite", req.tone)
    cached = redis_conn.get(key)
    if cached:
        return JSONResponse({"task": "rewrite", "cached": True, "result": cached.decode("utf-8")})
    result = rewrite_tone(req.text, req.tone)
    redis_conn.setex(key, CACHE_TTL, result)
    return {"task": "rewrite", "cached": False, "result": result}

# ===== Async Job Processor =====
def process_genai_task(task_type: str, payload: dict):
    """Executed by RQ worker"""
    if task_type == "summarize":
        return summarize_text(payload["text"], payload["max_length"], payload["min_length"])
    elif task_type == "qa":
        return answer_question(payload["context"], payload["question"])
    elif task_type == "rewrite":
        return rewrite_tone(payload["text"], payload["tone"])
    else:
        raise ValueError(f"Unknown task type: {task_type}")

# ===== Async Endpoints =====
@app.post("/submit/{task_type}", response_model=SubmitResponse)
def submit_job(task_type: Literal["summarize", "qa", "rewrite"], payload: dict):
    job = queue.enqueue(process_genai_task, task_type, payload)
    redis_conn.setex(f"job:{job.id}:status", 3600, "queued")
    return SubmitResponse(job_id=str(job.id), status="queued")

@app.get("/status/{job_id}")
def job_status(job_id: str):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return {"job_id": job_id, "status": "unknown"}
    return {"job_id": job_id, "status": job.get_status()}

@app.get("/result/{job_id}")
def job_result(job_id: str):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get_status() == "finished":
        return {"job_id": job_id, "status": "finished", "result": job.result}
    return {"job_id": job_id, "status": job.get_status()}

@app.get("/health")
def health():
    try:
        redis_conn.ping()
        return {"ok": True, "redis": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
