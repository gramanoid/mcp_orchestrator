# Global MCP Orchestrator Rules

## ALWAYS CHECK: Should I use an MCP tool?

### Automatic Tool Triggers:
1. **"Write tests"** → `test_generator`
2. **"Debug/Fix error"** → `debug_helper`
3. **"Analyze code"** → `code_analyzer`
4. **"Optimize/Performance"** → `performance_profiler`
5. **"Refactor/Improve"** → `refactor_assistant`
6. **"Document/Explain"** → `context_enhancer`
7. **"Migrate/Convert"** → `code_migrator`
8. **"Review code"** → `code_reviewer`
9. **"Visualize/Diagram"** → `architecture_visualizer`
10. **Complex tasks** → `orchestrate_task`

### Multi-Model Strategy:
- Simple tasks: Use default strategy
- Critical tasks: Use `strategy="max_quality_council"`

### Tool Chaining:
- Analyze → Refactor → Test → Review
- Debug → Fix → Test
- Profile → Optimize → Test

## Remember: These tools provide multi-model intelligence (Claude + Gemini + O3)!
