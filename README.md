# Text Intelligence API

A FastAPI-based text processing service that provides AI-powered text summarization, question answering, and tone rewriting capabilities using Hugging Face transformers and Redis for caching and job queuing.

## Features

- **Text Summarization**: Generate concise summaries of long text
- **Question Answering**: Answer questions based on provided context
- **Tone Rewriting**: Convert text between formal and informal tones
- **Redis Caching**: Intelligent caching to improve response times
- **Async Job Processing**: Background task processing with RQ (Redis Queue)
- **Docker Support**: Complete containerization with docker-compose

## APIi Endpoints

### Synchronous Endpoints
- `POST /summarize` - Summarize text
- `POST /qa` - Answer questions based on context
- `POST /rewrite` - Rewrite text tone (formal/informal)

### Asynchronous Endpoints
- `POST /submit/{task_type}` - Submit job for background processing
- `GET /status/{job_id}` - Check job status
- `GET /result/{job_id}` - Get job result

### Health Check
- `GET /health` - Check service and Redis connection status

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Redis (included in Docker setup)

## Quick Start with Docker

### 1. Clone the Repository
```bash
git clone <repository-url>
cd fixit
```

### 2. Run with Docker Compose
```bash
docker-compose up --build
```

This will start:
- Redis server on port 6379
- FastAPI web service on port 8000
- RQ worker for background job processing

### 3. Access the API
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Local Development Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Redis (if not using Docker)
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7

# Or install Redis locally and start the service
```

### 3. Start the Application
```bash
python app.py
```

### 4. Start the Worker (for async jobs)
```bash
rq worker genai --url redis://localhost:6379/0
```

## API Usage Examples

### Text Summarization
```bash
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your long text here...",
    "max_length": 150,
    "min_length": 25
  }'
```

### Question Answering
```bash
curl -X POST "http://localhost:8000/qa" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "Context text here...",
    "question": "Your question here?"
  }'
```

### Tone Rewriting
```bash
curl -X POST "http://localhost:8000/rewrite" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Text to rewrite",
    "tone": "formal"
  }'
```

### Asynchronous Job Processing
```bash
# Submit a job
curl -X POST "http://localhost:8000/submit/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your text here...",
    "max_length": 150,
    "min_length": 25
  }'

# Check job status
curl "http://localhost:8000/status/{job_id}"

# Get result when finished
curl "http://localhost:8000/result/{job_id}"
```

## Docker Configuration

### Dockerfile
The application uses a multi-stage Python 3.11 slim image with:
- FastAPI and uvicorn for the web server
- Transformers and PyTorch for AI models
- Redis and RQ for caching and job queuing

### Docker Compose Services

#### Web Service
- **Image**: Built from local Dockerfile
- **Port**: 8000 (mapped to host)
- **Environment**: REDIS_URL=redis://redis:6379/0
- **Dependencies**: Redis service

#### Worker Service
- **Image**: Same as web service
- **Command**: RQ worker for background processing
- **Environment**: REDIS_URL=redis://redis:6379/0
- **Dependencies**: Redis service

#### Redis Service
- **Image**: redis:7
- **Port**: 6379 (mapped to host)
- **Purpose**: Caching and job queue storage

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_TTL` | `86400` | Cache time-to-live in seconds (24 hours) |

## Deployment

### Production Deployment with Docker

1. **Prepare for Production**
```bash
# Update docker-compose.yml for production
# Remove port mappings for Redis if not needed externally
# Set appropriate environment variables
```

2. **Deploy with Docker Compose**
```bash
# Build and start services
docker-compose up -d --build

# Scale workers if needed
docker-compose up -d --scale worker=3
```

3. **Monitor Services**
```bash
# Check logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Cloud Deployment Options

#### AWS ECS/Fargate
1. Build and push Docker image to ECR
2. Create ECS task definition with required environment variables
3. Set up Application Load Balancer for the web service
4. Use ElastiCache for Redis

#### Google Cloud Run
1. Build and push to Google Container Registry
2. Deploy web service to Cloud Run
3. Use Cloud Memorystore for Redis
4. Deploy workers separately or use Cloud Tasks

#### Azure Container Instances
1. Push to Azure Container Registry
2. Deploy using Azure Container Instances
3. Use Azure Cache for Redis

### Environment-Specific Configuration

#### Production Environment Variables
```bash
REDIS_URL=redis://your-redis-host:6379/0
CACHE_TTL=86400
```

#### Health Monitoring
- Use `/health` endpoint for load balancer health checks
- Monitor Redis connection and job queue status
- Set up logging and metrics collection

## Performance Considerations

- **Model Loading**: Models are loaded lazily on first use
- **Caching**: Results are cached in Redis to avoid recomputation
- **Background Processing**: Use async endpoints for long-running tasks
- **Scaling**: Scale worker containers based on job queue length

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   - Ensure Redis is running and accessible
   - Check REDIS_URL environment variable
   - Verify network connectivity between services

2. **Model Download Issues**
   - Ensure internet connectivity for initial model downloads
   - Check disk space for model storage
   - Models are cached locally after first download

3. **Memory Issues**
   - Monitor container memory usage
   - Consider using smaller models for resource-constrained environments
   - Adjust worker count based on available resources

### Logs and Debugging
```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs worker
docker-compose logs redis

# Follow logs in real-time
docker-compose logs -f web
```
