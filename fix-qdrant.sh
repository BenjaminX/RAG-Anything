#!/bin/bash

# Fix script specifically for Qdrant health check issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Fixing Qdrant Health Check Issues${NC}"
echo -e "${BLUE}==================================${NC}"

# Step 1: Stop everything
echo -e "\n${YELLOW}1. Stopping all services...${NC}"
sudo docker-compose down

# Step 2: Remove Qdrant container and volume
echo -e "\n${YELLOW}2. Removing Qdrant container...${NC}"
sudo docker rm -f raganything-qdrant 2>/dev/null || true

# Step 3: Use alternative docker-compose without health checks
echo -e "\n${YELLOW}3. Starting services without health checks...${NC}"
sudo docker-compose -f docker-compose.no-healthcheck.yml up -d qdrant

# Step 4: Wait for Qdrant to start
echo -e "\n${YELLOW}4. Waiting for Qdrant to start (30 seconds)...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:6333/ > /dev/null 2>&1; then
        echo -e "\n${GREEN}✓ Qdrant is responding!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Step 5: Check Qdrant status
echo -e "\n${YELLOW}5. Checking Qdrant status...${NC}"
if curl -s http://localhost:6333/health 2>/dev/null; then
    echo -e "${GREEN}✓ Qdrant health endpoint is working${NC}"
else
    echo -e "${YELLOW}⚠ Health endpoint not responding, checking root...${NC}"
    curl -s http://localhost:6333/ | head -5
fi

# Step 6: Start RAGAnything
echo -e "\n${YELLOW}6. Starting RAGAnything service...${NC}"
sudo docker-compose -f docker-compose.no-healthcheck.yml up -d raganything

# Step 7: Final status
echo -e "\n${YELLOW}7. Final status:${NC}"
sudo docker-compose -f docker-compose.no-healthcheck.yml ps

echo -e "\n${GREEN}✅ Fix complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo "1. Access Qdrant UI: http://localhost:6333/dashboard"
echo "2. Test RAGAnything: docker exec -it raganything python examples/docker_quick_start.py /app/inputs/sample.pdf"
echo ""
echo -e "${YELLOW}Note: Using docker-compose.no-healthcheck.yml which doesn't have health checks${NC}"