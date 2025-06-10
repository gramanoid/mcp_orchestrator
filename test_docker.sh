#!/bin/bash
# Test MCP Orchestrator in Docker

echo "Testing MCP Orchestrator Docker deployment"
echo "=========================================="

# Check if API key is set
if [ -z "$OPENROUTER_API_KEY" ]; then
    source .env 2>/dev/null || true
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "Warning: OPENROUTER_API_KEY not set"
fi

# Test 1: Basic container run
echo -e "\n1. Testing container startup..."
docker run --rm \
    -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    mcp-orchestrator:latest \
    python -c "print('✓ Container runs Python successfully')"

# Test 2: Import test
echo -e "\n2. Testing imports in container..."
docker run --rm \
    -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    mcp-orchestrator:latest \
    python -c "
from src.core.orchestrator import MCPOrchestrator
from src.adapters.claude_adapter import ClaudeAdapter
from src.strategies.progressive_deep_dive import ProgressiveDeepDiveStrategy
print('✓ All imports successful')
"

# Test 3: MCP server startup
echo -e "\n3. Testing MCP server startup..."
timeout 5 docker run --rm \
    -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    mcp-orchestrator:latest \
    python -m src.mcp_server_simple 2>&1 | grep -q "Starting simple MCP server" && \
    echo "✓ MCP server starts successfully" || \
    echo "✗ MCP server failed to start"

# Test 4: Configuration test
echo -e "\n4. Testing configuration loading..."
docker run --rm \
    -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    -v $(pwd)/config:/app/config:ro \
    mcp-orchestrator:latest \
    python -c "
from src.config.manager import ConfigManager
cm = ConfigManager()
config = cm.load_config()
print(f'✓ Config loaded with {len(config.get(\"models\", {}))} models')
"

echo -e "\n=========================================="
echo "Docker tests completed!"