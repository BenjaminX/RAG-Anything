#!/bin/bash

# Docker build script for RAG-Anything

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BUILD_TYPE="cpu"
IMAGE_TAG="latest"
PUSH=false
REGISTRY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            BUILD_TYPE="gpu"
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --gpu              Build GPU-enabled image (default: CPU)"
            echo "  --tag TAG          Docker image tag (default: latest)"
            echo "  --push             Push image to registry after build"
            echo "  --registry REG     Docker registry URL"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Set image name based on build type
if [ "$BUILD_TYPE" = "gpu" ]; then
    DOCKERFILE="Dockerfile.gpu"
    IMAGE_NAME="raganything-gpu"
    echo -e "${YELLOW}Building GPU-enabled image...${NC}"
else
    DOCKERFILE="Dockerfile"
    IMAGE_NAME="raganything"
    echo -e "${YELLOW}Building CPU-only image...${NC}"
fi

# Add registry prefix if provided
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo -e "${GREEN}Image name: ${FULL_IMAGE_NAME}${NC}"
echo -e "${GREEN}Dockerfile: ${DOCKERFILE}${NC}"

# Build the Docker image
echo -e "\n${YELLOW}Starting Docker build...${NC}"
docker build -f "$DOCKERFILE" -t "$FULL_IMAGE_NAME" .

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Docker image built successfully!${NC}"
    
    # Show image info
    echo -e "\n${YELLOW}Image information:${NC}"
    docker images | grep "$IMAGE_NAME" | head -1
    
    # Push to registry if requested
    if [ "$PUSH" = true ]; then
        echo -e "\n${YELLOW}Pushing image to registry...${NC}"
        docker push "$FULL_IMAGE_NAME"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Image pushed successfully!${NC}"
        else
            echo -e "${RED}✗ Failed to push image${NC}"
            exit 1
        fi
    fi
    
    # Show run instructions
    echo -e "\n${GREEN}To run the container:${NC}"
    if [ "$BUILD_TYPE" = "gpu" ]; then
        echo "docker run --gpus all -v \$(pwd)/inputs:/app/inputs -v \$(pwd)/output:/app/output $FULL_IMAGE_NAME"
    else
        echo "docker run -v \$(pwd)/inputs:/app/inputs -v \$(pwd)/output:/app/output $FULL_IMAGE_NAME"
    fi
    
    echo -e "\n${GREEN}To run with docker-compose:${NC}"
    echo "docker-compose up"
    
else
    echo -e "\n${RED}✗ Docker build failed!${NC}"
    exit 1
fi