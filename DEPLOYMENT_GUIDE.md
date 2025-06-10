# MCP Orchestrator Deployment Guide

**Note**: The MCP Orchestrator uses ONLY external models (Gemini 2.5 Pro and O3). It does NOT use Claude models since users are already interacting with Claude directly.

## Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone <repository>
cd mcp_orchestrator

# Set up environment
cp .env.example .env
# Edit .env and add your API keys
# Required: OPENROUTER_API_KEY (for Gemini 2.5 Pro)
# Required: OPENAI_API_KEY (for O3)

# Source environment
source .env
export OPENROUTER_API_KEY
export OPENAI_API_KEY
```

### 2. Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_simple.py

# Run MCP server
python -m src.mcp_server
```

### 3. Docker Deployment

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs

# Run tests
docker-compose --profile test run --rm mcp-test

# Stop
docker-compose down
```

## Architecture Overview

```
MCP Client → MCP Server → Orchestrator → External Model Adapters → APIs
                ↓              ↓                    ↓
            Tools      Strategies          Gemini Pro + O3
                                          (NO Claude models)
```

### Network Bridges (NEW)
```
Any Application → REST API (5050) → MCP Server → External Models
                → WebSocket (8765) →
```

### Components

1. **MCP Server** (`src/mcp_server.py`)
   - Implements Model Context Protocol
   - Exposes 13 tools including:
     - `orchestrate_task`, `query_specific_model`
     - `code_review`, `think_deeper`, `multi_model_review`
     - `comparative_analysis`, `review_changes`
     - `quick_claude` (deprecated - returns error)

2. **Orchestrator** (`src/core/orchestrator.py`)
   - Manages external model adapters ONLY
   - Executes strategies
   - Tracks costs and usage
   - Fixed: ResponseSynthesizer and lifecycle issues

3. **Strategies**
   - **External Enhancement**: Uses external models for additional insights
   - **Max Quality Council**: Multi-model consensus from external models

4. **External Model Adapters**
   - Gemini 2.5 Pro (via OpenRouter)
   - O3 (via OpenAI)
   - NO Claude adapters (users already have Claude)

5. **Network Bridges** (NEW)
   - REST API (`rest_api.py`) - Port 5050
   - WebSocket Bridge (`websocket_bridge.py`) - Port 8765
   - Docker Compose network configuration

## Configuration

### config/config.yaml

```yaml
models:
  gemini_pro:
    provider: openrouter
    model_id: google/gemini-2.5-pro-preview
    max_tokens: 32768
    temperature: 0.7
    
  o3_architect:
    provider: openai
    model_id: o3
    max_tokens: 16384
    temperature: 0.8
    
strategies:
  external_enhancement:
    models:
      - gemini_pro
      - o3_architect
    
  max_quality_council:
    models:
      - gemini_pro
      - o3_architect
    require_consensus: true
```

## Testing

### Quick Test
```bash
# Start all services and run tests
./quick_test.sh
```

### Unit Tests
```bash
python -m pytest tests/
```

### Integration Tests (requires API keys)
```bash
python examples/integration_example.py
```

### Docker Tests
```bash
./test_docker_deployment.sh
```

### Network Bridge Tests
```bash
# Start services
./start_network_services.sh

# Test REST API
curl -X POST http://localhost:5050/mcp/get_orchestrator_status

# Test WebSocket (see examples/)
```

## Network Bridge Deployment

### Starting Network Services

```bash
# Start REST API and WebSocket bridges
./start_network_services.sh

# Or manually with Docker Compose
docker-compose -f docker-compose.network.yml up -d
```

### Accessing the Services

1. **REST API** (Port 5050)
   ```bash
   # Direct method call
   curl -X POST http://localhost:5050/mcp/orchestrate_task \
     -H "Content-Type: application/json" \
     -d '{"description": "Analyze this code"}''
   
   # Generic MCP call
   curl -X POST http://localhost:5050/mcp \
     -H "Content-Type: application/json" \
     -d '{"method": "get_orchestrator_status", "params": {}}'
   ```

2. **WebSocket** (Port 8765)
   - See `examples/integration_example.py` for WebSocket client example
   - Supports bidirectional MCP communication

## Production Deployment

### Security Considerations

1. **API Keys**: Use environment variables or secrets management
2. **Resource Limits**: Configure in docker-compose.yml
3. **Logging**: JSON structured logs for monitoring
4. **Non-root**: Runs as unprivileged user
5. **Network Security**: Use reverse proxy with HTTPS in production

### Monitoring

- Health checks every 30s
- Cost tracking in logs
- Structured logging for analysis

### Scaling

- Horizontal: Run multiple instances
- Vertical: Adjust memory/CPU limits
- Cost control: Configure daily limits

## Troubleshooting

### Container won't start
```bash
# Check main orchestrator
docker-compose logs mcp-orchestrator

# Check network services
docker-compose -f docker-compose.network.yml logs
```

### API errors
- Check both OPENROUTER_API_KEY and OPENAI_API_KEY are set
- Verify rate limits not exceeded
- Check logs for specific errors
- Ensure you're using external model names (gemini_pro, o3_architect)

### Import errors
- Ensure virtual environment activated
- Check Python version (3.11+)
- Verify all dependencies installed

## Current Status

✅ **Completed**:
- All 13 MCP tools implemented and working
- Network bridges (REST API + WebSocket) operational
- External model integration (Gemini 2.5 Pro + O3)
- All known bugs fixed (ResponseSynthesizer, lifecycle)
- Docker deployment fully functional

❌ **Not Supported**:
- Claude model adapters (removed - users already have Claude)
- Direct Claude orchestration (unnecessary)

## Integration Examples

See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for:
- Language-specific examples (Python, JS, Go, Rust, Java)
- CI/CD integration (GitHub Actions, GitLab)
- Docker Compose integration
- Security best practices

## Support

- Documentation: See /docs directory
- Issues: GitHub issues
- Logs: Check /app/logs in container