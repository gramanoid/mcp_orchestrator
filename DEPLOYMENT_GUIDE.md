# MCP Orchestrator Deployment Guide

## Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone <repository>
cd mcp_orchestrator

# Set up environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Source environment
source .env
export OPENROUTER_API_KEY
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
python -m src.mcp_server_simple
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
MCP Client → MCP Server → Orchestrator → LLM Adapters → APIs
                ↓              ↓
            Tools      Strategies
```

### Components

1. **MCP Server** (`src/mcp_server_simple.py`)
   - Implements Model Context Protocol
   - Exposes tools: `reason`, `get_status`
   - Future: `review_code`, `think_deeper`

2. **Orchestrator** (`src/core/orchestrator.py`)
   - Manages LLM adapters
   - Executes strategies
   - Tracks costs and usage

3. **Strategies**
   - **Progressive Deep Dive**: Cost-efficient escalation
   - **Max Quality Council**: Multi-model consensus

4. **Adapters**
   - Claude (Opus, Sonnet)
   - Gemini Pro
   - O3 (via OpenRouter)

## Configuration

### config/config.yaml

```yaml
models:
  claude-3-opus:
    provider: openrouter
    model_id: anthropic/claude-3-opus
    max_tokens: 4096
    temperature: 0.7
    
strategies:
  progressive_deep_dive:
    max_depth: 3
    confidence_threshold: 0.8
    
  max_quality_council:
    models:
      - claude-3-opus
      - gemini-pro
    require_consensus: true
```

## Testing

### Unit Tests
```bash
python test_simple.py
```

### Integration Tests (requires API key)
```bash
python test_integration.py
```

### Docker Tests
```bash
./test_docker.sh
```

## Production Deployment

### Security Considerations

1. **API Keys**: Use environment variables or secrets management
2. **Resource Limits**: Configure in docker-compose.yml
3. **Logging**: JSON structured logs for monitoring
4. **Non-root**: Runs as unprivileged user

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
docker-compose logs mcp-orchestrator
```

### API errors
- Check OPENROUTER_API_KEY is set
- Verify rate limits not exceeded
- Check logs for specific errors

### Import errors
- Ensure virtual environment activated
- Check Python version (3.11+)
- Verify all dependencies installed

## Next Steps

1. **Implement Enhanced Tools**
   - Complete code_review tool
   - Add think_deeper tool
   - Implement git integration

2. **Add More Strategies**
   - Specialist routing
   - Cost-optimized strategy
   - Custom strategy support

3. **Enhance Platform Support**
   - Native Windows/Mac scripts
   - WSL bridge support
   - Cloud deployment templates

## Support

- Documentation: See /docs directory
- Issues: GitHub issues
- Logs: Check /app/logs in container