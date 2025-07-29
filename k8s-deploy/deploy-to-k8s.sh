#!/bin/bash
set -e

# Configuration
REGISTRY="your-registry"  # Replace with your registry
IMAGE_NAME="raganything"
TAG="${TAG:-latest}"
NAMESPACE="raganything"

echo "RAG-Anything K8s Deployment Script"
echo "=================================="

# Check kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

# Check if connected to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Not connected to a Kubernetes cluster"
    exit 1
fi

# Build and push image
echo "Building Docker image..."
docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} .

echo "Pushing image to registry..."
docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}

# Update image in manifests
echo "Updating Kubernetes manifests..."
sed -i.bak "s|your-registry/raganything:latest|${REGISTRY}/${IMAGE_NAME}:${TAG}|g" k8s-*.yaml

# Create namespace if it doesn't exist
echo "Creating namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply manifests
echo "Applying Kubernetes manifests..."
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-ingress.yaml

# Wait for deployment
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/raganything -n ${NAMESPACE}

# Show status
echo ""
echo "Deployment complete! Current status:"
kubectl get all -n ${NAMESPACE}
echo ""
echo "To check logs:"
echo "  kubectl logs -f deployment/raganything -n ${NAMESPACE}"
echo ""
echo "To access the service:"
echo "  kubectl port-forward service/raganything 8000:8000 -n ${NAMESPACE}"

# Restore original manifests
mv k8s-*.yaml.bak k8s-*.yaml 2>/dev/null || true