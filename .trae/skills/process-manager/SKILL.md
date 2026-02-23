---
name: "process-manager"
description: "管理项目相关进程，启动前检查并终止已存在的后端/前端进程。Invoke when user wants to start the project or mentions starting services, to ensure no duplicate processes are running."
---

# Process Manager

This skill manages project-related processes to prevent port conflicts and resource waste.

## When to Invoke

- User wants to start the project (backend/frontend)
- User mentions starting services
- Before running `npm run dev` or `uvicorn`
- When encountering "port already in use" errors

## Steps

### 1. Check for Existing Python/Backend Processes

Look for processes running:
- `uvicorn` (backend server)
- `python.exe` with `app.main` or backend paths

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*uvicorn*" } | Select-Object ProcessName, Id, Path
```

### 2. Check for Existing Node/Frontend Processes

Look for processes running:
- `node.exe` (frontend dev server)
- `vite` processes

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*node*" -or $_.ProcessName -like "*vite*" } | Select-Object ProcessName, Id, Path
```

### 3. Terminate Conflicting Processes

If found, ask user for confirmation or terminate automatically:

```powershell
# Terminate Python/Uvicorn processes
Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*uvicorn*" } | Stop-Process -Force

# Terminate Node/Vite processes  
Get-Process | Where-Object { $_.ProcessName -like "*node*" -or $_.ProcessName -like "*vite*" } | Stop-Process -Force
```

### 4. Verify Ports are Free

Check if ports 8000 (backend) and 5173 (frontend) are available:

```powershell
# Check port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

# Check port 5173
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
```

### 5. Then Start Services

After cleanup, start the services:
- Backend: `venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Frontend: `npm run dev`

## Important Notes

- Always check before starting to avoid "port already in use" errors
- Be careful not to terminate unrelated Python/Node processes
- Prefer targeted termination by process ID if possible
- Inform user of what processes were terminated
