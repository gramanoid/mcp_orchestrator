#!/usr/bin/env python3
"""Example of integrating MCP Orchestrator into your application."""

import requests
import subprocess
import json
import asyncio
import websockets


class MCPOrchestrator:
    """Client for MCP Orchestrator integration."""
    
    def __init__(self, method="rest", base_url="http://localhost:5050", ws_url="ws://localhost:8765"):
        self.method = method
        self.base_url = base_url
        self.ws_url = ws_url
    
    def query_via_rest(self, tool, params):
        """Query MCP via REST API."""
        response = requests.post(
            f"{self.base_url}/mcp/{tool}",
            json=params
        )
        result = response.json()
        if result.get('success'):
            return json.loads(result['result'])
        else:
            raise Exception(result.get('error'))
    
    async def query_via_websocket(self, tool, params):
        """Query MCP via WebSocket."""
        async with websockets.connect(self.ws_url) as ws:
            await ws.send(json.dumps({
                "method": tool,
                "params": params
            }))
            response = json.loads(await ws.recv())
            if response.get('success'):
                return json.loads(response['result'])
            else:
                raise Exception(response.get('error'))
    
    def query_via_docker(self, tool, params):
        """Query MCP via direct Docker execution."""
        request = {
            "method": tool,
            "params": params
        }
        
        process = subprocess.run(
            ['docker', 'run', '--rm', '-i', '--env-file', '.env',
             'mcp-orchestrator:latest', 'python', '-m', 'src.mcp_server'],
            input=json.dumps(request),
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            return json.loads(process.stdout)
        else:
            raise Exception(process.stderr)
    
    def query(self, tool, params):
        """Query MCP using configured method."""
        if self.method == "rest":
            return self.query_via_rest(tool, params)
        elif self.method == "websocket":
            return asyncio.run(self.query_via_websocket(tool, params))
        elif self.method == "docker":
            return self.query_via_docker(tool, params)
        else:
            raise ValueError(f"Unknown method: {self.method}")


# Example usage in your application
def main():
    """Example integration."""
    
    # Initialize client (choose your preferred method)
    mcp = MCPOrchestrator(method="rest")  # or "websocket" or "docker"
    
    print("🤖 MCP Orchestrator Integration Example")
    print("=" * 60)
    
    # Example 1: Get external perspectives on a technical decision
    print("\n1. Technical Decision Support")
    try:
        result = mcp.query("multi_model_review", {
            "task": "Should we migrate from monolith to microservices?",
            "focus_areas": ["team size", "complexity", "maintenance"]
        })
        print(f"External perspectives: {result[:300]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Code review with external models
    print("\n\n2. Code Review")
    code = '''
def authenticate_user(username, password):
    user = db.query(f"SELECT * FROM users WHERE username='{username}'")
    if user and user.password == password:
        return {"authenticated": True, "user": user}
    return {"authenticated": False}
'''
    
    # Save code temporarily
    with open("auth_example.py", "w") as f:
        f.write(code)
    
    try:
        result = mcp.query("code_review", {
            "file_paths": ["auth_example.py"],
            "description": "Review this authentication code for security issues"
        })
        print(f"Security review: {result[:400]}...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        import os
        os.remove("auth_example.py")
    
    # Example 3: Architecture analysis
    print("\n\n3. Architecture Analysis")
    try:
        result = mcp.query("query_specific_model", {
            "model": "o3_architect",
            "description": "What's the best way to implement event sourcing?"
        })
        print(f"O3 Architect says: {result['content'][:300]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: Get Gemini's perspective
    print("\n\n4. Gemini's Perspective")
    try:
        result = mcp.query("query_specific_model", {
            "model": "gemini_pro",
            "description": "What are the trade-offs of using Rust vs Go for backend services?"
        })
        print(f"Gemini says: {result['content'][:300]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n\n✅ Integration example complete!")


if __name__ == "__main__":
    main()