#!/bin/bash
# Demonstrate MCP Orchestrator functionality

echo "🎯 MCP Orchestrator Demo"
echo "========================"
echo ""
echo "This orchestrator enhances Claude (me) with external AI models:"
echo "- Gemini 2.5 Pro (via OpenRouter)"
echo "- O3 (via OpenAI)"
echo ""

# Function to call MCP tool
call_mcp_tool() {
    local tool=$1
    local params=$2
    echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"'$tool'","arguments":'$params'},"id":1}' | \
    docker run --rm -i --env-file .env mcp-orchestrator:latest python -m src.mcp_server 2>/dev/null
}

# Demo 1: Status
echo "1. Getting orchestrator status..."
result=$(call_mcp_tool "get_orchestrator_status" '{}')
if echo "$result" | grep -q "result"; then
    echo "✅ Orchestrator is running!"
    echo "$result" | python -c "
import sys, json
data = json.load(sys.stdin)
if 'result' in data and data['result']:
    content = data['result'][0]['content'] if isinstance(data['result'], list) else data['result']
    try:
        status = json.loads(content)
        print(f'   Status: {status.get(\"status\", \"unknown\")}')
        print(f'   Models: ' + ', '.join(status.get('models_available', [])))
    except:
        print('   ', content[:100])
" 2>/dev/null || echo "   [Status data]"
else
    echo "❌ Failed to get status"
fi

# Demo 2: Query Gemini
echo -e "\n2. Asking Gemini a question..."
result=$(call_mcp_tool "query_specific_model" '{"model":"gemini_pro","description":"What are 3 key benefits of TypeScript? Be very brief."}')
if echo "$result" | grep -q "result"; then
    echo "✅ Gemini 2.5 Pro responds:"
    echo "$result" | python -c "
import sys, json
data = json.load(sys.stdin)
if 'result' in data and data['result']:
    content = data['result'][0]['content'] if isinstance(data['result'], list) else data['result']
    try:
        response = json.loads(content)
        print('   ', response.get('content', content)[:300])
    except:
        print('   ', content[:300])
" 2>/dev/null || echo "   [Gemini response]"
else
    echo "❌ Failed to query Gemini"
fi

# Demo 3: Query O3
echo -e "\n3. Asking O3 about architecture..."
result=$(call_mcp_tool "query_specific_model" '{"model":"o3_architect","description":"Best pattern for error handling in microservices? One sentence."}')
if echo "$result" | grep -q "result"; then
    echo "✅ O3 responds:"
    echo "$result" | python -c "
import sys, json
data = json.load(sys.stdin)
if 'result' in data and data['result']:
    content = data['result'][0]['content'] if isinstance(data['result'], list) else data['result']
    try:
        response = json.loads(content)
        print('   ', response.get('content', content)[:300])
    except:
        print('   ', content[:300])
" 2>/dev/null || echo "   [O3 response]"
else
    echo "❌ Failed to query O3"
fi

echo -e "\n========================"
echo "✅ Demo complete!"
echo ""
echo "The MCP Orchestrator allows Claude to get additional perspectives"
echo "from external AI models to provide enhanced responses."