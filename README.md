# MCP Orchestrator

A sophisticated Model Context Protocol (MCP) server that orchestrates external AI models (Gemini 2.5 Pro and O3) to enhance Claude's responses with additional perspectives and insights. Following MCP best practices for secure, scalable deployment.

## Architecture Overview

When you interact with Claude in Claude Code, this MCP server allows Claude to consult external models:
- **Gemini 2.5 Pro** (via OpenRouter): Provides alternative analysis and perspectives
- **O3** (via OpenAI): Offers architectural and system design insights

## Features

- **External Model Enhancement**: Get perspectives from Gemini 2.5 Pro and O3 to supplement Claude's responses
- **Advanced Reasoning Strategies**: External enhancement and multi-model council approaches
- **MCP-Compliant**: Full adherence to Model Context Protocol standards
- **Secure by Design**: Non-root execution, encrypted storage, API key protection
- **Docker Support**: Production-ready containerization with health checks
- **Cost Controls**: Built-in request and daily spending limits

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/gramanoid/mcp_orchestrator
cd mcp_orchestrator

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# OPENROUTER_API_KEY=your_openrouter_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here (for O3)
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
│   User   │────▶│Claude (You) │────▶│MCP Orchestra │────▶│External Models│
└──────────┘     │in Claude Code│     │   tor        │     │Gemini 2.5 Pro│
                 └─────────────┘     └──────────────┘     │     O3       │
                                                           └──────────────┘
```

The flow:
1. User asks Claude a question
2. Claude (in Claude Code) can use MCP tools to get external perspectives
3. MCP Orchestrator queries Gemini 2.5 Pro and/or O3
4. External insights enhance Claude's response to the user

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
strategies:
  external_enhancement:
    models:
      - "google/gemini-2.5-pro-preview"  # via OpenRouter
      - "o3"  # via OpenAI
    
  max_quality_council:
    models:
      - "google/gemini-2.5-pro-preview"
      - "o3"
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