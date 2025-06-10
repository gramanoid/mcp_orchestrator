# MCP Orchestrator Integration Examples

## Quick Start

1. **Start the network services:**
   ```bash
   ./start_network_services.sh
   ```

2. **Choose your integration method:**
   - REST API (port 5050)
   - WebSocket (port 8765)
   - Direct Docker execution

## Integration Examples by Language

### Python

```python
import requests

# Simple REST API call
response = requests.post('http://localhost:5050/mcp/orchestrate_task', 
    json={
        "description": "Analyze this architecture decision",
        "strategy": "external_enhancement"
    }
)
result = response.json()
print(result['result'])
```

### JavaScript/Node.js

```javascript
// REST API
const axios = require('axios');

async function queryMCP() {
    const response = await axios.post('http://localhost:5050/mcp', {
        method: 'query_specific_model',
        params: {
            model: 'gemini_pro',
            description: 'What are React best practices?'
        }
    });
    return response.data;
}

// WebSocket
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8765');

ws.on('open', () => {
    ws.send(JSON.stringify({
        method: 'get_orchestrator_status',
        params: {}
    }));
});

ws.on('message', (data) => {
    console.log('Received:', JSON.parse(data));
});
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

func queryMCP() {
    payload := map[string]interface{}{
        "method": "orchestrate_task",
        "params": map[string]interface{}{
            "description": "Compare SQL vs NoSQL databases",
        },
    }
    
    jsonData, _ := json.Marshal(payload)
    resp, err := http.Post("http://localhost:5050/mcp", 
                          "application/json", 
                          bytes.NewBuffer(jsonData))
    
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()
    
    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    fmt.Println(result)
}
```

### Rust

```rust
use reqwest;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    
    let response = client
        .post("http://localhost:5050/mcp/code_review")
        .json(&json!({
            "file_paths": ["src/main.rs"],
            "description": "Review for best practices"
        }))
        .send()
        .await?;
    
    let result: serde_json::Value = response.json().await?;
    println!("{}", result);
    
    Ok(())
}
```

### Java

```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public class MCPClient {
    private static final HttpClient client = HttpClient.newHttpClient();
    
    public static void queryMCP() throws Exception {
        String json = """
            {
                "method": "multi_model_review",
                "params": {
                    "task": "Design a scalable messaging system",
                    "focus_areas": ["reliability", "performance"]
                }
            }
            """;
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:5050/mcp"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();
        
        HttpResponse<String> response = client.send(request, 
            HttpResponse.BodyHandlers.ofString());
        
        System.out.println(response.body());
    }
}
```

### Shell/Bash

```bash
# Simple query
curl -X POST http://localhost:5050/mcp/query_specific_model \
  -H "Content-Type: application/json" \
  -d '{
    "model": "o3_architect",
    "description": "How to design a distributed cache?"
  }'

# With jq for pretty output
curl -s -X POST http://localhost:5050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "get_orchestrator_status",
    "params": {}
  }' | jq '.'

# Using environment variables
export MCP_ENDPOINT="http://localhost:5050"
curl -X POST "$MCP_ENDPOINT/mcp/orchestrate_task" \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"$TASK_DESCRIPTION\"}"
```

## Docker Integration

### From Docker Compose

```yaml
version: '3.8'

services:
  your-app:
    build: .
    environment:
      - MCP_API_URL=http://mcp-rest-api:5000
    depends_on:
      - mcp-rest-api
    networks:
      - mcp-network

networks:
  mcp-network:
    external: true
```

### Direct Docker Execution

```python
import subprocess
import json

def query_mcp_docker(method, params):
    request = json.dumps({"method": method, "params": params})
    
    result = subprocess.run([
        'docker', 'run', '--rm', '-i',
        '--env-file', '.env',
        'mcp-orchestrator:latest',
        'python', '-m', 'src.mcp_server'
    ], input=request, capture_output=True, text=True)
    
    return json.loads(result.stdout)
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run MCP Analysis
  run: |
    docker run --rm -i \
      -e OPENROUTER_API_KEY=${{ secrets.OPENROUTER_API_KEY }} \
      -e OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }} \
      mcp-orchestrator:latest \
      python -m src.mcp_server << EOF
    {"method": "code_review", "params": {"file_paths": ["src/"], "description": "PR review"}}
    EOF
```

### GitLab CI

```yaml
code-review:
  stage: test
  script:
    - |
      curl -X POST http://mcp-service:5050/mcp/code_review \
        -H "Content-Type: application/json" \
        -d "{\"file_paths\": [\"$CI_PROJECT_DIR/src\"], \"description\": \"Pipeline review\"}"
```

## Security Considerations

1. **API Authentication** (if needed):
   ```python
   # Add to rest_api.py
   @app.before_request
   def check_api_key():
       api_key = request.headers.get('X-API-Key')
       if api_key != os.getenv('MCP_API_KEY'):
           return jsonify({'error': 'Unauthorized'}), 401
   ```

2. **Rate Limiting**:
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(
       app=app,
       key_func=lambda: request.remote_addr,
       default_limits=["100 per hour"]
   )
   ```

3. **Network Security**:
   - Use HTTPS in production
   - Implement proper CORS policies
   - Use Docker networks for isolation

## Monitoring Integration

```python
# Prometheus metrics example
from prometheus_client import Counter, Histogram, generate_latest

mcp_requests = Counter('mcp_requests_total', 'Total MCP requests', ['method'])
mcp_latency = Histogram('mcp_request_duration_seconds', 'MCP request latency')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

## Troubleshooting

1. **Connection refused**: Check if services are running
   ```bash
   docker-compose -f docker-compose.network.yml ps
   ```

2. **Timeout errors**: Increase timeout in your client
   ```python
   requests.post(url, timeout=300)  # 5 minute timeout
   ```

3. **CORS issues**: Already handled by `flask-cors` in REST API

4. **Memory issues**: Adjust Docker limits in compose file