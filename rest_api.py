#!/usr/bin/env python3
"""REST API wrapper for MCP Orchestrator."""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from functools import wraps
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Global variables
orchestrator = None
tools = {}
start_time = time.time()


def async_to_sync(func):
    """Decorator to run async functions in sync context."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


@async_to_sync
async def initialize_orchestrator():
    """Initialize the orchestrator instance."""
    global orchestrator
    
    logger.info("[REST_INIT] Starting orchestrator initialization")
    
    from core.orchestrator import MCPOrchestrator
    orchestrator = MCPOrchestrator()
    await orchestrator.initialize()
    
    logger.info(f"[REST_INIT] Orchestrator initialized successfully, adapters: {list(orchestrator.adapters.keys())}")
    return orchestrator


def initialize_tools():
    """Initialize tool wrappers."""
    global tools, orchestrator
    
    logger.info("[REST_INIT] Initializing tool wrappers")
    
    # Create simple tool wrappers that call orchestrator methods
    tools = {
        "orchestrate_task": lambda **params: orchestrate_task_handler(**params),
        "analyze_task": lambda **params: analyze_task_handler(**params),
        "query_specific_model": lambda **params: query_specific_model_handler(**params),
        "get_orchestrator_status": lambda **params: get_status_handler(**params),
        "code_review": lambda **params: code_review_handler(**params),
        "multi_model_review": lambda **params: multi_model_review_handler(**params),
        "quick_claude": lambda **params: quick_claude_handler(**params),
    }
    
    logger.info(f"[REST_INIT] Initialized {len(tools)} tools")


@async_to_sync
async def orchestrate_task_handler(description, strategy=None, **kwargs):
    """Handle orchestrate_task requests."""
    from core.task import Task
    task = Task(description=description)
    
    # Use external_enhancement strategy by default
    if not strategy:
        strategy = "external_enhancement"
    
    response = await orchestrator.orchestrate(task, strategy_override=strategy)
    return response.to_dict()


@async_to_sync
async def analyze_task_handler(description, **kwargs):
    """Handle analyze_task requests."""
    from core.task import Task
    task = Task(description=description)
    analysis = orchestrator.task_analyzer.analyze(task)
    
    return {
        "task_type": analysis.task_type.value,
        "complexity": analysis.complexity.value,
        "estimated_tokens": analysis.estimated_tokens,
        "recommended_strategy": analysis.recommended_strategy,
        "key_requirements": analysis.key_requirements
    }


@async_to_sync
async def query_specific_model_handler(model, description, **kwargs):
    """Handle query_specific_model requests."""
    from core.task import Task
    
    # Map model names to adapter keys
    model_map = {
        "gemini_pro": "gemini_pro",
        "gemini": "gemini_pro",
        "o3": "o3_architect",
        "o3_architect": "o3_architect"
    }
    
    adapter_key = model_map.get(model, model)
    
    if adapter_key not in orchestrator.adapters:
        raise ValueError(f"Model {model} not available. Available models: {list(orchestrator.adapters.keys())}")
    
    task = Task(description=description)
    response = await orchestrator.adapters[adapter_key].query(task)
    return response.to_dict()


def get_status_handler(**kwargs):
    """Handle get_orchestrator_status requests."""
    runtime = time.time() - start_time
    
    return {
        "status": "active",
        "runtime_seconds": runtime,
        "request_count": orchestrator.request_count if orchestrator else 0,
        "total_cost": orchestrator.total_cost if orchestrator else 0.0,
        "models_available": list(orchestrator.adapters.keys()) if orchestrator else [],
        "strategies": ["external_enhancement", "max_quality_council", "progressive_deep_dive"],
        "default_strategy": "external_enhancement",
        "adapter_status": {
            name: "healthy" for name in (orchestrator.adapters.keys() if orchestrator else [])
        }
    }


@async_to_sync
async def code_review_handler(file_paths=None, description=None, **kwargs):
    """Handle code review requests."""
    from tools.code_review import CodeReviewTool
    tool = CodeReviewTool(orchestrator)
    result = await tool.execute(file_paths=file_paths, description=description, **kwargs)
    return result


@async_to_sync
async def multi_model_review_handler(task, **kwargs):
    """Handle multi-model review requests."""
    from tools.multi_model_review import MultiModelReviewTool
    tool = MultiModelReviewTool(orchestrator)
    result = await tool.execute(task=task, **kwargs)
    return result


@async_to_sync
async def quick_claude_handler(task, **kwargs):
    """Handle quick claude requests."""
    # For quick_claude, we'll use external models with minimal processing
    return await query_specific_model_handler("gemini_pro", task)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "mcp-orchestrator-rest-api",
        "timestamp": datetime.now().isoformat(),
        "orchestrator_initialized": orchestrator is not None,
        "runtime_seconds": time.time() - start_time
    })


@app.route('/tools', methods=['GET'])
def list_tools():
    """List available MCP tools."""
    return jsonify({
        "tools": [
            {
                "name": "orchestrate_task",
                "description": "Get external model perspectives on any task"
            },
            {
                "name": "analyze_task",
                "description": "Analyze task complexity with external models"
            },
            {
                "name": "query_specific_model",
                "description": "Query Gemini 2.5 Pro or O3 directly"
            },
            {
                "name": "code_review",
                "description": "Get external code review perspectives"
            },
            {
                "name": "multi_model_review",
                "description": "Get multiple external perspectives"
            },
            {
                "name": "get_orchestrator_status",
                "description": "Check orchestrator status and statistics"
            },
            {
                "name": "quick_claude",
                "description": "Fast task processing (uses external models)"
            }
        ]
    })


@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    """Main MCP endpoint."""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        method = data.get("method")
        params = data.get("params", {})
        
        if not method:
            return jsonify({"error": "Missing 'method' in request"}), 400
        
        # Check if tool exists
        if method not in tools:
            return jsonify({"error": f"Unknown tool: {method}"}), 404
        
        # Log request
        logger.info(f"[REST_REQUEST] Processing: {method}")
        
        # Call the tool
        try:
            result = tools[method](**params)
            
            # Format response
            return jsonify({
                "success": True,
                "result": json.dumps(result) if isinstance(result, dict) else result,
                "method": method,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[REST_ERROR] Tool execution failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "method": method
            }), 500
            
    except Exception as e:
        logger.error(f"[REST_ERROR] Request processing failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "method": method if 'method' in locals() else "unknown"
        }), 500


@app.route('/mcp/<tool_name>', methods=['POST'])
def mcp_tool_endpoint(tool_name):
    """Direct tool endpoint."""
    try:
        # Get request data
        params = request.get_json() or {}
        
        # Check if tool exists
        if tool_name not in tools:
            return jsonify({"error": f"Unknown tool: {tool_name}"}), 404
        
        # Log request
        logger.info(f"[REST_REQUEST] Direct tool call: {tool_name}")
        
        # Call the tool
        try:
            result = tools[tool_name](**params)
            
            # Format response
            return jsonify({
                "success": True,
                "result": json.dumps(result) if isinstance(result, dict) else result,
                "tool": tool_name,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[REST_ERROR] Tool execution failed: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "tool": tool_name
            }), 500
            
    except Exception as e:
        logger.error(f"[REST_ERROR] Request processing failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "tool": tool_name
        }), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation."""
    return jsonify({
        "service": "MCP Orchestrator REST API",
        "version": "1.0.0",
        "endpoints": {
            "GET /": "This documentation",
            "GET /health": "Health check",
            "GET /tools": "List available tools",
            "POST /mcp": "Execute MCP tool (method and params in body)",
            "POST /mcp/<tool_name>": "Execute specific tool (params in body)"
        },
        "example": {
            "endpoint": "POST /mcp",
            "body": {
                "method": "orchestrate_task",
                "params": {
                    "description": "What are the best practices for API design?",
                    "strategy": "external_enhancement"
                }
            }
        }
    })


if __name__ == '__main__':
    # Check for required environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)
    
    # O3 is optional
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - O3 will not be available")
    
    # Initialize the orchestrator
    logger.info("[REST_INIT] Initializing MCP Orchestrator REST API...")
    try:
        initialize_orchestrator()
        initialize_tools()
        logger.info("[REST_INIT] Initialization complete")
    except Exception as e:
        logger.error(f"[REST_INIT] Failed to initialize: {e}")
        sys.exit(1)
    
    # Run Flask app
    logger.info("[REST_LIFECYCLE] Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)