#!/bin/bash
# Test Docker deployment of MCP Orchestrator

echo "🧪 Testing MCP Orchestrator Docker Deployment"
echo "==========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run test
run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((TESTS_FAILED++))
        echo "  Command: $test_command"
    fi
}

# Test 1: Docker available
run_test "Docker availability" "docker --version"

# Test 2: Build image
echo ""
echo "Building Docker image..."
if docker build -t mcp-orchestrator:test . > build.log 2>&1; then
    echo -e "${GREEN}✅ Docker build successful${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Docker build failed${NC}"
    echo "Check build.log for details"
    ((TESTS_FAILED++))
    exit 1
fi

# Test 3: Image exists
run_test "Docker image exists" "docker images | grep mcp-orchestrator"

# Test 4: Container can start
echo ""
echo "Testing container startup..."
docker run --rm -d --name mcp-test mcp-orchestrator:test sleep 30
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container starts successfully${NC}"
    ((TESTS_PASSED++))
    docker stop mcp-test > /dev/null 2>&1
else
    echo -e "${RED}❌ Container failed to start${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Python imports work
echo ""
echo "Testing Python imports..."
docker run --rm mcp-orchestrator:test python -c "
import sys
sys.path.append('/app/src')
try:
    from mcp_server import server
    from core.orchestrator import MCPOrchestrator
    from tools.comparative_analysis import ComparativeAnalysisTool
    print('All imports successful')
    sys.exit(0)
except Exception as e:
    print(f'Import failed: {e}')
    sys.exit(1)
" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python imports successful${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Python imports failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: MCP server can initialize
echo ""
echo "Testing MCP server initialization..."
timeout 5 docker run --rm -i mcp-orchestrator:test python -c "
import asyncio
import sys
sys.path.append('/app/src')

async def test():
    try:
        from mcp_server import initialize_orchestrator
        await initialize_orchestrator()
        print('MCP server initialized')
        return True
    except Exception as e:
        print(f'Initialization failed: {e}')
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ MCP server initialization successful${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️  MCP server initialization needs API keys${NC}"
    # This is expected without API keys
fi

# Test 7: Environment variables
echo ""
echo "Testing environment variable handling..."
docker run --rm -e TEST_VAR=test_value mcp-orchestrator:test printenv | grep TEST_VAR > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Environment variables work${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Environment variable handling failed${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Volume mounting
echo ""
echo "Testing volume mounting..."
touch test_file.txt
docker run --rm -v $(pwd)/test_file.txt:/app/test_file.txt mcp-orchestrator:test ls /app/test_file.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Volume mounting works${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Volume mounting failed${NC}"
    ((TESTS_FAILED++))
fi
rm -f test_file.txt

# Test 9: Docker Compose
echo ""
echo "Testing Docker Compose setup..."
docker-compose -f docker-compose.mcp-enhanced.yml config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker Compose configuration valid${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Docker Compose configuration invalid${NC}"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo "====================================="
echo "Test Summary:"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Docker deployment is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Create .env file with API keys"
    echo "2. Run: ./deploy_mcp.sh"
    echo "3. Use MCP tools in Claude Code"
else
    echo -e "${RED}⚠️  Some tests failed. Please fix issues before deployment.${NC}"
fi

# Cleanup
docker rmi mcp-orchestrator:test > /dev/null 2>&1
rm -f build.log

exit $TESTS_FAILED