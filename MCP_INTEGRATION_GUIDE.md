# MCP Orchestrator Integration Guide

## How to Use MCP Orchestrator Across Different Applications

### Understanding MCP Communication
MCP (Model Context Protocol) servers communicate via stdio (stdin/stdout), not HTTP. This means they don't expose network ports like traditional APIs.

## Integration Options

### 1. **Claude Desktop App Integration**
Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mcp-orchestrator": {
      "command": "docker",
      "args": ["run", "--rm", "-i", 
               "--env-file", "/path/to/your/.env",
               "mcp-orchestrator:latest",
               "python", "-m", "src.mcp_server"]
    }
  }
}
```

### 2. **VS Code Integration (with Continue.dev)**
If using Continue.dev extension, add to `.continue/config.json`:

```json
{
  "models": [{
    "title": "Claude with External Models",
    "provider": "anthropic",
    "model": "claude-3-sonnet",
    "contextProviders": [{
      "name": "mcp-orchestrator",
      "params": {
        "command": "docker run --rm -i --env-file /path/to/.env mcp-orchestrator:latest python -m src.mcp_server"
      }
    }]
  }]
}
```

### 3. **Network-Accessible MCP Bridge**
To make MCP available over network, create a bridge service:

```yaml
# docker-compose.mcp-bridge.yml
version: '3.8'

services:
  mcp-bridge:
    build:
      context: .
      dockerfile: Dockerfile.bridge
    ports:
      - "8765:8765"  # WebSocket port
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    command: python -m mcp_bridge
```

Create the bridge script:

```python
# mcp_bridge.py
import asyncio
import websockets
import json
import subprocess
import os

async def handle_client(websocket):
    """Bridge WebSocket requests to MCP server via stdio."""
    process = await asyncio.create_subprocess_exec(
        'python', '-m', 'src.mcp_server',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ}
    )
    
    async def read_from_mcp():
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await websocket.send(line.decode())
    
    asyncio.create_task(read_from_mcp())
    
    try:
        async for message in websocket:
            process.stdin.write(message.encode() + b'\n')
            await process.stdin.drain()
    finally:
        process.terminate()
        await process.wait()

async def main():
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. **Direct Docker Execution from Apps**
Applications can directly spawn the Docker container:

```python
# Python example
import subprocess
import json

def query_mcp_orchestrator(request):
    """Query MCP orchestrator from any Python app."""
    process = subprocess.Popen(
        ['docker', 'run', '--rm', '-i', '--env-file', '.env',
         'mcp-orchestrator:latest', 'python', '-m', 'src.mcp_server'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send request
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()
    
    # Read response
    response = process.stdout.readline()
    return json.loads(response)

# Usage
result = query_mcp_orchestrator({
    "method": "orchestrate_task",
    "params": {
        "description": "Analyze this architecture decision"
    }
})
```

### 5. **Using Docker Compose for Multi-Service Setup**

```yaml
# docker-compose.full-stack.yml
version: '3.8'

services:
  # Your main application
  app:
    build: ./app
    environment:
      - MCP_ORCHESTRATOR_COMMAND=docker run --rm -i mcp-orchestrator:latest python -m src.mcp_server
    depends_on:
      - mcp-orchestrator
  
  # MCP Orchestrator (built but not running - spawned on demand)
  mcp-orchestrator:
    build:
      context: ./mcp_orchestrator
    image: mcp-orchestrator:latest
    profiles:
      - build-only
```

## Best Practices

1. **Environment Variables**: Always use `--env-file` to pass API keys securely
2. **Resource Limits**: Use `--memory` and `--cpus` flags to limit resource usage
3. **Logging**: Mount a volume for logs: `-v ./logs:/app/logs`
4. **Security**: Run with `--read-only` and `--security-opt no-new-privileges`

## Example: Full Integration Command

```bash
docker run \
  --rm \
  -i \
  --env-file /path/to/.env \
  --memory="2g" \
  --cpus="2.0" \
  --read-only \
  --security-opt no-new-privileges \
  -v $(pwd)/logs:/app/logs \
  mcp-orchestrator:latest \
  python -m src.mcp_server
```

## Verifying Integration

Test your integration:

```bash
# Test with echo
echo '{"method": "get_orchestrator_status", "params": {}}' | \
  docker run --rm -i --env-file .env mcp-orchestrator:latest python -m src.mcp_server

# Should return status JSON
```

## Common Issues

1. **Container exits immediately**: MCP servers need `-i` (interactive) flag
2. **No response**: Ensure stdio is properly connected
3. **Permission denied**: Check Docker socket permissions
4. **API errors**: Verify environment variables are passed correctly

## Network Alternative: REST API Wrapper

If you need HTTP/REST access, create a wrapper:

```python
# rest_wrapper.py
from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    data = request.json
    
    process = subprocess.run(
        ['docker', 'run', '--rm', '-i', '--env-file', '.env',
         'mcp-orchestrator:latest', 'python', '-m', 'src.mcp_server'],
        input=json.dumps(data),
        capture_output=True,
        text=True
    )
    
    return jsonify(json.loads(process.stdout))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

This allows HTTP access:
```bash
curl -X POST http://localhost:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "orchestrate_task", "params": {"description": "Test task"}}'
```