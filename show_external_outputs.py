#!/usr/bin/env python3
"""Show detailed outputs from external models."""

import asyncio
import json
import sys
import os

sys.path.insert(0, 'src')
from mcp_server import call_tool, initialize_orchestrator


async def show_external_outputs():
    """Display full outputs from external models."""
    print("🔍 External Model Outputs - Real Examples")
    print("=" * 60)
    
    await initialize_orchestrator()
    
    # Example 1: Gemini on a coding question
    print("\n📘 Example 1: Gemini 2.5 Pro - Coding Best Practices")
    print("-" * 60)
    result = await call_tool("query_specific_model", {
        "model": "gemini_pro",
        "description": "What are the top 3 Python coding mistakes beginners make?"
    })
    response = json.loads(result[0].text)
    print(f"GEMINI'S FULL RESPONSE:\n{response['content']}\n")
    print(f"Tokens used: {response['total_tokens']}")
    print(f"Cost: ${response['cost']:.4f}")
    
    # Example 2: O3 on architecture
    print("\n\n🏛️ Example 2: O3 - System Architecture")
    print("-" * 60)
    result = await call_tool("query_specific_model", {
        "model": "o3_architect",
        "description": "How should I structure a Python web API project?"
    })
    response = json.loads(result[0].text)
    print(f"O3'S FULL RESPONSE:\n{response['content']}\n")
    print(f"Model: {response['model']}")
    
    # Example 3: Multi-model on a decision
    print("\n\n🤝 Example 3: Both Models - Technical Decision")
    print("-" * 60)
    result = await call_tool("multi_model_review", {
        "task": "Should I use async/await or threading for concurrent Python code?",
        "focus_areas": ["performance", "complexity", "use cases"]
    })
    print(f"COMBINED PERSPECTIVES:\n{result[0].text}\n")
    
    # Example 4: Gemini code review
    print("\n\n💻 Example 4: Gemini - Code Review")
    print("-" * 60)
    code = '''def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)'''
    
    with open("fib.py", "w") as f:
        f.write(code)
    
    result = await call_tool("orchestrate_task", {
        "description": f"Review this fibonacci implementation and suggest improvements:\n\n{code}",
        "strategy": "external_enhancement"
    })
    print(f"GEMINI'S CODE REVIEW:\n{result[0].text[:1500]}...\n")
    
    os.remove("fib.py")
    
    # Example 5: Quick comparison
    print("\n\n⚖️ Example 5: External Models Compare Options")
    print("-" * 60)
    result = await call_tool("orchestrate_task", {
        "description": "Compare FastAPI vs Flask for building REST APIs",
        "strategy": "max_quality_council"
    })
    print(f"EXTERNAL COMPARISON:\n{result[0].text[:1000]}...\n")


if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Set environment: export $(grep -v '^#' .env | xargs)")
        sys.exit(1)
    
    asyncio.run(show_external_outputs())