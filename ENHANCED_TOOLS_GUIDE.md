# 🚀 Enhanced MCP Orchestrator Tools Guide

## Overview
The Enhanced MCP Orchestrator now includes 11 powerful tools for comprehensive coding assistance. Each tool leverages multi-model orchestration to provide the best possible results.

## 🛠️ Available Tools

### 1. **analyze_task**
Analyzes coding tasks to determine optimal LLM strategy.
```bash
analyze_task(description="Refactor this authentication system")
```

### 2. **orchestrate_task**
Main tool for multi-model task processing.
```bash
orchestrate_task(
    description="Design a caching strategy",
    strategy="max_quality_council"  # For critical tasks
)
```

### 3. **test_generator** 🧪
Generates comprehensive test suites with edge cases.
```bash
test_generator(
    code_context="your_function_code",
    test_framework="pytest",
    coverage_target=95,
    include_edge_cases=true
)
```

### 4. **code_analyzer** 🔍
Deep analysis for complexity, security, and performance.
```bash
code_analyzer(
    code_context="your_code",
    analysis_types=["security", "performance"],
    include_suggestions=true
)
```

### 5. **debug_helper** 🐛
Expert debugging with root cause analysis.
```bash
debug_helper(
    error_message="TypeError: ...",
    stack_trace="full_trace",
    debugging_depth="exhaustive"
)
```

### 6. **refactor_assistant** 🔧
Intelligent refactoring with design patterns.
```bash
refactor_assistant(
    code_context="messy_code",
    refactor_goals=["extract_method", "apply_pattern"],
    target_pattern="factory"
)
```

### 7. **context_enhancer** 📚
Enhance code with documentation and examples.
```bash
context_enhancer(
    code_context="your_code",
    enhancement_types=["docstrings", "examples"],
    explain_level="beginner"
)
```

### 8. **code_migrator** 🔄
Migrate between versions or frameworks.
```bash
code_migrator(
    source_code="python2_code",
    migration_type="version",
    from_spec="python2",
    to_spec="python3"
)
```

### 9. **performance_profiler** ⚡
Profile performance and suggest optimizations.
```bash
performance_profiler(
    code_context="slow_function",
    profile_aspects=["time_complexity", "memory_usage"],
    suggest_optimizations=true
)
```

### 10. **architecture_visualizer** 🏗️
Generate architecture diagrams.
```bash
architecture_visualizer(
    code_context="module_code",
    diagram_types=["class_diagram", "dependency_graph"],
    output_format="mermaid"
)
```

### 11. **code_reviewer** 👀
Comprehensive code reviews.
```bash
code_reviewer(
    code_context="pr_diff",
    review_type="security",
    suggest_improvements=true
)
```

## 🎯 Usage Strategies

### For Quick Tasks
- Use `orchestrate_task` with default strategy
- Single model (Claude) responds quickly

### For Critical Tasks
- Use `strategy="max_quality_council"`
- All models (Claude, Gemini, O3) collaborate
- Higher cost but maximum quality

### For Debugging
- `debug_helper` always uses max quality
- Provides exhaustive analysis
- Multiple solution strategies

### For Performance
- `performance_profiler` + `code_analyzer`
- Identifies bottlenecks
- Provides optimized alternatives

## 💡 Pro Tips

1. **Combine Tools**: Use `code_analyzer` before `refactor_assistant`
2. **Test Everything**: Always run `test_generator` after refactoring
3. **Document Well**: Use `context_enhancer` for team collaboration
4. **Review Security**: Run `code_reviewer` with `review_type="security"`
5. **Visualize First**: Use `architecture_visualizer` before major changes

## 🚀 Example Workflow

```python
# 1. Analyze existing code
code_analyzer(code_context=my_code, analysis_types=["all"])

# 2. Visualize architecture
architecture_visualizer(code_context=my_code, output_format="mermaid")

# 3. Refactor based on analysis
refactor_assistant(code_context=my_code, refactor_goals=["optimize"])

# 4. Generate tests for refactored code
test_generator(code_context=refactored_code, coverage_target=95)

# 5. Review final result
code_reviewer(code_context=refactored_code, review_type="full")
```

## 🎉 Ready to Use!

After restarting Claude Code, all these tools will be available in your MCP tools menu. Each tool automatically determines whether to use single-model or multi-model orchestration based on task complexity.

Happy coding with your AI council! 🤖✨