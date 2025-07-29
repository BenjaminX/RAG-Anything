#!/bin/bash
set -e

# Configuration
REGISTRY="${REGISTRY:-docker.io}"  # Change to your registry
IMAGE_NAME="${IMAGE_NAME:-raganything}"
TAG="${TAG:-latest}"

echo "Building multi-architecture Docker image"
echo "========================================"

# Enable Docker Buildx
echo "Setting up Docker Buildx..."
docker buildx create --name multiarch-builder --use || docker buildx use multiarch-builder
docker buildx inspect --bootstrap

# Build for multiple platforms
echo "Building for linux/amd64..."
docker buildx build \
  --platform linux/amd64 \
  --tag ${REGISTRY}/${IMAGE_NAME}:${TAG} \
  --tag ${REGISTRY}/${IMAGE_NAME}:${TAG}-$(date +%Y%m%d) \
  --push \
  .

echo ""
echo "Build complete!"
echo "Images pushed to:"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${TAG}"
echo "  - ${REGISTRY}/${IMAGE_NAME}:${TAG}-$(date +%Y%m%d)"

# Local load for testing (only loads current architecture)
# echo ""
# echo "To load the image locally for testing (ARM64 only on M1):"
# echo "docker buildx build --platform linux/arm64 --tag ${IMAGE_NAME}:${TAG} --load ."