# MCP Orchestrator

A sophisticated Model Context Protocol (MCP) server that orchestrates multiple LLMs for enhanced reasoning capabilities. Following MCP best practices for secure, scalable deployment.

## Features

- **Multi-Model Orchestration**: Coordinate Claude, Gemini, and other models
- **Advanced Reasoning Strategies**: Progressive deep dive and consensus-based council approaches
- **MCP-Compliant**: Full adherence to Model Context Protocol standards
- **Secure by Design**: Non-root execution, encrypted storage, API key protection
- **Docker Support**: Production-ready containerization with health checks
- **Cost Controls**: Built-in request and daily spending limits

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository>
cd mcp_orchestrator

# Copy environment template
cp .env.example .env

# Edit .env with your API key
# OPENROUTER_API_KEY=your_api_key_here
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

### 3. Use with MCP Clients

The orchestrator exposes the following tools via MCP:

- `reason`: Execute reasoning tasks with configurable strategies
- `get_status`: Check orchestrator health and statistics

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  MCP Client │────▶│ Orchestrator │────▶│  LLM APIs   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  Strategies  │
                    └──────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | Required |
| `MCP_LOG_LEVEL` | Logging level | INFO |
| `MCP_MAX_COST_PER_REQUEST` | Max cost per request ($) | 5.0 |
| `MCP_DAILY_LIMIT` | Daily spending limit ($) | 100.0 |

### Strategy Configuration

Edit `config/config.yaml` to customize:

```yaml
strategies:
  progressive_deep_dive:
    max_depth: 3
    initial_model: "anthropic/claude-3-opus"
    
  max_quality_council:
    models:
      - "anthropic/claude-3-opus"
      - "google/gemini-pro"
      - "openai/gpt-4"
    require_consensus: true
```

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