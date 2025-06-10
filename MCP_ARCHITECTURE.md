# MCP Orchestrator Architecture

## Core Principle: External Models Only

The MCP Orchestrator exclusively uses external AI models (Gemini 2.5 Pro and O3) to provide additional perspectives when using Claude. It does NOT orchestrate Claude itself since users are already interacting with Claude directly.

## How It Actually Works

When using Claude with MCP Orchestrator:

1. **Primary Response**: You ask a question → Claude responds directly
   - This is the normal Claude interaction
   - No MCP tools involved yet

2. **Enhancement via MCP Tools**: For additional perspectives:
   - `orchestrate_task` → Get external model insights on any task
   - `multi_model_review` → Gemini 2.5 Pro and O3 analyze the topic
   - `comparative_analysis` → Compare approaches using external models
   - `think_deeper` → Deep analysis from external models
   - `code_review` → External models review code
   - `query_specific_model` → Direct query to Gemini or O3

## Example Workflow

```
User: "Write a function to calculate fibonacci"
Claude: "Here's a fibonacci function: [provides code]"

User: "Use multi_model_review to get other perspectives"
MCP Tool: 
  - Sends task to Gemini 2.5 Pro: "Review this fibonacci implementation"
  - Sends task to O3: "Analyze the architecture of this solution"
  - Returns combined external insights
  - Does NOT query Claude (you already have Claude's response)
```

## Key Architecture Points

1. **Claude is NOT orchestrated** - Users already interact with Claude directly
2. **MCP orchestrates ONLY external models** - Gemini 2.5 Pro and O3
3. **Tools enhance, not replace** - They add external perspectives to Claude's responses
4. **Network bridges available** - REST API (5050) and WebSocket (8765) for integration

## Implementation Details

### External Model Adapters

1. **Gemini Adapter** (`adapters/gemini_adapter.py`)
   - Uses OpenRouter API
   - Model: `google/gemini-2.5-pro-preview`
   - Supports thinking modes and dynamic context

2. **O3 Adapter** (`adapters/o3_adapter.py`)
   - Uses OpenAI API directly
   - Model: `o3`
   - Specialized for architecture and system design

### Network Bridges

1. **REST API** (`rest_api.py`)
   - Flask-based HTTP API
   - Port 5050
   - CORS enabled for browser access

2. **WebSocket Bridge** (`websocket_bridge.py`)
   - Real-time bidirectional communication
   - Port 8765
   - Supports streaming responses

## System Architecture

### Direct MCP Integration
```
User Query
    ↓
Claude - Primary Response
    ↓
[Optional] MCP Tools
    ↓
MCP Orchestrator
    ↓
External Models Only
  - Gemini 2.5 Pro (via OpenRouter)
  - O3 (via OpenAI)
    ↓
Combined External Insights
```

### Network Bridge Architecture
```
Any Application
    ↓
REST API (5050) or WebSocket (8765)
    ↓
MCP Server (stdio bridge)
    ↓
MCP Orchestrator
    ↓
External Models Only
```

## Available Tools

### Core Orchestration
- **orchestrate_task**: Intelligently route tasks to external models
- **query_specific_model**: Direct query to Gemini or O3
- **analyze_task**: Analyze task complexity using external models

### Specialized Tools
- **multi_model_review**: Get multiple external perspectives
- **think_deeper**: Extended reasoning from external models
- **comparative_analysis**: Compare approaches using external models
- **code_review**: Professional code review from external models
- **review_changes**: Pre-commit validation using external models

### Configuration Tools
- **get_orchestrator_status**: View available models and statistics
- **configure_orchestrator**: Adjust settings and strategies
- **update_session_context**: Provide context for better responses

### Deprecated
- **quick_claude**: Returns error (users already have Claude)

## Strategies

1. **External Enhancement** (default)
   - Uses best external model for the task
   - Cost-efficient single model approach

2. **Max Quality Council**
   - Queries multiple external models in parallel
   - Synthesizes consensus from different perspectives
   - Higher cost but maximum insight

## Cost Management

- Per-request limits: $5.00 default
- Daily limits: $100.00 default
- Token optimization through thinking modes
- Usage tracking and reporting