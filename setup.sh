#!/bin/bash
set -e

# Check critical environment variable
if [ -z "$OPENAI_API_KEY" ]; then
    echo "WARNING: OPENAI_API_KEY is not set. LLM functionality will not work."
fi

# Create necessary directories if they don't exist
mkdir -p /app/rag_storage /app/output /app/logs

# Execute the main command
exec "$@"