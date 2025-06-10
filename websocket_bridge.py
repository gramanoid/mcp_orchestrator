#!/usr/bin/env python3
"""WebSocket bridge for MCP Orchestrator - allows network access."""

import asyncio
import websockets
import json
import logging
import os
import sys
from typing import Optional
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPWebSocketBridge:
    """Bridge WebSocket connections to MCP orchestrator."""
    
    def __init__(self):
        self.clients = set()
        self.orchestrator = None
        self.start_time = time.time()
    
    async def initialize(self):
        """Initialize the orchestrator once."""
        if not self.orchestrator:
            logger.info("[WS_INIT] Initializing orchestrator")
            from core.orchestrator import MCPOrchestrator
            self.orchestrator = MCPOrchestrator()
            await self.orchestrator.initialize()
            logger.info(f"[WS_INIT] Orchestrator initialized with adapters: {list(self.orchestrator.adapters.keys())}")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections."""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"[WS_CLIENT] Client connected from {client_info}")
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Connected to MCP Orchestrator WebSocket Bridge",
                "available_tools": [
                    "orchestrate_task", "analyze_task", "query_specific_model",
                    "code_review", "multi_model_review", "get_orchestrator_status"
                ],
                "models": list(self.orchestrator.adapters.keys()) if self.orchestrator else []
            }))
            
            # Handle client messages
            async for message in websocket:
                try:
                    request = json.loads(message)
                    logger.info(f"[WS_REQUEST] {client_info} - {request.get('method', 'unknown')}")
                    
                    # Process request
                    response = await self.process_request(request)
                    
                    # Send response
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "error": "Invalid JSON",
                        "message": "Request must be valid JSON"
                    }))
                except Exception as e:
                    logger.error(f"[WS_ERROR] Processing error: {e}")
                    await websocket.send(json.dumps({
                        "error": "Processing error",
                        "message": str(e)
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[WS_CLIENT] Client {client_info} disconnected")
        except Exception as e:
            logger.error(f"[WS_ERROR] Client handler error: {e}")
        finally:
            self.clients.remove(websocket)
    
    async def process_request(self, request: dict) -> dict:
        """Process a request and return response."""
        method = request.get("method")
        params = request.get("params", {})
        
        if not method:
            return {"error": "Missing method"}
        
        try:
            # Handle different methods
            if method == "get_orchestrator_status":
                return await self.handle_status()
            elif method == "query_specific_model":
                return await self.handle_query_model(params)
            elif method == "orchestrate_task":
                return await self.handle_orchestrate(params)
            elif method == "analyze_task":
                return await self.handle_analyze(params)
            else:
                return {"error": f"Unknown method: {method}"}
                
        except Exception as e:
            logger.error(f"[WS_ERROR] Method {method} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": method
            }
    
    async def handle_status(self) -> dict:
        """Handle status request."""
        runtime = time.time() - self.start_time
        return {
            "success": True,
            "result": json.dumps({
                "status": "active",
                "runtime_seconds": runtime,
                "models_available": list(self.orchestrator.adapters.keys()),
                "active_connections": len(self.clients),
                "request_count": self.orchestrator.request_count,
                "total_cost": self.orchestrator.total_cost
            }),
            "method": "get_orchestrator_status"
        }
    
    async def handle_query_model(self, params: dict) -> dict:
        """Handle model query request."""
        from core.task import Task
        
        model = params.get("model")
        description = params.get("description")
        
        if not model or not description:
            return {"error": "Missing model or description"}
        
        # Map model names
        model_map = {
            "gemini_pro": "gemini_pro",
            "gemini": "gemini_pro",
            "o3": "o3_architect",
            "o3_architect": "o3_architect"
        }
        
        adapter_key = model_map.get(model, model)
        
        if adapter_key not in self.orchestrator.adapters:
            return {"error": f"Model {model} not available"}
        
        task = Task(description=description)
        response = await self.orchestrator.adapters[adapter_key].query(task)
        
        return {
            "success": True,
            "result": json.dumps(response.to_dict()),
            "method": "query_specific_model"
        }
    
    async def handle_orchestrate(self, params: dict) -> dict:
        """Handle orchestrate task request."""
        from core.task import Task
        
        description = params.get("description")
        strategy = params.get("strategy", "external_enhancement")
        
        if not description:
            return {"error": "Missing description"}
        
        task = Task(description=description)
        response = await self.orchestrator.orchestrate(task, strategy_override=strategy)
        
        return {
            "success": True,
            "result": json.dumps(response.to_dict()),
            "method": "orchestrate_task"
        }
    
    async def handle_analyze(self, params: dict) -> dict:
        """Handle analyze task request."""
        from core.task import Task
        
        description = params.get("description")
        
        if not description:
            return {"error": "Missing description"}
        
        task = Task(description=description)
        analysis = self.orchestrator.task_analyzer.analyze(task)
        
        return {
            "success": True,
            "result": json.dumps({
                "task_type": analysis.task_type.value,
                "complexity": analysis.complexity.value,
                "estimated_tokens": analysis.estimated_tokens,
                "recommended_strategy": analysis.recommended_strategy
            }),
            "method": "analyze_task"
        }
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8765):
        """Start WebSocket server."""
        # Initialize orchestrator first
        await self.initialize()
        
        # Start WebSocket server
        logger.info(f"[WS_LIFECYCLE] Starting WebSocket server on {host}:{port}")
        async with websockets.serve(self.handle_client, host, port):
            logger.info("[WS_LIFECYCLE] WebSocket bridge ready for connections")
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)
    
    # O3 is optional
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - O3 will not be available")
    
    # Start bridge
    bridge = MCPWebSocketBridge()
    await bridge.start_server()


if __name__ == "__main__":
    asyncio.run(main())