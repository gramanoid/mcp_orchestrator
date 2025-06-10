#!/usr/bin/env python3
"""
MCP Client Script
Demonstrates how to connect to and use the MCP Orchestrator
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional

# MCP client would typically be installed separately
# This is a simplified example showing the interaction pattern
class MCPClient:
    """Simple MCP client for demonstration"""
    
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process = None
        self.reader = None
        self.writer = None
    
    async def connect(self):
        """Connect to MCP server via stdio"""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        
        # Send initialization
        await self.send_message({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {}
            },
            "id": 1
        })
        
        # Read initialization response
        response = await self.read_message()
        if response.get("error"):
            raise Exception(f"Initialization failed: {response['error']}")
        
        print("Connected to MCP Orchestrator")
        return response
    
    async def send_message(self, message: Dict[str, Any]):
        """Send JSON-RPC message to server"""
        json_str = json.dumps(message) + "\n"
        self.writer.write(json_str.encode())
        await self.writer.drain()
    
    async def read_message(self) -> Dict[str, Any]:
        """Read JSON-RPC message from server"""
        line = await self.reader.readline()
        if not line:
            raise Exception("Server closed connection")
        return json.loads(line.decode())
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        message = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 2
        }
        
        await self.send_message(message)
        response = await self.read_message()
        
        if response.get("error"):
            raise Exception(f"Tool call failed: {response['error']}")
        
        return response.get("result", {})
    
    async def close(self):
        """Close connection to server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()


async def demonstrate_orchestration():
    """Demonstrate MCP Orchestrator capabilities"""
    
    # Connect to MCP server
    # In production, this would typically be handled by the MCP host
    client = MCPClient(["python", "-m", "src.mcp_server"])
    
    try:
        # Initialize connection
        init_response = await client.connect()
        print(f"Server capabilities: {init_response.get('result', {}).get('capabilities', {})}")
        
        # Example 1: Simple reasoning task
        print("\n=== Example 1: Simple Reasoning ===")
        result = await client.call_tool("reason", {
            "task": "What are the key considerations when designing a distributed system?",
            "strategy": "progressive_deep_dive",
            "max_depth": 2
        })
        print(f"Result: {result}")
        
        # Example 2: Complex analysis with council
        print("\n=== Example 2: Complex Analysis ===")
        result = await client.call_tool("reason", {
            "task": "Analyze the trade-offs between microservices and monolithic architecture",
            "strategy": "max_quality_council",
            "models": ["claude-3-opus", "gemini-pro", "gpt-4"],
            "options": {
                "require_consensus": True,
                "min_confidence": 0.8
            }
        })
        print(f"Result: {result}")
        
        # Example 3: Code review task
        print("\n=== Example 3: Code Review ===")
        code_sample = '''
        def process_data(items):
            result = []
            for i in range(len(items)):
                if items[i] > 0:
                    result.append(items[i] * 2)
            return result
        '''
        
        result = await client.call_tool("reason", {
            "task": f"Review this Python code and suggest improvements:\n{code_sample}",
            "strategy": "progressive_deep_dive",
            "options": {
                "focus_areas": ["performance", "readability", "pythonic style"]
            }
        })
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


def main():
    """Main entry point"""
    print("MCP Orchestrator Client Demo")
    print("=" * 50)
    
    # Check if running in Docker
    if len(sys.argv) > 1 and sys.argv[1] == "--docker":
        print("Note: When using Docker, ensure the container is running:")
        print("  docker-compose up -d")
        print("  docker exec -it mcp-orchestrator python scripts/mcp-client.py")
        return
    
    # Run demonstration
    asyncio.run(demonstrate_orchestration())


if __name__ == "__main__":
    main()