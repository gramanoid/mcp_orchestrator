# MCP Orchestrator

A sophisticated Model Context Protocol (MCP) server that orchestrates external AI models (Gemini 2.5 Pro and O3) to provide additional perspectives and insights when using Claude. The orchestrator exclusively uses external models since users are already interacting with Claude directly.

## Architecture Overview

When you interact with Claude, this MCP server provides tools to consult external models for additional perspectives:
- **Gemini 2.5 Pro** (via OpenRouter): Alternative analysis and perspectives
- **O3** (via OpenAI): Architectural and system design insights

**Note**: The orchestrator does NOT use Claude models since you're already talking to Claude. It exclusively orchestrates external models to enhance your Claude experience.

## Features

- **External Model Enhancement**: Get perspectives from Gemini 2.5 Pro and O3 to supplement Claude's responses
- **Network Bridges**: REST API (port 5050) and WebSocket (port 8765) for integration with any application
- **Advanced Reasoning Strategies**: External enhancement and multi-model council approaches
- **MCP-Compliant**: Full adherence to Model Context Protocol standards
- **Secure by Design**: Non-root execution, encrypted storage, API key protection
- **Docker Support**: Production-ready containerization with health checks
- **Cost Controls**: Built-in request and daily spending limits
- **Bug-Free**: All known issues fixed including ResponseSynthesizer and lifecycle management

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/gramanoid/mcp_orchestrator
cd mcp_orchestrator

# Create .env file with your API keys
cat > .env << EOF
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

### 2. Deploy with Docker

```bash
# Deploy the service
./scripts/deploy.sh

# Check status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs
```

### 3. Start Network Services (Optional)

```bash
# Start REST API and WebSocket bridges for network access
./start_network_services.sh

# Test REST API
curl -X POST http://localhost:5050/mcp/get_orchestrator_status

# Test WebSocket (see examples/integration_example.py)
```

### 4. Use with MCP Clients

The orchestrator exposes 13 MCP tools that allow Claude to get external perspectives:

- `orchestrate_task`: Get external model perspectives on any task
- `analyze_task`: Analyze task complexity with external models
- `query_specific_model`: Query Gemini 2.5 Pro or O3 directly
- `code_review`: Get external code review perspectives
- `think_deeper`: Request deeper analysis from external models
- `multi_model_review`: Get multiple external perspectives
- `comparative_analysis`: Compare solutions using external models
- And more tools for specific use cases

## Architecture

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   User   │────▶│   Claude    │────▶│MCP Orchestra │────▶│External Models│
└──────────┘     │   (You)     │     │   tor        │     │Gemini 2.5 Pro│
                 └─────────────┘     └──────────────┘     │     O3       │
                        │                    ▲              └──────────────┘
                        │                    │
                        └────────────────────┘
                         MCP Tools Usage
```

The flow:
1. User asks Claude a question
2. Claude responds directly (primary interaction)
3. Claude can optionally use MCP tools to get external perspectives
4. MCP Orchestrator queries ONLY external models (Gemini 2.5 Pro and/or O3)
5. External insights are integrated into Claude's response

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key (for Gemini 2.5 Pro) | Required |
| `OPENAI_API_KEY` | Your OpenAI API key (for O3) | Required |
| `MCP_LOG_LEVEL` | Logging level | INFO |
| `MCP_MAX_COST_PER_REQUEST` | Max cost per request ($) | 5.0 |
| `MCP_DAILY_LIMIT` | Daily spending limit ($) | 100.0 |

### Strategy Configuration

Edit `config/config.yaml` to customize:

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

## Integration Options

### REST API
```python
import requests

response = requests.post('http://localhost:5050/mcp/orchestrate_task', 
    json={
        "description": "Analyze this architecture decision",
        "strategy": "external_enhancement"
    }
)
print(response.json()['result'])
```

### WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8765');
ws.send(JSON.stringify({
    method: 'query_specific_model',
    params: {
        model: 'gemini_pro',
        description: 'What are React best practices?'
    }
}));
```

See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) for more examples in various languages.

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run locally
python -m src.mcp_server
```

### Testing with Client

```python
# See scripts/mcp-client.py for example usage
python scripts/mcp-client.py
```

## Security

- Runs as non-root user in containers
- Read-only filesystem with specific writable volumes
- Encrypted credential storage
- No capabilities beyond essentials
- Resource limits enforced

## Monitoring

- JSON structured logging
- Health checks every 30s
- Log rotation (3 files, 10MB each)
- Cost tracking and limits

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Verify environment
docker-compose config
```

### API errors
- Verify API key in `.env`
- Check rate limits and quotas
- Review logs for specific errors

### Memory issues
- Adjust `mem_limit` in docker-compose.yml
- Monitor with `docker stats`

## License

MIT License - see LICENSE file for details