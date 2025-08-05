#!/bin/bash

# Debug script for Qdrant health check issues

echo "🔍 Debugging Qdrant Health Check"
echo "================================"

# Check if Qdrant container is running
echo -e "\n1. Checking container status:"
sudo docker ps -a | grep qdrant || echo "No Qdrant container found"

# Check Qdrant logs
echo -e "\n2. Recent Qdrant logs:"
sudo docker logs raganything-qdrant --tail 20 2>&1

# Test different health check endpoints
echo -e "\n3. Testing health endpoints:"

# Try curl if available
echo -n "   - Testing with curl: "
sudo docker exec raganything-qdrant curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/health 2>/dev/null || echo "curl not available"

# Try wget
echo -n "   - Testing with wget: "
sudo docker exec raganything-qdrant wget -q -O- http://localhost:6333/health 2>/dev/null && echo "Success" || echo "Failed"

# Try direct HTTP request
echo -n "   - Testing root endpoint: "
sudo docker exec raganything-qdrant wget -q -O- http://localhost:6333/ 2>/dev/null | head -1 || echo "Failed"

# Check from host
echo -e "\n4. Testing from host:"
echo -n "   - Port 6333: "
curl -s http://localhost:6333/health 2>/dev/null && echo "Accessible" || echo "Not accessible"

# Check what's actually in the container
echo -e "\n5. Available tools in container:"
sudo docker exec raganything-qdrant which curl 2>/dev/null && echo "   ✓ curl available" || echo "   ✗ curl not available"
sudo docker exec raganything-qdrant which wget 2>/dev/null && echo "   ✓ wget available" || echo "   ✗ wget not available"
sudo docker exec raganything-qdrant which nc 2>/dev/null && echo "   ✓ nc available" || echo "   ✗ nc not available"

# Show actual health check command result
echo -e "\n6. Running actual health check command:"
sudo docker exec raganything-qdrant sh -c "wget --no-verbose --tries=1 --spider http://localhost:6333/health" 2>&1

# Alternative health checks
echo -e "\n7. Alternative health check methods:"
echo "   - Using Python:"
sudo docker exec raganything-qdrant python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:6333/health').status)" 2>/dev/null || echo "     Python not available"

echo "   - Using /dev/tcp:"
sudo docker exec raganything-qdrant bash -c "timeout 1 bash -c '</dev/tcp/localhost/6333' && echo '     Port is open' || echo '     Port is closed'" 2>/dev/null || echo "     Bash tcp not available"

echo -e "\n✅ Debug complete!"