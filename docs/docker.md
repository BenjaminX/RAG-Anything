# Docker Deployment Guide for RAG-Anything

This guide provides instructions for building and running RAG-Anything using Docker.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose v2.0+ (optional, for multi-service deployment)
- NVIDIA Docker runtime (for GPU support)
- At least 8GB of available RAM
- 20GB+ of free disk space

## Quick Start

### 1. Build the Docker Image

#### CPU Version (Default)
```bash
# Build CPU-only image
./docker-build.sh

# Or manually:
docker build -t raganything:latest .
```

#### GPU Version (NVIDIA CUDA)
```bash
# Build GPU-enabled image
./docker-build.sh --gpu

# Or manually:
docker build -f Dockerfile.gpu -t raganything-gpu:latest .
```

### 2. Run the Container

#### Basic Usage
```bash
# CPU version
docker run -it \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/rag_storage:/app/rag_storage \
  -e OPENAI_API_KEY=your_api_key \
  raganything:latest \
  python examples/raganything_example.py /app/inputs/document.pdf

# GPU version
docker run -it --gpus all \
  -v $(pwd)/inputs:/app/inputs \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/rag_storage:/app/rag_storage \
  -e OPENAI_API_KEY=your_api_key \
  raganything-gpu:latest \
  python examples/raganything_example.py /app/inputs/document.pdf
```

#### Using Docker Compose
```bash
# Start all services
docker-compose up

# Start with specific profiles (e.g., with vector database)
docker-compose --profile with-qdrant up

# Run in background
docker-compose up -d
```

## Docker Images

### CPU Image (`Dockerfile`)
- Base: `python:3.10-slim`
- Includes: LibreOffice, MinerU, all Python dependencies
- Size: ~2.5GB
- Use for: General document processing without GPU acceleration

### GPU Image (`Dockerfile.gpu`)
- Base: `nvidia/cuda:12.1.0-devel-ubuntu22.04`
- Includes: CUDA toolkit, PyTorch with GPU support, all CPU features
- Size: ~6GB
- Use for: Accelerated processing with NVIDIA GPUs

## Environment Variables

Configure the container using these environment variables:

```bash
# API Configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-large

# Parser Configuration
PARSER=mineru                    # or "docling"
PARSE_METHOD=auto               # or "ocr", "txt"
OUTPUT_DIR=/app/output
WORKING_DIR=/app/rag_storage

# Processing Options
ENABLE_IMAGE_PROCESSING=true
ENABLE_TABLE_PROCESSING=true
ENABLE_EQUATION_PROCESSING=true

# Performance
MAX_CONCURRENT_FILES=4
DEVICE=cuda:0                   # GPU only

# Logging
LOG_LEVEL=INFO
VERBOSE=false
LOG_DIR=/app/logs
```

## Volume Mounts

The following directories can be mounted for persistent storage:

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./inputs` | `/app/inputs` | Input documents |
| `./output` | `/app/output` | Parsed output files |
| `./rag_storage` | `/app/rag_storage` | RAG database storage |
| `./logs` | `/app/logs` | Application logs |
| `./.env` | `/app/.env` | Environment configuration |

## Multi-Service Deployment

The `docker-compose.yml` includes optional services:

### Vector Database (Qdrant)
```bash
# Start with Qdrant
docker-compose --profile with-qdrant up

# Access Qdrant UI at http://localhost:6333
```

### PostgreSQL Storage
```bash
# Start with PostgreSQL
docker-compose --profile with-postgres up

# Configure in .env:
LIGHTRAG_KV_STORAGE=PGKVStorage
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### Neo4j Graph Database
```bash
# Start with Neo4j
docker-compose --profile with-neo4j up

# Access Neo4j Browser at http://localhost:7474
```

## Building Custom Images

### Build with Custom Registry
```bash
# Build and tag for custom registry
./docker-build.sh --tag v1.0.0 --registry myregistry.com

# Push to registry
./docker-build.sh --tag v1.0.0 --registry myregistry.com --push
```

### Multi-Architecture Build
```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t raganything:latest \
  --push .
```

## Production Deployment

### Security Considerations
1. Run as non-root user (already configured)
2. Use secrets management for API keys
3. Limit resource usage
4. Enable health checks

### Resource Limits
```yaml
# In docker-compose.yml
services:
  raganything:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### Scaling
```bash
# Scale service replicas
docker-compose up --scale raganything=3
```

## Troubleshooting

### Common Issues

1. **Out of Memory**
   ```bash
   # Increase shared memory size
   docker run --shm-size=2g ...
   ```

2. **GPU Not Available**
   ```bash
   # Check NVIDIA runtime
   docker run --rm --gpus all nvidia/cuda:12.1.0-base nvidia-smi
   ```

3. **LibreOffice Issues**
   ```bash
   # Test LibreOffice inside container
   docker run -it raganything:latest libreoffice --version
   ```

4. **Permission Errors**
   ```bash
   # Fix volume permissions
   docker run -it --user root raganything:latest chown -R 1000:1000 /app
   ```

### Debugging
```bash
# Run interactive shell
docker run -it --entrypoint /bin/bash raganything:latest

# Check logs
docker logs container_name

# Inspect running container
docker exec -it container_name /bin/bash
```

## Performance Optimization

### CPU Optimization
- Use `--cpus` flag to limit CPU usage
- Enable multi-threading with `MAX_ASYNC` environment variable

### GPU Optimization
- Use specific GPU with `CUDA_VISIBLE_DEVICES`
- Monitor GPU usage with `nvidia-smi`
- Adjust batch sizes for memory efficiency

### Storage Optimization
- Use bind mounts for better I/O performance
- Consider SSD storage for database volumes
- Regular cleanup of output directories

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Build and push Docker image
  run: |
    docker build -t ${{ secrets.REGISTRY }}/raganything:${{ github.sha }} .
    docker push ${{ secrets.REGISTRY }}/raganything:${{ github.sha }}
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: raganything
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: raganything
        image: raganything:latest
        resources:
          limits:
            nvidia.com/gpu: 1
```

## Maintenance

### Update Base Images
```bash
# Pull latest base images
docker pull python:3.10-slim
docker pull nvidia/cuda:12.1.0-devel-ubuntu22.04

# Rebuild
./docker-build.sh --tag latest
```

### Clean Up
```bash
# Remove unused images
docker image prune -a

# Clean build cache
docker builder prune

# Remove volumes (careful!)
docker volume prune
```