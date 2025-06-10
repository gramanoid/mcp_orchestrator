#!/bin/bash
# One-line installer for MCP Orchestrator

echo "🚀 Installing MCP Orchestrator..."

# Check if running with curl or wget
if [ -z "$1" ]; then
    echo "Cloning repository..."
    git clone https://github.com/yourusername/mcp_orchestrator.git /tmp/mcp_orchestrator
    cd /tmp/mcp_orchestrator
else
    echo "Using provided directory: $1"
    cd "$1"
fi

# Run deployment
if [ -f deploy_mcp.sh ]; then
    ./deploy_mcp.sh
else
    echo "❌ Deployment script not found!"
    echo "Please run from the MCP orchestrator directory"
    exit 1
fi