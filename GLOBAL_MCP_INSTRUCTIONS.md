# Global MCP Orchestrator Instructions

## 🎯 How to Make MCP Tools Work Globally

### Option 1: Update Claude Desktop Config (Recommended)

Add a global instruction to your Claude Desktop settings that reminds Claude to check for MCP tools.

**Location**: Claude Desktop Settings → Custom Instructions

**Add this text**:
```
Always check if MCP orchestrator tools are available for:
- Writing tests → use test_generator
- Debugging → use debug_helper  
- Code analysis → use code_analyzer
- Performance → use performance_profiler
- Refactoring → use refactor_assistant
- Documentation → use context_enhancer
- Migration → use code_migrator
- Reviews → use code_reviewer
- Architecture → use architecture_visualizer
- Complex tasks → use orchestrate_task

These tools provide multi-model intelligence (Claude + Gemini + O3).
```

### Option 2: Use Smart Assist Tool

The new `smart_assist` tool automatically detects what you need:

```python
# Instead of manually choosing tools, just use:
smart_assist(request="Write tests for this function", code_context=code)
smart_assist(request="Debug this error", code_context=error_info)
smart_assist(request="Optimize this slow code", code_context=code)
```

### Option 3: Shell Alias for Quick Access

Add to your ~/.bashrc or ~/.zshrc:

```bash
# Quick MCP tool access
alias mcp-test='echo "Use MCP test_generator tool"'
alias mcp-debug='echo "Use MCP debug_helper tool"'
alias mcp-analyze='echo "Use MCP code_analyzer tool"'
alias mcp-help='echo "Available MCP tools: test_generator, debug_helper, code_analyzer, performance_profiler, refactor_assistant, context_enhancer, code_migrator, architecture_visualizer, code_reviewer"'
```

### Option 4: Project Template

Create a template for new projects:

```bash
# Create project template
mkdir -p ~/.project-template
ln -s ~/.config/claude/CLAUDE_GLOBAL.md ~/.project-template/CLAUDE.md

# Function to create new project with MCP support
new-project() {
    mkdir -p "$1"
    cp -r ~/.project-template/* "$1/"
    cd "$1"
    echo "✅ Project created with MCP support!"
}
```

## 🚀 Best Practices

1. **Use smart_assist** - It auto-detects what tool you need
2. **Set global instructions** in Claude Desktop settings
3. **Create project templates** with CLAUDE.md pre-linked
4. **Use the watcher script** to auto-link new projects

## 📝 Quick Reference Card

Save this somewhere visible:

```
🛠️ MCP TOOLS CHEAT SHEET
========================
Write tests      → test_generator
Debug errors     → debug_helper
Analyze code     → code_analyzer
Optimize perf    → performance_profiler
Refactor code    → refactor_assistant
Add docs         → context_enhancer
Migrate code     → code_migrator
Review PR        → code_reviewer
Draw diagrams    → architecture_visualizer
Complex tasks    → orchestrate_task
Auto-detect      → smart_assist
```