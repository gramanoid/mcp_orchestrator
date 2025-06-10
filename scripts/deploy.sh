#!/bin/bash
set -euo pipefail

# MCP Orchestrator Deployment Script
# Follows MCP best practices for secure deployment

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
CONFIG_FILE="config/config.yaml"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found. Creating from template..."
        create_env_file
    fi
    
    # Check if config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warning "config.yaml not found. Creating from example..."
        if [ -f "config/config.example.yaml" ]; then
            cp config/config.example.yaml "$CONFIG_FILE"
            log_info "Created config.yaml from example. Please update with your settings."
        else
            log_error "No config example found. Please create config/config.yaml"
            exit 1
        fi
    fi
}

create_env_file() {
    cat > "$ENV_FILE" << EOF
# MCP Orchestrator Environment Variables
# Generated on $(date)

# API Keys (Required)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# MCP Configuration
MCP_LOG_LEVEL=INFO
MCP_MAX_COST_PER_REQUEST=5.0
MCP_DAILY_LIMIT=100.0

# Security Settings
MCP_ENABLE_ENCRYPTION=true
MCP_MAX_CONCURRENT_TASKS=10
EOF
    
    chmod 600 "$ENV_FILE"
    log_info "Created .env file. Please update it with your API keys."
}

validate_env() {
    log_info "Validating environment..."
    
    # Source .env file
    set -a
    source "$ENV_FILE"
    set +a
    
    # Check required variables
    if [ -z "${OPENROUTER_API_KEY:-}" ] || [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ]; then
        log_error "OPENROUTER_API_KEY not set in .env file"
        exit 1
    fi
    
    log_info "Environment validation successful"
}

build_image() {
    log_info "Building Docker image..."
    docker-compose build --no-cache
    log_info "Docker image built successfully"
}

deploy() {
    log_info "Deploying MCP Orchestrator..."
    
    # Stop existing containers
    if docker-compose ps -q &> /dev/null; then
        log_info "Stopping existing containers..."
        docker-compose down
    fi
    
    # Start containers
    log_info "Starting containers..."
    docker-compose up -d
    
    # Wait for health check
    log_info "Waiting for service to be healthy..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "healthy"; then
            log_info "Service is healthy and ready!"
            break
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            log_error "Service failed to become healthy"
            docker-compose logs
            exit 1
        fi
        
        sleep 2
    done
    
    log_info "MCP Orchestrator deployed successfully!"
    log_info "To view logs: docker-compose logs -f"
}

show_status() {
    log_info "Current deployment status:"
    docker-compose ps
    echo ""
    log_info "Recent logs:"
    docker-compose logs --tail=20
}

# Main script
main() {
    case "${1:-deploy}" in
        deploy)
            check_prerequisites
            validate_env
            build_image
            deploy
            show_status
            ;;
        build)
            check_prerequisites
            build_image
            ;;
        status)
            show_status
            ;;
        logs)
            docker-compose logs -f
            ;;
        stop)
            log_info "Stopping MCP Orchestrator..."
            docker-compose down
            ;;
        restart)
            log_info "Restarting MCP Orchestrator..."
            docker-compose restart
            ;;
        *)
            echo "Usage: $0 {deploy|build|status|logs|stop|restart}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Build and deploy the service (default)"
            echo "  build    - Build Docker image only"
            echo "  status   - Show deployment status"
            echo "  logs     - Follow service logs"
            echo "  stop     - Stop the service"
            echo "  restart  - Restart the service"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"