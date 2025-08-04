#!/bin/bash

# Quick fix script for common Docker issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}RAG-Anything Docker Quick Fix${NC}"
echo -e "${BLUE}=============================${NC}"

# Function to check if running with sudo
check_sudo() {
    if [ "$EUID" -ne 0 ] && ! groups | grep -q docker; then 
        echo -e "${YELLOW}This script may need to run with sudo or you need to be in the docker group${NC}"
        echo -e "${YELLOW}Try: sudo $0${NC}"
        exit 1
    fi
}

# Function to fix common issues
fix_issues() {
    echo -e "\n${YELLOW}1. Stopping all services...${NC}"
    docker-compose down 2>/dev/null || true
    
    echo -e "\n${YELLOW}2. Removing problematic containers...${NC}"
    docker rm -f raganything-qdrant 2>/dev/null || true
    docker rm -f raganything 2>/dev/null || true
    
    echo -e "\n${YELLOW}3. Cleaning up volumes (keeping data)...${NC}"
    # Don't remove named volumes, just clean up anonymous ones
    docker volume prune -f
    
    echo -e "\n${YELLOW}4. Checking port conflicts...${NC}"
    for port in 6333 6334; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${RED}Port $port is in use!${NC}"
            echo -e "Process using port $port:"
            lsof -Pi :$port -sTCP:LISTEN
            echo -e "${YELLOW}Kill the process or change the port in docker-compose.yml${NC}"
        else
            echo -e "${GREEN}Port $port is free${NC}"
        fi
    done
    
    echo -e "\n${YELLOW}5. Creating necessary directories...${NC}"
    mkdir -p rag_storage output inputs logs
    
    echo -e "\n${YELLOW}6. Pulling latest images...${NC}"
    docker pull qdrant/qdrant:v1.7.4
    
    echo -e "\n${YELLOW}7. Starting services again...${NC}"
    docker-compose up -d qdrant
    
    # Wait for Qdrant to be healthy
    echo -e "\n${YELLOW}Waiting for Qdrant to be healthy...${NC}"
    for i in {1..30}; do
        if docker exec raganything-qdrant wget --spider -q http://localhost:6333/health 2>/dev/null; then
            echo -e "${GREEN}Qdrant is healthy!${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    echo -e "\n${YELLOW}8. Starting RAGAnything...${NC}"
    docker-compose up -d raganything
    
    echo -e "\n${GREEN}Fix complete! Checking status...${NC}"
    docker-compose ps
}

# Main execution
check_sudo
fix_issues

echo -e "\n${GREEN}Next steps:${NC}"
echo "1. Check if services are running: docker-compose ps"
echo "2. View logs if needed: docker-compose logs -f"
echo "3. Access Qdrant UI: http://localhost:6333/dashboard"
echo "4. Run examples: docker exec -it raganything python examples/raganything_example.py /app/inputs/document.pdf"