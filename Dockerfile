# Multi-stage Dockerfile for RAG-Anything
# Supports both CPU and GPU environments

# Stage 1: Base image with Python and system dependencies
FROM python:3.10-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic tools
    curl \
    wget \
    git \
    build-essential \
    # LibreOffice for document processing
    libreoffice \
    # Image processing libraries
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglu1-mesa \
    # PDF processing
    poppler-utils \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Stage 2: Dependencies installation
FROM base AS dependencies

WORKDIR /app

# Copy requirements files
COPY requirements.txt setup.py MANIFEST.in ./
COPY raganything/__init__.py ./raganything/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    # Install base requirements
    pip install -r requirements.txt && \
    # Install optional dependencies for full feature support
    pip install Pillow>=10.0.0 reportlab>=4.0.0

# Stage 3: Final image
FROM base AS final

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Install the package in development mode
RUN pip install -e '.[all]'

# Create necessary directories with proper permissions
RUN mkdir -p /app/rag_storage /app/output /app/logs /app/inputs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory permissions
VOLUME ["/app/rag_storage", "/app/output", "/app/inputs", "/app/logs"]

# Expose ports for potential API servers
EXPOSE 8000 8080

# Default environment variables
ENV WORKING_DIR=/app/rag_storage \
    OUTPUT_DIR=/app/output \
    INPUT_DIR=/app/inputs \
    LOG_DIR=/app/logs \
    PARSER=mineru \
    PARSE_METHOD=auto \
    ENABLE_IMAGE_PROCESSING=true \
    ENABLE_TABLE_PROCESSING=true \
    ENABLE_EQUATION_PROCESSING=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from raganything import RAGAnything; print('Health check passed')" || exit 1

# Default command - can be overridden
CMD ["python", "-c", "print('RAG-Anything Docker container is ready. Run with specific commands or mount your scripts.')"]