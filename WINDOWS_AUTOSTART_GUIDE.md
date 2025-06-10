# 🖥️ Windows Auto-Start Guide for MCP Orchestrator

## ✅ Current Configuration

Your Docker container is configured with:
```yaml
restart: unless-stopped
```

This means it **WILL automatically restart** when:
1. Docker Desktop starts
2. After system reboot (if Docker Desktop auto-starts)
3. After any crash

## 🎯 To Enable Full Windows Auto-Start:

### Step 1: Enable Docker Desktop Auto-Start
1. **Right-click Docker Desktop icon** in system tray
2. **Settings** → **General**
3. **✅ Check**: "Start Docker Desktop when you log in"
4. **Apply & Restart**

### Step 2: Verify Container Policy
The container already has the correct restart policy (`unless-stopped`).

## 🔍 Alternative Methods

### Method A: Windows Startup Folder (Simple)
1. Press `Win + R`
2. Type: `shell:startup`
3. Copy `start_mcp_orchestrator.bat` to this folder

### Method B: Task Scheduler (More Control)
1. Open Task Scheduler
2. Create Task → "MCP Orchestrator Startup"
3. Triggers: At log on
4. Actions: Start `start_mcp_orchestrator.bat`
5. Conditions: Uncheck "Start only on AC power"

### Method C: Windows Service (Most Reliable)
```powershell
# Run as Administrator
sc create "MCPOrchestrator" binPath= "docker-compose -f C:\Users\%USERNAME%\GitHome\mcp_orchestrator\docker-compose.auto.yml up" start= auto
```

## ✅ Verification Steps

1. **Check Docker auto-start setting**:
   - Docker Desktop → Settings → General → "Start when you log in" ✅

2. **Test restart behavior**:
   ```bash
   # Stop container
   docker-compose -f docker-compose.auto.yml stop
   
   # Restart Docker Desktop
   # Container should auto-start!
   ```

3. **After Windows reboot**:
   ```bash
   docker ps | grep mcp-orchestrator
   ```

## 📊 Auto-Start Status Check

Run this command to verify:
```bash
docker inspect mcp-orchestrator-auto | grep -i restart
```

Should show:
```json
"RestartPolicy": {
    "Name": "unless-stopped",
    "MaximumRetryCount": 0
}
```

## 🎉 Summary

✅ **Docker container**: Configured for auto-restart
✅ **Restart policy**: `unless-stopped` (perfect for production)
❓ **Docker Desktop**: Must be set to auto-start in Windows

**Action Required**: Just enable Docker Desktop auto-start in settings!