#!/usr/bin/env python3
"""Demo showing real results from MCP tools."""

import asyncio
import json
import sys
import os

sys.path.insert(0, 'src')
from mcp_server import call_tool, initialize_orchestrator


async def demo_results():
    """Show real examples of tool outputs."""
    print("🎯 MCP Tools Demo - Real Results")
    print("=" * 60)
    
    await initialize_orchestrator()
    
    # Demo 1: Get Gemini's perspective on a technical question
    print("\n🤖 Demo 1: Gemini's Perspective on API Design")
    print("-" * 40)
    result = await call_tool("query_specific_model", {
        "model": "gemini_pro",
        "description": "What's your take on using GraphQL vs REST for a new project in 2024?"
    })
    response = json.loads(result[0].text)
    print(f"Gemini says: {response['content'][:500]}...")
    print(f"Cost: ${response['cost']:.4f}")
    
    # Demo 2: Get O3's architectural insights
    print("\n\n🏗️ Demo 2: O3's Architecture Insights")
    print("-" * 40)
    result = await call_tool("query_specific_model", {
        "model": "o3_architect",
        "description": "What's the most important consideration when designing a microservices architecture?"
    })
    response = json.loads(result[0].text)
    print(f"O3 says: {response['content'][:500]}...")
    
    # Demo 3: Multi-model review
    print("\n\n🔄 Demo 3: Multi-Model Review on Database Choice")
    print("-" * 40)
    result = await call_tool("multi_model_review", {
        "task": "Should we use PostgreSQL or MongoDB for an e-commerce platform?",
        "focus_areas": ["ACID compliance", "scalability", "developer experience"]
    })
    print("Combined External Perspectives:")
    print(result[0].text[:600])
    
    # Demo 4: Code review from external models
    print("\n\n📝 Demo 4: External Code Review")
    print("-" * 40)
    code = '''def process_payment(amount, card_number):
    # Process payment
    if amount > 0:
        charge_card(card_number, amount)
        return {"status": "success"}
    return {"status": "failed"}'''
    
    with open("payment.py", "w") as f:
        f.write(code)
    
    result = await call_tool("code_review", {
        "file_paths": ["payment.py"],
        "description": "Review this payment processing code"
    })
    print("External Review:")
    print(result[0].text[:500])
    
    os.remove("payment.py")
    
    # Show status
    print("\n\n📊 System Status")
    print("-" * 40)
    result = await call_tool("get_orchestrator_status", {})
    status = json.loads(result[0].text)
    print(f"Total Requests: {status['request_count']}")
    print(f"Total Cost: ${status['total_cost']:.4f}")
    print(f"Available Models: {', '.join(status['models_available'])}")


if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Set environment: export $(grep -v '^#' .env | xargs)")
        sys.exit(1)
    
    asyncio.run(demo_results())