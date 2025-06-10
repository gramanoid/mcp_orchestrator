#!/bin/bash
# Run script for MCP Orchestrator

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

# Set API keys from environment or use defaults
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"

# Run the integrated MCP server
exec python3 "${SCRIPT_DIR}/src/mcp_server_integrated.py"