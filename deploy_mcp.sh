#!/bin/bash
# Deploy MCP Orchestrator to any Claude Code instance

set -e

echo "🚀 MCP Orchestrator Deployment Script"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        echo "Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        echo "Please install Docker Compose"
        exit 1
    fi
    
    # Check Claude CLI
    if ! command -v claude &> /dev/null; then
        echo -e "${YELLOW}⚠️  Claude CLI not found${NC}"
        echo "Install with: npm install -g @anthropic-ai/claude-cli"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Prerequisites checked${NC}"
}

# Function to setup environment
setup_environment() {
    echo ""
    echo "🔑 Setting up environment..."
    
    # Check for .env file
    if [ ! -f .env ]; then
        echo "Creating .env file..."
        cat > .env << EOL
# API Keys for external models
OPENROUTER_API_KEY=your_openrouter_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional: Project path to analyze
PROJECT_PATH=/path/to/your/project

# Cost limits
MAX_COST_PER_REQUEST=5.0
DAILY_COST_LIMIT=100.0
EOL
        echo -e "${YELLOW}⚠️  Please edit .env file with your API keys${NC}"
        read -p "Press Enter after updating .env file..."
    fi
    
    # Source .env
    set -a
    source .env
    set +a
}

# Function to build Docker image
build_docker_image() {
    echo ""
    echo "🔨 Building Docker image..."
    
    # Build with cache
    docker build -t mcp-orchestrator:enhanced . || {
        echo -e "${RED}❌ Docker build failed${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
}

# Function to test MCP server
test_mcp_server() {
    echo ""
    echo "🧪 Testing MCP server..."
    
    # Run a quick test
    docker run --rm -i mcp-orchestrator:enhanced python -c "
import sys
sys.path.append('/app/src')
from mcp_server import server
print('MCP server imports successfully')
" || {
        echo -e "${RED}❌ MCP server test failed${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✅ MCP server test passed${NC}"
}

# Function to setup MCP in Claude Code
setup_claude_code() {
    echo ""
    echo "🔧 Setting up MCP in Claude Code..."
    
    # Remove existing if present
    claude mcp remove mcp-orchestrator 2>/dev/null || true
    
    # Determine platform and setup command
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        MCP_CMD="docker run --rm -i --env-file $(pwd)/.env mcp-orchestrator:enhanced"
    elif grep -qi microsoft /proc/version 2>/dev/null; then
        # WSL
        MCP_CMD="docker run --rm -i --env-file $(pwd)/.env mcp-orchestrator:enhanced"
    else
        # Linux
        MCP_CMD="docker run --rm -i --env-file $(pwd)/.env mcp-orchestrator:enhanced"
    fi
    
    # Add MCP server
    claude mcp add mcp-orchestrator "$MCP_CMD" || {
        echo -e "${YELLOW}⚠️  Could not add MCP server automatically${NC}"
        echo "Manual setup required. Run:"
        echo "claude mcp add mcp-orchestrator \"$MCP_CMD\""
        return
    }
    
    echo -e "${GREEN}✅ MCP server added to Claude Code${NC}"
}

# Function to create quick start guide
create_quickstart() {
    echo ""
    echo "📚 Creating quick start guide..."
    
    cat > QUICKSTART.md << 'EOL'
# MCP Orchestrator Quick Start

## 🚀 Your MCP Orchestrator is ready!

### Available Tools in Claude Code:

1. **Orchestrate Task** - Multi-model task processing
   ```
   /mcp__mcp-orchestrator__orchestrate_task
   ```

2. **Analyze Task** - Determine optimal strategy
   ```
   /mcp__mcp-orchestrator__analyze_task
   ```

3. **Code Review** - Professional multi-model review
   ```
   /mcp__mcp-orchestrator__code_review
   ```

4. **Think Deeper** - Extended reasoning
   ```
   /mcp__mcp-orchestrator__think_deeper
   ```

5. **Multi-Model Review** - Compare model perspectives
   ```
   /mcp__mcp-orchestrator__multi_model_review
   ```

6. **Comparative Analysis** - Decision matrices
   ```
   /mcp__mcp-orchestrator__comparative_analysis
   ```

### Quick Examples:

#### Analyze a codebase:
```
Use /mcp__mcp-orchestrator__orchestrate_task with:
description: "Analyze the architecture of this codebase and suggest improvements"
strategy: "max_quality_council"
```

#### Compare solutions:
```
Use /mcp__mcp-orchestrator__comparative_analysis with:
options: ["PostgreSQL", "MongoDB", "DynamoDB"]
criteria: ["scalability", "cost", "developer_experience", "performance"]
context: "Building a social media platform with 1M users"
```

### Monitoring:
- Check costs: `/mcp__mcp-orchestrator__get_orchestrator_status`
- View logs: `docker logs mcp-orchestrator-enhanced`

### Troubleshooting:
- Restart: `docker-compose -f docker-compose.mcp-enhanced.yml restart`
- Check health: `docker ps | grep mcp-orchestrator`
- View errors: `docker logs mcp-orchestrator-enhanced --tail 50`
EOL
    
    echo -e "${GREEN}✅ Created QUICKSTART.md${NC}"
}

# Main deployment flow
main() {
    echo ""
    echo "Choose deployment option:"
    echo "1) Full deployment (build + setup)"
    echo "2) Docker only (build image)"
    echo "3) Claude Code setup only (use existing image)"
    echo "4) Export deployment package"
    read -p "Enter choice (1-4): " choice
    
    case $choice in
        1)
            check_prerequisites
            setup_environment
            build_docker_image
            test_mcp_server
            setup_claude_code
            create_quickstart
            ;;
        2)
            check_prerequisites
            setup_environment
            build_docker_image
            test_mcp_server
            echo -e "${GREEN}✅ Docker image ready${NC}"
            echo "Run 'docker images | grep mcp-orchestrator' to verify"
            ;;
        3)
            check_prerequisites
            setup_claude_code
            create_quickstart
            ;;
        4)
            echo "📦 Creating deployment package..."
            tar -czf mcp-orchestrator-deploy.tar.gz \
                --exclude='venv' \
                --exclude='__pycache__' \
                --exclude='.git' \
                --exclude='logs/*' \
                --exclude='.env' \
                .
            echo -e "${GREEN}✅ Created mcp-orchestrator-deploy.tar.gz${NC}"
            echo "Share this file to deploy on other machines"
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo "🎉 Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "1. Ensure your API keys are set in .env"
    echo "2. Open Claude Code and type '/' to see MCP tools"
    echo "3. Read QUICKSTART.md for usage examples"
    echo ""
    echo "Happy orchestrating! 🤖"
}

# Run main function
main