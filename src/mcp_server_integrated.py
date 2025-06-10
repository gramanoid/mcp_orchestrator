#!/usr/bin/env python3
"""
Integrated MCP Server for Claude Code.

This server provides orchestration tools that can be used directly from Claude Code.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Add src to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import MCPOrchestrator
from core.task import Task
from config.manager import ConfigManager
from tools.code_review import CodeReviewTool
from tools.think_deeper import ThinkDeeperTool
from tools.review_changes import ReviewChangesTool
from tools.multi_model_review import MultiModelReviewTool
from tools.quick_claude import QuickClaudeTool


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server with a descriptive name
server = Server("mcp-orchestrator")

# Global orchestrator instance
orchestrator = None

# Tool registry
TOOLS = {}


async def initialize_orchestrator():
    """Initialize the orchestrator and tools."""
    global orchestrator, TOOLS
    
    # Load configuration
    config = {
        'api_keys': {
            'openrouter': os.getenv('OPENROUTER_API_KEY')
        },
        'orchestration': {
            'default_strategy': 'progressive_deep_dive'
        }
    }
    
    # Create orchestrator
    orchestrator = MCPOrchestrator(config)
    await orchestrator.initialize()
    
    # Initialize tools with orchestrator
    TOOLS = {
        "multi_model_review": MultiModelReviewTool(orchestrator),
        "quick_claude": QuickClaudeTool(orchestrator),
        "review_code": CodeReviewTool(orchestrator),
        "think_deeper": ThinkDeeperTool(orchestrator),
        "review_changes": ReviewChangesTool(orchestrator),
    }
    
    logger.info("MCP Orchestrator initialized with all tools")


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available tools for Claude Code."""
    if not TOOLS:
        await initialize_orchestrator()
    
    tools = []
    
    # Add all specialized tools
    for tool_name, tool_instance in TOOLS.items():
        tools.append(types.Tool(
            name=tool_name,
            description=tool_instance.get_description(),
            inputSchema=tool_instance.get_input_schema()
        ))
    
    # Add direct orchestration tool
    tools.append(types.Tool(
        name="orchestrate",
        description=(
            "Direct orchestration control. Use specific strategy and options. "
            "Responses include model usage summary."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task or question to process"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["progressive_deep_dive", "max_quality_council"],
                    "description": "Orchestration strategy to use"
                },
                "code_context": {
                    "type": "string",
                    "description": "Optional code context"
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth for reasoning"
                }
            },
            "required": ["task"]
        }
    ))
    
    # Add status tool
    tools.append(types.Tool(
        name="orchestrator_status",
        description="Get orchestrator status, available models, and configuration",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ))
    
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[types.TextContent]:
    """Handle tool calls from Claude Code."""
    if not orchestrator:
        await initialize_orchestrator()
    
    try:
        # Handle specialized tools
        if name in TOOLS:
            tool = TOOLS[name]
            result = await tool.execute(arguments)
            
            return [types.TextContent(
                type="text",
                text=result.content
            )]
        
        # Handle direct orchestration
        elif name == "orchestrate":
            task_desc = arguments.get("task", "")
            thinking_mode = arguments.get("thinking_mode", "medium")
            
            # Add thinking mode to description if specified
            if thinking_mode != "medium":
                task_desc = f"Use {thinking_mode} thinking: {task_desc}"
            
            task = Task(
                description=task_desc,
                code_context=arguments.get("code_context"),
                session_context={
                    "strategy": arguments.get("strategy", "progressive_deep_dive")
                }
            )
            
            response = await orchestrator.orchestrate(
                task,
                strategy_override=arguments.get("strategy")
            )
            
            return [types.TextContent(
                type="text",
                text=response.content
            )]
        
        # Handle status
        elif name == "orchestrator_status":
            status = {
                "status": "active",
                "available_models": list(orchestrator.adapters.keys()),
                "available_strategies": list(orchestrator.strategies.keys()),
                "tools_available": list(TOOLS.keys()),
                "default_strategy": orchestrator.default_strategy,
                "total_requests": orchestrator._request_count,
                "total_cost": f"${orchestrator._total_cost:.4f}"
            }
            
            status_text = "🤖 MCP Orchestrator Status\n" + "=" * 40 + "\n"
            for key, value in status.items():
                status_text += f"{key}: {value}\n"
            
            return [types.TextContent(
                type="text",
                text=status_text
            )]
        
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting MCP Orchestrator Server...")
    
    # Initialize orchestrator on startup
    await initialize_orchestrator()
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())