#!/bin/bash
# Simple test of MCP orchestrator

echo "🧪 Simple MCP Orchestrator Test"
echo "=============================="

# Test 1: Get status via Docker
echo -e "\n1. Testing orchestrator status..."
echo '{"jsonrpc":"2.0","method":"get_orchestrator_status","params":{},"id":1}' | \
docker run --rm -i --env-file .env mcp-orchestrator:latest python -m src.mcp_server 2>/dev/null | \
grep -o '"status":"[^"]*"' || echo "❌ Status check failed"

# Test 2: Query Gemini
echo -e "\n2. Testing Gemini query..."
echo '{"jsonrpc":"2.0","method":"query_specific_model","params":{"model":"gemini_pro","description":"Hello from test"},"id":2}' | \
docker run --rm -i --env-file .env mcp-orchestrator:latest python -m src.mcp_server 2>/dev/null | \
grep -o '"content":"[^"]*"' | head -c 100 || echo "❌ Gemini query failed"

echo -e "\n\n✅ Test complete!"