"""
MCP (Model Context Protocol) Server for the Multi-Code-LLM Orchestrator.

This module implements an MCP server that exposes the orchestrator's capabilities
as tools that can be used by Claude Code and other MCP-compatible clients.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

# Setup proper import path
import sys
from pathlib import Path

# Add parent directory to path to enable imports
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import MCPOrchestrator
from core.task import Task, TaskAnalysis, TaskType, ComplexityLevel, ImpactLevel
from config.manager import ConfigManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("mcp-orchestrator")

# Global orchestrator instance and state
orchestrator = None
config_manager = ConfigManager()
session_context = {}


def read_file_content(file_path: str, max_size: int = 50000) -> str:
    """Read file content with size limit."""
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        
        if path.stat().st_size > max_size:
            return f"File too large: {file_path} (>{max_size} bytes)"
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def read_codebase_files(base_path: str, patterns: List[str] = None) -> Dict[str, str]:
    """Read relevant files from a codebase."""
    if patterns is None:
        patterns = ['*.py', '*.md', '*.yaml', '*.yml', '*.json']
    
    files_content = {}
    base = Path(base_path)
    
    # Read key files first
    key_files = ['README.md', 'DESIGN.md', 'CLAUDE.md', 'setup.py', 'requirements.txt']
    for file_name in key_files:
        file_path = base / file_name
        if file_path.exists():
            files_content[str(file_path)] = read_file_content(str(file_path))
    
    # Read source files
    for pattern in patterns:
        for file_path in base.rglob(pattern):
            # Skip large files, cache, and virtual environments
            if any(skip in str(file_path) for skip in ['venv/', '__pycache__/', '.git/', 'node_modules/']):
                continue
            
            # Limit total files read
            if len(files_content) > 50:
                break
                
            rel_path = file_path.relative_to(base)
            files_content[str(rel_path)] = read_file_content(str(file_path))
    
    return files_content


def format_codebase_context(files_content: Dict[str, str], task_description: str) -> str:
    """Format codebase content into a structured context."""
    context_parts = [
        f"Task: {task_description}",
        "\n=== CODEBASE ANALYSIS ===\n"
    ]
    
    # Add file contents
    for file_path, content in files_content.items():
        if content and not content.startswith("Error") and not content.startswith("File"):
            context_parts.append(f"\n--- File: {file_path} ---\n{content[:5000]}...")  # Limit per file
            
    return "\n".join(context_parts)


def _recommend_strategy(analysis: TaskAnalysis) -> str:
    """Recommend an orchestration strategy based on task analysis."""
    if (analysis.complexity.value >= 4 or 
        analysis.requires_multiple_perspectives or
        analysis.estimated_impact.value >= 4):
        return "max_quality_council"
    else:
        return "progressive_deep_dive"


async def initialize_orchestrator():
    """Initialize the orchestrator if not already initialized."""
    global orchestrator
    
    if orchestrator is None:
        try:
            # Load configuration
            config = config_manager.load_config()
            
            # Initialize orchestrator
            orchestrator = MCPOrchestrator(config)
            await orchestrator.initialize()
            
            logger.info("MCP Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="analyze_task",
            description="Analyze a coding task to determine optimal LLM selection strategy",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of the task"
                    },
                    "code_context": {
                        "type": "string",
                        "description": "Optional code snippets or file contents"
                    },
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of file paths involved"
                    }
                },
                "required": ["description"]
            }
        ),
        types.Tool(
            name="orchestrate_task",
            description="Process a coding task using the optimal LLM or combination of LLMs",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of the task"
                    },
                    "code_context": {
                        "type": "string",
                        "description": "Optional code snippets or file contents"
                    },
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of file paths involved"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Optional strategy override: max_quality_council or progressive_deep_dive"
                    },
                    "preferences": {
                        "type": "object",
                        "description": "Optional user preferences dictionary"
                    }
                },
                "required": ["description"]
            }
        ),
        types.Tool(
            name="query_specific_model",
            description="Query a specific LLM model directly",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Model identifier: claude_opus, claude_sonnet, gemini_polyglot, or o3_architect"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "code_context": {
                        "type": "string",
                        "description": "Optional code context"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Optional model-specific parameters"
                    }
                },
                "required": ["model", "description"]
            }
        ),
        types.Tool(
            name="code_review",
            description="Professional code review with multi-model analysis. Identifies bugs, security issues, and improvements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files or directories to review"
                    },
                    "review_type": {
                        "type": "string",
                        "enum": ["full", "security", "performance", "quick"],
                        "default": "full",
                        "description": "Type of review to perform"
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific areas to focus on"
                    },
                    "severity_filter": {
                        "type": "string",
                        "enum": ["all", "high", "critical"],
                        "default": "all",
                        "description": "Minimum severity level to report"
                    }
                },
                "required": ["files"]
            }
        ),
        types.Tool(
            name="think_deeper",
            description="Extended reasoning using advanced models for complex problems. Best for architectural decisions and difficult bugs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "problem": {
                        "type": "string",
                        "description": "Complex problem or question to analyze"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context or constraints"
                    },
                    "thinking_mode": {
                        "type": "string",
                        "enum": ["minimal", "low", "medium", "high", "max"],
                        "default": "high",
                        "description": "Depth of reasoning required"
                    }
                },
                "required": ["problem"]
            }
        ),
        types.Tool(
            name="multi_model_review",
            description="Get perspectives from multiple models on the same problem. Shows how different AI models approach the task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task or question for multi-model analysis"
                    },
                    "models": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific models to use (default: all available)"
                    },
                    "compare_approaches": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include comparison of different approaches"
                    }
                },
                "required": ["task"]
            }
        ),
        types.Tool(
            name="comparative_analysis",
            description="Compare different solutions or approaches using multiple models. Great for architecture decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of options to compare"
                    },
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Evaluation criteria (e.g., performance, maintainability, cost)"
                    },
                    "context": {
                        "type": "string",
                        "description": "Project context and constraints"
                    }
                },
                "required": ["options"]
            }
        ),
        types.Tool(
            name="review_changes",
            description="Review git changes before committing. Validates against requirements, finds incomplete implementations, and security issues.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Repository paths to review (defaults to current directory)"
                    },
                    "include_untracked": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include untracked files in review"
                    },
                    "original_request": {
                        "type": "string",
                        "description": "Original task/requirement to validate against"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="quick_claude",
            description="Get a quick response using only Claude. Fast and cost-effective for simple tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task or question for Claude"
                    },
                    "code_context": {
                        "type": "string",
                        "description": "Optional code context"
                    },
                    "thinking_mode": {
                        "type": "string",
                        "enum": ["minimal", "low", "medium"],
                        "default": "low",
                        "description": "Thinking depth (kept low for speed)"
                    }
                },
                "required": ["task"]
            }
        ),
        types.Tool(
            name="get_orchestrator_status",
            description="Get the current status and statistics of the orchestrator",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="update_session_context",
            description="Update the session context for subsequent orchestrations",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "object",
                        "description": "Dictionary of context information to merge"
                    }
                },
                "required": ["context"]
            }
        ),
        types.Tool(
            name="configure_orchestrator",
            description="Configure orchestrator settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "strategy": {
                        "type": "string",
                        "description": "Default strategy: max_quality_council or progressive_deep_dive"
                    },
                    "cost_limit": {
                        "type": "number",
                        "description": "Maximum cost per request in USD"
                    },
                    "quality_mode": {
                        "type": "string",
                        "description": "Quality preference: maximum, balanced, or efficient"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Execute a tool."""
    
    # Ensure orchestrator is initialized
    await initialize_orchestrator()
    
    try:
        if name == "analyze_task":
            # Extract arguments
            description = arguments.get("description", "")
            code_context = arguments.get("code_context")
            file_paths = arguments.get("file_paths", [])
            
            # If analyzing a codebase, read the files
            if not code_context and ("analyze" in description.lower() and 
                ("codebase" in description.lower() or "folder" in description.lower() or 
                 "project" in description.lower() or "open folder" in description.lower())):
                
                # Try to extract path from description or use current directory
                base_path = os.getcwd()
                
                # Check if a specific path is mentioned
                if "mcp_orchestrator" in description.lower():
                    potential_path = "/home/alexgrama/GitHome/mcp_orchestrator"
                    if os.path.exists(potential_path):
                        base_path = potential_path
                
                # Read codebase files
                files_content = read_codebase_files(base_path)
                
                # Format into context
                code_context = format_codebase_context(files_content, description)
            
            # Create task object
            task = Task(
                description=description,
                code_context=code_context,
                file_paths=file_paths,
                session_context=session_context
            )
            
            # Analyze task
            analyzer = orchestrator.task_analyzer
            analysis = analyzer.analyze(task)
            
            # Format response
            result = {
                "task_type": analysis.task_type.name,
                "complexity": analysis.complexity.name,
                "estimated_impact": analysis.estimated_impact.name,
                "recommended_strategy": _recommend_strategy(analysis),
                "requires_multiple_perspectives": analysis.requires_multiple_perspectives,
                "languages_detected": analysis.languages_detected,
                "frameworks_detected": analysis.frameworks_detected,
                "requires_deep_reasoning": analysis.requires_deep_reasoning,
                "confidence_score": analysis.confidence_score
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        elif name == "orchestrate_task":
            # Extract arguments
            description = arguments.get("description", "")
            code_context = arguments.get("code_context")
            file_paths = arguments.get("file_paths", [])
            strategy = arguments.get("strategy")
            preferences = arguments.get("preferences", {})
            
            # If analyzing a codebase, read the files
            if not code_context and ("analyze" in description.lower() and 
                ("codebase" in description.lower() or "folder" in description.lower() or 
                 "project" in description.lower() or "open folder" in description.lower())):
                
                # Try to extract path from description or use current directory
                base_path = os.getcwd()
                
                # Check if a specific path is mentioned
                if "mcp_orchestrator" in description.lower():
                    potential_path = "/home/alexgrama/GitHome/mcp_orchestrator"
                    if os.path.exists(potential_path):
                        base_path = potential_path
                
                # Read codebase files
                logger.info(f"Reading codebase files from: {base_path}")
                files_content = read_codebase_files(base_path)
                
                # Format into context
                code_context = format_codebase_context(files_content, description)
                logger.info(f"Read {len(files_content)} files, context size: {len(code_context)} chars")
            
            # Create task object
            task = Task(
                description=description,
                code_context=code_context,
                file_paths=file_paths,
                user_preferences=preferences,
                session_context=session_context
            )
            
            # Orchestrate task
            response = await orchestrator.orchestrate(task, strategy_override=strategy)
            
            # Format the response to be more readable
            content = response.content
            
            # Extract and format the usage summary if present
            usage_summary = ""
            if "🤖 Models:" in content or "💰 Cost:" in content:
                # Extract the usage summary line
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "🤖 Models:" in line or "💰 Cost:" in line:
                        usage_summary = line
                        # Remove it from content
                        lines[i] = ""
                        content = '\n'.join(lines).strip()
            
            # Create a clean formatted response
            formatted_response = content
            
            # Add enhanced metadata
            metadata_lines = []
            if usage_summary:
                metadata_lines.append(usage_summary)
            
            # Add confidence score
            if response.confidence_score:
                metadata_lines.append(f"📊 Confidence: {response.confidence_score:.2f}")
            
            # Add strategy used
            if response.metadata.get("strategy"):
                metadata_lines.append(f"🎯 Strategy: {response.metadata['strategy']}")
            
            if metadata_lines:
                formatted_response = f"{content}\n\n---\n" + " | ".join(metadata_lines)
            
            # Add metadata about what was analyzed
            if code_context and "codebase" in description.lower():
                formatted_response = f"{formatted_response}\n\n[Analyzed {len(files_content)} files from the codebase]"
            
            return [types.TextContent(
                type="text",
                text=formatted_response
            )]
            
        elif name == "query_specific_model":
            # Extract arguments
            model = arguments.get("model", "")
            description = arguments.get("description", "")
            code_context = arguments.get("code_context")
            parameters = arguments.get("parameters", {})
            
            # Create task
            task = Task(
                description=description,
                code_context=code_context,
                session_context=session_context
            )
            
            # Get the appropriate adapter
            adapter = orchestrator.get_adapter(model)
            if not adapter:
                raise ValueError(f"Unknown model: {model}")
            
            # Query with maximum reasoning
            params = adapter.get_max_reasoning_params()
            if parameters:
                params.update(parameters)
            
            response = await adapter.query(task, **params)
            
            # Format response
            result = {
                "content": response.content,
                "model": response.model,
                "thinking_tokens_used": response.thinking_tokens_used,
                "total_tokens": response.total_tokens,
                "cost": response.cost,
                "metadata": response.metadata
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        elif name == "get_orchestrator_status":
            status = await orchestrator.get_status()
            
            return [types.TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )]
            
        elif name == "update_session_context":
            context = arguments.get("context", {})
            session_context.update(context)
            
            return [types.TextContent(
                type="text",
                text="Session context updated successfully"
            )]
            
        elif name == "configure_orchestrator":
            config_updates = {}
            
            if "strategy" in arguments:
                config_updates["default_strategy"] = arguments["strategy"]
            
            if "cost_limit" in arguments:
                config_updates["max_cost_per_request"] = arguments["cost_limit"]
            
            if "quality_mode" in arguments:
                config_updates["quality_mode"] = arguments["quality_mode"]
            
            config_manager.update_config(config_updates)
            
            return [types.TextContent(
                type="text",
                text=f"Configuration updated: {json.dumps(config_updates, indent=2)}"
            )]
            
        elif name == "code_review":
            # Import and initialize the tool
            from tools.code_review import CodeReviewTool
            tool = CodeReviewTool(orchestrator)
            
            # Execute the review
            result = await tool.execute(arguments)
            
            return [types.TextContent(
                type="text",
                text=result.content
            )]
            
        elif name == "think_deeper":
            # Import and initialize the tool
            from tools.think_deeper import ThinkDeeperTool
            tool = ThinkDeeperTool(orchestrator)
            
            # Execute deep thinking
            result = await tool.execute({
                "current_analysis": arguments.get("problem"),  # Map problem to current_analysis
                "problem_context": arguments.get("context"),
                "thinking_mode": arguments.get("thinking_mode", "high")
            })
            
            return [types.TextContent(
                type="text",
                text=result.content
            )]
            
        elif name == "multi_model_review":
            # Get task and models
            task_desc = arguments.get("task", "")
            models = arguments.get("models", ["claude-direct", "gemini", "o3"])
            
            # Create task for each model
            task = Task(
                description=task_desc,
                session_context={"multi_model": True}
            )
            
            # Query each model
            responses = {}
            for model in models:
                adapter = orchestrator.get_adapter(model)
                if adapter:
                    try:
                        response = await adapter.query(task)
                        responses[model] = response
                    except Exception as e:
                        logger.error(f"Failed to query {model}: {e}")
            
            # Format multi-model output
            output = ["# Multi-Model Analysis\n"]
            total_cost = 0
            
            for model, response in responses.items():
                output.append(f"## {model.upper()} Perspective")
                confidence = response.confidence_score if response.confidence_score else "N/A"
                output.append(f"*Cost: ${response.cost:.4f} | Tokens: {response.total_tokens:,} | Confidence: {confidence}*\n")
                output.append(response.content)
                output.append("\n---\n")
                total_cost += response.cost
            
            # Add comparison if requested
            if arguments.get("compare_approaches", True):
                output.append("## Approach Comparison")
                output.append("Each model brings unique strengths:")
                output.append("- **Claude**: Deep reasoning and nuanced understanding")
                output.append("- **Gemini**: Large context analysis and pattern recognition")
                output.append("- **O3**: Architectural insights and system design")
                output.append(f"\n**Total Cost**: ${total_cost:.4f}")
            
            return [types.TextContent(
                type="text",
                text="\n".join(output)
            )]
            
        elif name == "comparative_analysis":
            # Import and initialize the tool
            from tools.comparative_analysis import ComparativeAnalysisTool
            tool = ComparativeAnalysisTool(orchestrator)
            
            # Execute comparison
            result = await tool.execute(arguments)
            
            return [types.TextContent(
                type="text",
                text=result.content
            )]
            
        elif name == "review_changes":
            # Import and initialize the tool
            from tools.review_changes import ReviewChangesTool
            tool = ReviewChangesTool(orchestrator)
            
            # Execute git changes review
            result = await tool.execute(arguments)
            
            return [types.TextContent(
                type="text",
                text=result.content
            )]
            
        elif name == "quick_claude":
            # Import and initialize the tool
            from tools.quick_claude import QuickClaudeTool
            tool = QuickClaudeTool(orchestrator)
            
            # Execute with Claude only
            result = await tool.execute(arguments)
            
            return [types.TextContent(
                type="text",
                text=result.content
            )]
            
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Main entry point."""
    logger.info("Starting MCP Orchestrator server...")
    
    try:
        # Initialize orchestrator before starting server
        await initialize_orchestrator()
        
        # Start MCP server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
            
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Cleanup
        if orchestrator:
            await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())