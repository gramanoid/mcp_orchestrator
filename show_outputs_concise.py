#!/usr/bin/env python3
"""Show concise outputs from external models."""

import asyncio
import json
import sys
import os

sys.path.insert(0, 'src')
from mcp_server import call_tool, initialize_orchestrator


async def show_outputs():
    """Display concise outputs from external models."""
    print("🔍 External Model Outputs - Examples")
    print("=" * 60)
    
    await initialize_orchestrator()
    
    # Example 1: Simple Gemini query
    print("\n1️⃣ GEMINI 2.5 PRO OUTPUT:")
    print("-" * 40)
    result = await call_tool("query_specific_model", {
        "model": "gemini_pro",
        "description": "In 3 sentences, what makes Python good for beginners?"
    })
    response = json.loads(result[0].text)
    print(response['content'])
    print(f"\n📊 Tokens: {response['total_tokens']} | Cost: ${response['cost']:.4f}")
    
    # Example 2: Simple O3 query
    print("\n\n2️⃣ O3 ARCHITECT OUTPUT:")
    print("-" * 40)
    result = await call_tool("query_specific_model", {
        "model": "o3_architect",
        "description": "In 3 sentences, what's the key to good microservice design?"
    })
    response = json.loads(result[0].text)
    print(response['content'])
    print(f"\n📊 Model: {response['model']}")
    
    # Example 3: Multi-model quick review
    print("\n\n3️⃣ MULTI-MODEL REVIEW:")
    print("-" * 40)
    result = await call_tool("multi_model_review", {
        "task": "Is TypeScript worth learning for Python developers?",
        "focus_areas": ["learning curve", "career benefits"]
    })
    # Just show first 800 chars
    print(result[0].text[:800] + "...")
    
    # Example 4: Code analysis
    print("\n\n4️⃣ GEMINI CODE ANALYSIS:")
    print("-" * 40)
    result = await call_tool("orchestrate_task", {
        "description": "Analyze this code: def add(a, b): return a + b",
        "strategy": "external_enhancement"
    })
    # Show first 600 chars
    print(result[0].text[:600] + "...")
    
    print("\n" + "=" * 60)
    print("✅ External models are providing real, substantive responses!")


if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Set environment: export $(grep -v '^#' .env | xargs)")
        sys.exit(1)
    
    asyncio.run(show_outputs())