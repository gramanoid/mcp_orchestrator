# MCP Orchestrator Testing Guide

## Quick Test (2 minutes)

### 1. Start Services
```bash
# First, ensure you have the .env file with API keys
export $(grep -v '^#' .env | xargs)

# Start the network services
./start_network_services.sh
```

### 2. Quick Health Check
```bash
# Test REST API is running
curl http://localhost:5050/health

# Should return:
# {
#   "status": "healthy",
#   "service": "mcp-orchestrator-rest-api",
#   "timestamp": "2024-...",
#   "mcp_initialized": true
# }
```

### 3. List Available Tools
```bash
curl http://localhost:5050/tools | jq '.'
```

### 4. Quick MCP Test
```bash
# Test with a simple query
curl -X POST http://localhost:5050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "query_specific_model",
    "params": {
      "model": "gemini_pro",
      "description": "Say hello in 3 words"
    }
  }' | jq '.'
```

## Comprehensive Test Suite

### Option 1: Run Automated Tests
```bash
# Make sure services are running first
./start_network_services.sh

# Run the comprehensive test
python test_network_access.py
```

### Option 2: Manual Testing

#### A. Test REST API

1. **Test Status Endpoint**
```bash
curl -X POST http://localhost:5050/mcp/get_orchestrator_status \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.'
```

2. **Test Gemini Query**
```bash
curl -X POST http://localhost:5050/mcp/query_specific_model \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini_pro",
    "description": "What are 3 benefits of TypeScript?"
  }' | jq '.'
```

3. **Test O3 Query**
```bash
curl -X POST http://localhost:5050/mcp/query_specific_model \
  -H "Content-Type: application/json" \
  -d '{
    "model": "o3_architect",
    "description": "Best practices for microservices?"
  }' | jq '.'
```

4. **Test Multi-Model Review**
```bash
curl -X POST http://localhost:5050/mcp/multi_model_review \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Should I use Docker or Kubernetes?",
    "focus_areas": ["complexity", "team size", "scalability"]
  }' | jq '.'
```

#### B. Test WebSocket Connection

1. **Install wscat** (if not installed)
```bash
npm install -g wscat
```

2. **Connect to WebSocket**
```bash
wscat -c ws://localhost:8765
```

3. **Send Test Commands** (paste these after connecting)
```json
{"method":"get_orchestrator_status","params":{}}
```

```json
{"method":"query_specific_model","params":{"model":"gemini_pro","description":"Hello from WebSocket!"}}
```

#### C. Test Docker Direct Access

```bash
# Test direct Docker execution
echo '{"method":"get_orchestrator_status","params":{}}' | \
  docker run --rm -i --env-file .env mcp-orchestrator:latest \
  python -m src.mcp_server | jq '.'
```

## Integration Testing

### Python Client Test
```bash
cd examples
python integration_example.py
```

### Create Your Own Test Script

Save as `my_test.py`:
```python
#!/usr/bin/env python3
import requests
import json

def test_mcp():
    base_url = "http://localhost:5050"
    
    # Test 1: Get status
    print("1. Testing status...")
    response = requests.post(f"{base_url}/mcp/get_orchestrator_status", json={})
    print(f"Status: {response.json()['success']}")
    
    # Test 2: Query Gemini
    print("\n2. Testing Gemini...")
    response = requests.post(f"{base_url}/mcp/query_specific_model", json={
        "model": "gemini_pro",
        "description": "What makes Python popular?"
    })
    result = json.loads(response.json()['result'])
    print(f"Gemini says: {result['content'][:100]}...")
    
    # Test 3: Multi-model
    print("\n3. Testing multi-model...")
    response = requests.post(f"{base_url}/mcp/orchestrate_task", json={
        "description": "Compare Python vs JavaScript",
        "strategy": "external_enhancement"
    })
    print(f"Response length: {len(response.json()['result'])} chars")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_mcp()
```

Run it:
```bash
python my_test.py
```

## Load Testing

### Simple Load Test
```bash
# Install hey (HTTP load tester)
# macOS: brew install hey
# Linux: wget https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64 -O hey && chmod +x hey

# Test with 10 concurrent requests
hey -n 10 -c 2 -m POST \
  -H "Content-Type: application/json" \
  -d '{"method":"get_orchestrator_status","params":{}}' \
  http://localhost:5050/mcp
```

## Browser Testing

### Simple HTML Test Page

Save as `test.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP Test</title>
</head>
<body>
    <h1>MCP Orchestrator Test</h1>
    <button onclick="testAPI()">Test REST API</button>
    <button onclick="testWebSocket()">Test WebSocket</button>
    <pre id="output"></pre>

    <script>
        async function testAPI() {
            const output = document.getElementById('output');
            output.textContent = 'Testing REST API...\n';
            
            try {
                const response = await fetch('http://localhost:5050/mcp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        method: 'query_specific_model',
                        params: {
                            model: 'gemini_pro',
                            description: 'Hello from browser!'
                        }
                    })
                });
                
                const result = await response.json();
                output.textContent += JSON.stringify(result, null, 2);
            } catch (error) {
                output.textContent += 'Error: ' + error.message;
            }
        }
        
        function testWebSocket() {
            const output = document.getElementById('output');
            output.textContent = 'Testing WebSocket...\n';
            
            const ws = new WebSocket('ws://localhost:8765');
            
            ws.onopen = () => {
                output.textContent += 'Connected!\n';
                ws.send(JSON.stringify({
                    method: 'get_orchestrator_status',
                    params: {}
                }));
            };
            
            ws.onmessage = (event) => {
                output.textContent += 'Response: ' + event.data + '\n';
            };
            
            ws.onerror = (error) => {
                output.textContent += 'Error: ' + error + '\n';
            };
        }
    </script>
</body>
</html>
```

Open in browser:
```bash
python -m http.server 8080
# Then open http://localhost:8080/test.html
```

## Debugging

### Check Logs
```bash
# View all logs
docker-compose -f docker-compose.network.yml logs

# Follow logs
docker-compose -f docker-compose.network.yml logs -f

# Specific service logs
docker-compose -f docker-compose.network.yml logs mcp-rest-api
```

### Check Container Status
```bash
# See running containers
docker-compose -f docker-compose.network.yml ps

# Check resource usage
docker stats
```

### Common Issues

1. **Port already in use**
```bash
# Find what's using port 5050
lsof -i :5050
# or
netstat -tlnp | grep 5050
```

2. **API Key errors**
```bash
# Verify environment variables
docker-compose -f docker-compose.network.yml exec mcp-rest-api env | grep API_KEY
```

3. **Connection refused**
```bash
# Check if services are running
docker-compose -f docker-compose.network.yml ps

# Restart services
docker-compose -f docker-compose.network.yml restart
```

## Performance Testing

### Monitor Response Times
```bash
# Create a monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
while true; do
    START=$(date +%s.%N)
    curl -s -X POST http://localhost:5050/mcp/get_orchestrator_status \
      -H "Content-Type: application/json" -d '{}' > /dev/null
    END=$(date +%s.%N)
    DIFF=$(echo "$END - $START" | bc)
    echo "Response time: ${DIFF}s"
    sleep 5
done
EOF

chmod +x monitor.sh
./monitor.sh
```

## Stop Services

When done testing:
```bash
# Stop all services
docker-compose -f docker-compose.network.yml down

# Stop and remove volumes
docker-compose -f docker-compose.network.yml down -v
```