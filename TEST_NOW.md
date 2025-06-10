# 🚀 Test MCP Orchestrator Right Now

## Step 1: Stop Old Container
```bash
docker stop mcp-orchestrator-auto
docker rm mcp-orchestrator-auto
```

## Step 2: Start Network Services
```bash
./start_network_services.sh
```

Wait for "✅ Services started!" message.

## Step 3: Quick Test (30 seconds)
```bash
./quick_test.sh
```

This will:
- Check health
- Test Gemini query
- Test O3 query  
- Test multi-model review

## Step 4: Interactive Testing
```bash
python interactive_test.py
```

Then press:
- `2` → Get Status (see models and costs)
- `3` → Query Gemini (ask any question)
- `4` → Query O3 (ask architecture questions)
- `8` → Run all tests automatically

## Step 5: Test from Another App

### Python Example
```python
import requests

# Ask Gemini a question
response = requests.post('http://localhost:5050/mcp/query_specific_model',
    json={
        "model": "gemini_pro",
        "description": "What are Python best practices?"
    })
    
print(response.json()['result'])
```

### cURL Example
```bash
curl -X POST http://localhost:5050/mcp/orchestrate_task \
  -H "Content-Type: application/json" \
  -d '{"description": "Compare Docker vs Kubernetes"}' | jq '.'
```

### Browser Test
Open `test.html` in your browser and click the buttons.

## What You Should See

1. **Health Check**: 
   ```json
   {"status": "healthy", "mcp_initialized": true}
   ```

2. **Gemini Response**:
   ```
   "Gemini 2.5 Pro here! Python best practices include..."
   ```

3. **O3 Response**:
   ```
   "From an architectural perspective, microservices should..."
   ```

## Quick Troubleshooting

### If services won't start:
```bash
# Check logs
docker-compose -f docker-compose.network.yml logs

# Check .env file
cat .env | grep API_KEY
```

### If connection refused:
```bash
# Check if services are running
docker ps | grep mcp

# Restart services
docker-compose -f docker-compose.network.yml restart
```

### If API key errors:
```bash
# Make sure .env has your keys
echo "OPENROUTER_API_KEY=your_key_here" >> .env
echo "OPENAI_API_KEY=your_key_here" >> .env
```

## 🎉 Success Indicators

You know it's working when:
1. ✅ Health check returns "healthy"
2. ✅ Gemini gives thoughtful responses
3. ✅ O3 provides architectural insights
4. ✅ Multi-model reviews show different perspectives
5. ✅ You can query from other apps via REST/WebSocket

## Stop Services When Done
```bash
docker-compose -f docker-compose.network.yml down
```