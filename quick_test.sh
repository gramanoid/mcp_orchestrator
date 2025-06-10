#!/bin/bash
# Quick test script for MCP Orchestrator

echo "🧪 MCP Orchestrator Quick Test"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local data=$3
    
    echo -n "Testing $name... "
    
    response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$data" 2>/dev/null)
    
    if [ $? -eq 0 ] && echo "$response" | grep -q "success"; then
        echo -e "${GREEN}✅ SUCCESS${NC}"
        echo "Response preview: $(echo "$response" | jq -r '.result // .status' 2>/dev/null | head -c 100)..."
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "Error: $response"
        return 1
    fi
}

# Start services if not running
echo "Checking if services are running..."
if ! curl -s http://localhost:5050/health > /dev/null 2>&1; then
    echo "Starting services..."
    ./start_network_services.sh
    echo "Waiting for services to be ready..."
    sleep 10
fi

echo ""
echo "Running tests..."
echo ""

# Test 1: Health check
echo -n "1. Health Check... "
if curl -s http://localhost:5050/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Not healthy${NC}"
    exit 1
fi

# Test 2: Status
test_endpoint "2. Orchestrator Status" \
    "http://localhost:5050/mcp/get_orchestrator_status" \
    '{}'

# Test 3: Gemini query
test_endpoint "3. Gemini Query" \
    "http://localhost:5050/mcp/query_specific_model" \
    '{"model": "gemini_pro", "description": "What is 2+2?"}'

# Test 4: O3 query
test_endpoint "4. O3 Query" \
    "http://localhost:5050/mcp/query_specific_model" \
    '{"model": "o3_architect", "description": "Name one design pattern"}'

# Test 5: Multi-model
test_endpoint "5. Multi-Model Review" \
    "http://localhost:5050/mcp/orchestrate_task" \
    '{"description": "Compare REST vs GraphQL", "strategy": "external_enhancement"}'

echo ""
echo "=============================="
echo -e "${GREEN}✅ All tests completed!${NC}"
echo ""
echo "📡 Services are running at:"
echo "   REST API: http://localhost:5050"
echo "   WebSocket: ws://localhost:8765"
echo ""
echo "📚 Next steps:"
echo "   - Run full test: python test_network_access.py"
echo "   - Try examples: python examples/integration_example.py"
echo "   - View logs: docker-compose -f docker-compose.network.yml logs -f"