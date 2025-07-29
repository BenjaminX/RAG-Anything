# Multi-stage build for RAG-Anything
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY setup.py pyproject.toml ./
COPY raganything ./raganything

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e '.[all]'

# Final stage
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # LibreOffice for document processing
    libreoffice \
    # System libraries for image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libfontconfig1 \
    libxrender1 \
    # Security updates
    ca-certificates \
    # Utilities
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for security
# Use specific UID/GID for K8s compatibility
RUN groupadd -g 1000 raguser && \
    useradd -m -u 1000 -g 1000 raguser

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=1000:1000 . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/rag_storage /app/output /app/logs && \
    chown -R 1000:1000 /app && \
    chmod -R 755 /app

# Install MinerU models (can be overridden by volume mount)
RUN mkdir -p /home/raguser/.mineru/models && \
    chown -R 1000:1000 /home/raguser/.mineru && \
    chmod -R 755 /home/raguser/.mineru

# Switch to non-root user
USER 1000:1000

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKING_DIR=/app/rag_storage \
    OUTPUT_DIR=/app/output \
    PARSER=mineru \
    PARSE_METHOD=auto \
    ENABLE_IMAGE_PROCESSING=true \
    ENABLE_TABLE_PROCESSING=true \
    ENABLE_EQUATION_PROCESSING=true \
    MAX_CONCURRENT_FILES=1

# Expose port for API service (if needed)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import raganything; print('OK')" || exit 1

# Add setup script
COPY --chown=1000:1000 setup.sh /app/setup.sh

# Use setup script as entrypoint
ENTRYPOINT ["/app/setup.sh"]

# Default command - can be overridden
CMD ["python", "-m", "raganything"]