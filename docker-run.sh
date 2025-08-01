#!/bin/bash

# Docker Compose run script for RAG-Anything

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE=""
COMMAND="up"
DETACH=""
BUILD=""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  up          Start all services (default)"
    echo "  down        Stop all services"
    echo "  logs        Show logs"
    echo "  ps          List running services"
    echo "  exec        Execute command in container"
    echo "  restart     Restart services"
    echo ""
    echo "Options:"
    echo "  -d, --detach        Run in background"
    echo "  -b, --build         Build images before starting"
    echo "  -p, --profile PROF  Use specific profile:"
    echo "                      - default: RAGAnything + Qdrant"
    echo "                      - with-postgres: Add PostgreSQL"
    echo "                      - with-neo4j: Add Neo4j"
    echo "                      - with-ollama: Add Ollama for local LLM"
    echo "                      - with-redis: Add Redis for caching"
    echo "                      - full-stack: All services"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Start default services"
    echo "  $0 -d                        # Start in background"
    echo "  $0 -p full-stack -b          # Build and start all services"
    echo "  $0 exec python examples/raganything_example.py /app/inputs/document.pdf"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--detach)
            DETACH="-d"
            shift
            ;;
        -b|--build)
            BUILD="--build"
            shift
            ;;
        -p|--profile)
            PROFILE="--profile $2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        up|down|logs|ps|exec|restart)
            COMMAND="$1"
            shift
            break
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    if [ -f ".env.docker.example" ]; then
        echo -e "${BLUE}Creating .env from .env.docker.example${NC}"
        cp .env.docker.example .env
        echo -e "${YELLOW}Please edit .env file with your API keys before running${NC}"
        exit 1
    fi
fi

# Check if directories exist
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p rag_storage output inputs logs

# Execute command based on input
case $COMMAND in
    up)
        echo -e "${GREEN}Starting RAG-Anything services...${NC}"
        if [ -n "$PROFILE" ]; then
            echo -e "${BLUE}Using profile: ${PROFILE#--profile }${NC}"
        fi
        docker-compose $PROFILE up $DETACH $BUILD
        
        if [ -z "$DETACH" ]; then
            echo -e "\n${GREEN}Services are running in foreground${NC}"
        else
            echo -e "\n${GREEN}Services started in background${NC}"
            echo -e "${BLUE}View logs with: $0 logs${NC}"
            echo -e "${BLUE}Stop services with: $0 down${NC}"
            echo ""
            echo -e "${GREEN}To run RAG-Anything examples:${NC}"
            echo "docker exec -it raganything python examples/raganything_example.py /app/inputs/your_document.pdf"
        fi
        ;;
        
    down)
        echo -e "${YELLOW}Stopping RAG-Anything services...${NC}"
        docker-compose $PROFILE down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
        
    logs)
        echo -e "${BLUE}Showing logs...${NC}"
        docker-compose $PROFILE logs -f "$@"
        ;;
        
    ps)
        echo -e "${BLUE}Listing services...${NC}"
        docker-compose $PROFILE ps
        ;;
        
    exec)
        if [ -z "$*" ]; then
            echo -e "${BLUE}Entering interactive shell...${NC}"
            docker-compose $PROFILE exec raganything /bin/bash
        else
            echo -e "${BLUE}Executing command: $*${NC}"
            docker-compose $PROFILE exec raganything "$@"
        fi
        ;;
        
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        docker-compose $PROFILE restart
        echo -e "${GREEN}Services restarted${NC}"
        ;;
        
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_usage
        exit 1
        ;;
esac

# Show service status after up command
if [ "$COMMAND" = "up" ] && [ -n "$DETACH" ]; then
    sleep 5
    echo -e "\n${BLUE}Service Status:${NC}"
    docker-compose $PROFILE ps
    
    echo -e "\n${GREEN}Quick Start Examples:${NC}"
    echo "1. Process a document:"
    echo "   docker exec -it raganything python examples/raganything_example.py /app/inputs/document.pdf"
    echo ""
    echo "2. Test MinerU parsing:"
    echo "   docker exec -it raganything python examples/office_document_test.py --file /app/inputs/document.docx"
    echo ""
    echo "3. Interactive Python shell:"
    echo "   docker exec -it raganything python"
    echo ""
    echo "4. View Qdrant UI:"
    echo "   Open http://localhost:6333/dashboard in your browser"
fi