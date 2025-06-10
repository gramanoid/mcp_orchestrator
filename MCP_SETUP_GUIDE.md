# MCP Orchestrator Setup Guide

## Quick Setup for Claude Code

### 1. Add the MCP Server

```bash
# Navigate to your project directory
cd /home/alexgrama/GitHome/mcp_orchestrator

# Add the MCP server to Claude Code
claude mcp add mcp-orchestrator "python $(pwd)/src/mcp_server.py"

# Verify it's added
claude mcp list
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
# Required for external models
OPENROUTER_API_KEY=your_openrouter_key_here
OPENAI_API_KEY=your_openai_key_here  # For O3 model
```

### 3. Test the Installation

In Claude Code, you should now see these tools when typing `/`:
- `mcp__mcp-orchestrator__orchestrate_task`
- `mcp__mcp-orchestrator__analyze_task`
- `mcp__mcp-orchestrator__code_review`
- `mcp__mcp-orchestrator__think_deeper`
- `mcp__mcp-orchestrator__multi_model_review`
- `mcp__mcp-orchestrator__comparative_analysis`

## Troubleshooting WSL and IDE Issues

### Why MCP Tools Don't Show in `/mcp` Command

The `/mcp` command in Claude Code shows built-in MCP tools. Custom MCP servers appear with the `mcp__` prefix when you type `/`.

### Making MCP Work in WSL

1. **Ensure Python Path is Correct**:
   ```bash
   # Use full WSL path
   claude mcp add mcp-orchestrator "python3 /home/username/GitHome/mcp_orchestrator/src/mcp_server.py"
   ```

2. **Check Python Version**:
   ```bash
   python3 --version  # Should be 3.8+
   ```

3. **Install Dependencies**:
   ```bash
   cd /home/alexgrama/GitHome/mcp_orchestrator
   pip install -r requirements.txt
   ```

4. **Test MCP Server Manually**:
   ```bash
   # This should start without errors
   python3 src/mcp_server.py
   ```

### Using in Other IDEs (Windsurf, VS Code, etc.)

Currently, only Claude Code and Claude Desktop support MCP protocol. For other IDEs:

#### Option 1: REST API Wrapper (Recommended)

Create `rest_wrapper.py`:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import sys
sys.path.append('/home/alexgrama/GitHome/mcp_orchestrator/src')

from core.orchestrator import MCPOrchestrator
from core.task import Task
from config.manager import ConfigManager

app = FastAPI()
orchestrator = None

class TaskRequest(BaseModel):
    description: str
    code_context: str = None
    strategy: str = "progressive_deep_dive"

@app.on_event("startup")
async def startup():
    global orchestrator
    config = ConfigManager().load_config()
    orchestrator = MCPOrchestrator(config)
    await orchestrator.initialize()

@app.post("/orchestrate")
async def orchestrate(request: TaskRequest):
    task = Task(
        description=request.description,
        code_context=request.code_context
    )
    response = await orchestrator.orchestrate(task, strategy_override=request.strategy)
    return {
        "content": response.content,
        "cost": response.cost,
        "models_used": response.metadata.get("models_used", [])
    }

# Run with: uvicorn rest_wrapper:app --reload
```

Then in any IDE, call:
```bash
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description": "analyze this codebase"}'
```

#### Option 2: CLI Wrapper

Create `cli_orchestrator.py`:

```python
#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
sys.path.append('/home/alexgrama/GitHome/mcp_orchestrator/src')

from core.orchestrator import MCPOrchestrator
from core.task import Task
from config.manager import ConfigManager

async def main():
    parser = argparse.ArgumentParser(description='MCP Orchestrator CLI')
    parser.add_argument('command', choices=['analyze', 'orchestrate', 'review'])
    parser.add_argument('description', help='Task description')
    parser.add_argument('--strategy', default='progressive_deep_dive')
    parser.add_argument('--files', nargs='+', help='Files to analyze')
    
    args = parser.parse_args()
    
    config = ConfigManager().load_config()
    orchestrator = MCPOrchestrator(config)
    await orchestrator.initialize()
    
    task = Task(
        description=args.description,
        file_paths=args.files or []
    )
    
    if args.command == 'orchestrate':
        response = await orchestrator.orchestrate(task, strategy_override=args.strategy)
        print(response.content)
        print(f"\nCost: ${response.cost:.4f}")
    
    await orchestrator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

Use in any terminal:
```bash
./cli_orchestrator.py orchestrate "refactor this function for better performance" --files main.py
```

## Project-Specific MCP Configuration

For project-specific MCP servers, create `.mcp.json` in your project root:

```json
{
  "servers": {
    "mcp-orchestrator": {
      "command": "python",
      "args": ["/home/alexgrama/GitHome/mcp_orchestrator/src/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/home/alexgrama/GitHome/mcp_orchestrator"
      }
    }
  }
}
```

Then in that project directory:
```bash
# Claude Code will auto-detect and prompt to use this MCP server
cd /your/project
claude code .
```

## Debugging MCP Issues

1. **Check MCP Server Logs**:
   ```bash
   # Start server manually to see errors
   python3 src/mcp_server.py 2>&1 | tee mcp_debug.log
   ```

2. **Verify Tool Registration**:
   ```bash
   # In Claude Code
   /mcp list  # Shows registered servers
   ```

3. **Test Individual Tools**:
   ```python
   # test_mcp_tools.py
   import asyncio
   from mcp_server import call_tool
   
   async def test():
       result = await call_tool("get_orchestrator_status", {})
       print(result)
   
   asyncio.run(test())
   ```

## Best Practices

1. **Always specify working directory** when adding MCP servers
2. **Use absolute paths** in WSL to avoid path resolution issues
3. **Check Python environment** - virtual envs can cause issues
4. **Monitor costs** with `get_orchestrator_status` tool
5. **Start with `analyze_task`** to see recommended strategy before running expensive operations