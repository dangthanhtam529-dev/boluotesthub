---
name: "pre-startup-check"
description: "启动项目前检查虚拟环境、自动激活venv、清理资源、检查内存泄漏和溢出风险。Invoke when user wants to start the project or mentions starting services, to ensure environment is healthy and optimized."
---

# Pre-Startup Check

This skill performs comprehensive checks before starting the project, automatically activates virtual environment, and cleans up unnecessary resources.

## When to Invoke

- User wants to start the project (backend/frontend)
- User mentions starting services
- Before running `npm run dev` or `uvicorn`
- When encountering environment-related issues
- When system resources are low

## Steps

### 1. Check and Auto-Activate Virtual Environment

**Check current Python:**
```powershell
$systemPython = (Get-Command python).Source
$venvPythonPath = ".\venv\Scripts\python.exe"

if ($systemPython -like "*venv*") {
    Write-Host "✅ 虚拟环境已激活: $systemPython" -ForegroundColor Green
    $global:pythonCmd = "python"
} else {
    Write-Host "⚠️  虚拟环境未激活，当前使用: $systemPython" -ForegroundColor Yellow
    
    # Check if venv exists
    if (Test-Path $venvPythonPath) {
        Write-Host "🔧 正在激活虚拟环境..." -ForegroundColor Cyan
        $global:pythonCmd = $venvPythonPath
        Write-Host "✅ 虚拟环境已设置: $venvPythonPath" -ForegroundColor Green
    } else {
        Write-Host "❌ 虚拟环境不存在，请先创建: python -m venv venv" -ForegroundColor Red
    }
}
```

**Usage in subsequent commands:**
- Instead of `python`, use `$pythonCmd` or `.
v\Scripts\python.exe`
- Instead of `pip`, use `.
env\Scripts\pip.exe`

### 2. Clean Up Unnecessary Resources

**Clean Python cache files:**
```powershell
Write-Host "`n🧹 清理 Python 缓存文件..." -ForegroundColor Cyan
$cacheCount = 0
Get-ChildItem -Path "." -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force
    $cacheCount++
}
Get-ChildItem -Path "." -Recurse -File -Filter "*.pyc" | ForEach-Object {
    Remove-Item -Path $_.FullName -Force
    $cacheCount++
}
Write-Host "✅ 已清理 $cacheCount 个缓存文件/目录" -ForegroundColor Green
```

**Clean temporary files:**
```powershell
Write-Host "`n🧹 清理临时文件..." -ForegroundColor Cyan
$tempCount = 0
# Clean .log files older than 7 days
Get-ChildItem -Path "." -Recurse -File -Filter "*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | ForEach-Object {
    Remove-Item -Path $_.FullName -Force
    $tempCount++
}
Write-Host "✅ 已清理 $tempCount 个临时日志文件" -ForegroundColor Green
```

**Clean npm cache (if frontend exists):**
```powershell
if (Test-Path ".\frontend\node_modules") {
    Write-Host "`n🧹 清理 npm 缓存..." -ForegroundColor Cyan
    npm cache clean --force 2>$null
    Write-Host "✅ npm 缓存已清理" -ForegroundColor Green
}
```

### 3. Check Memory Usage

Check system memory status:
```powershell
$memory = Get-CimInstance -ClassName Win32_OperatingSystem
$totalMemory = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 2)
$freeMemory = [math]::Round($memory.FreePhysicalMemory / 1MB, 2)
$usedMemory = $totalMemory - $freeMemory
$memoryUsagePercent = [math]::Round(($usedMemory / $totalMemory) * 100, 2)

Write-Host "`n内存状态:" -ForegroundColor Cyan
Write-Host "  总计: $totalMemory GB"
Write-Host "  已用: $usedMemory GB ($memoryUsagePercent%)"
Write-Host "  可用: $freeMemory GB"

if ($memoryUsagePercent -gt 90) {
    Write-Host "⚠️  警告：内存使用率超过 90%，建议清理后再启动" -ForegroundColor Red
    # Auto-clean suggestion
    Write-Host "💡 建议：关闭不必要的应用程序或重启电脑" -ForegroundColor Yellow
} elseif ($memoryUsagePercent -gt 80) {
    Write-Host "⚠️  注意：内存使用率超过 80%" -ForegroundColor Yellow
} else {
    Write-Host "✅ 内存状态良好" -ForegroundColor Green
}
```

### 4. Check for Memory Leaks and Resource Hogs

**Check existing processes:**
```powershell
$pythonProcesses = Get-Process | Where-Object { $_.ProcessName -like "*python*" }
$nodeProcesses = Get-Process | Where-Object { $_.ProcessName -like "*node*" }

$totalPythonMemory = 0
$totalNodeMemory = 0
$highMemoryProcesses = @()

Write-Host "`n现有进程内存使用:" -ForegroundColor Cyan

foreach ($proc in $pythonProcesses) {
    $memoryMB = [math]::Round($proc.WorkingSet64 / 1MB, 2)
    $totalPythonMemory += $memoryMB
    if ($memoryMB -gt 500) {
        Write-Host "  ⚠️  Python PID $($proc.Id): $memoryMB MB (内存占用较高)" -ForegroundColor Yellow
        $highMemoryProcesses += $proc
    } else {
        Write-Host "  Python PID $($proc.Id): $memoryMB MB" -ForegroundColor Gray
    }
}

foreach ($proc in $nodeProcesses) {
    $memoryMB = [math]::Round($proc.WorkingSet64 / 1MB, 2)
    $totalNodeMemory += $memoryMB
    if ($memoryMB -gt 500) {
        Write-Host "  ⚠️  Node PID $($proc.Id): $memoryMB MB (内存占用较高)" -ForegroundColor Yellow
        $highMemoryProcesses += $proc
    } else {
        Write-Host "  Node PID $($proc.Id): $memoryMB MB" -ForegroundColor Gray
    }
}

Write-Host "`nPython 进程总内存: $totalPythonMemory MB"
Write-Host "Node 进程总内存: $totalNodeMemory MB"

# Auto-terminate high memory processes if total > 2GB
if ($totalPythonMemory -gt 2000 -or $totalNodeMemory -gt 2000) {
    Write-Host "⚠️  警告：检测到内存占用过高，可能存在内存泄漏" -ForegroundColor Red
    Write-Host "🔧 正在终止高内存进程..." -ForegroundColor Cyan
    foreach ($proc in $highMemoryProcesses) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "  已终止 PID $($proc.Id)" -ForegroundColor Green
    }
}
```

### 5. Check Disk Space

```powershell
$disk = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB, 2)
$totalSpaceGB = [math]::Round($disk.Size / 1GB, 2)
$freePercent = [math]::Round(($freeSpaceGB / $totalSpaceGB) * 100, 2)

Write-Host "`n磁盘状态 (C:):" -ForegroundColor Cyan
Write-Host "  总计: $totalSpaceGB GB"
Write-Host "  可用: $freeSpaceGB GB ($freePercent%)"

if ($freeSpaceGB -lt 5) {
    Write-Host "⚠️  警告：磁盘空间不足 5GB，可能影响项目运行" -ForegroundColor Red
    Write-Host "💡 建议：清理临时文件、卸载不必要的程序" -ForegroundColor Yellow
} elseif ($freeSpaceGB -lt 10) {
    Write-Host "⚠️  注意：磁盘空间不足 10GB" -ForegroundColor Yellow
} else {
    Write-Host "✅ 磁盘空间充足" -ForegroundColor Green
}
```

### 6. Check and Free Ports

```powershell
$ports = @(8000, 5173)
$occupiedPorts = @()

Write-Host "`n端口检查:" -ForegroundColor Cyan

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "⚠️  端口 $port 被占用 (PID: $($connection.OwningProcess), 进程: $($process.ProcessName))" -ForegroundColor Yellow
        $occupiedPorts += @{ Port = $port; PID = $connection.OwningProcess; ProcessName = $process.ProcessName }
    } else {
        Write-Host "✅ 端口 $port 可用" -ForegroundColor Green
    }
}

# Auto-terminate processes occupying ports
if ($occupiedPorts.Count -gt 0) {
    Write-Host "`n🔧 正在释放被占用的端口..." -ForegroundColor Cyan
    foreach ($info in $occupiedPorts) {
        Stop-Process -Id $info.PID -Force -ErrorAction SilentlyContinue
        Write-Host "  已终止 $($info.ProcessName) (PID: $($info.PID))，释放端口 $($info.Port)" -ForegroundColor Green
    }
}
```

### 7. Summary and Start Services

After all checks and cleanup:

```powershell
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  启动前检查完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# Start backend with venv Python
Write-Host "`n🚀 启动后端服务..." -ForegroundColor Cyan
# Use: $pythonCmd -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend
Write-Host "`n🚀 启动前端服务..." -ForegroundColor Cyan
# Use: npm run dev
```

## Auto-Cleanup Script (Complete)

```powershell
# 完整自动清理和启动脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  项目启动前检查与优化" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# 1. 设置虚拟环境
$venvPython = ".\venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $global:pythonCmd = $venvPython
    Write-Host "✅ 虚拟环境: $venvPython" -ForegroundColor Green
} else {
    Write-Host "❌ 虚拟环境不存在" -ForegroundColor Red
    exit 1
}

# 2. 清理缓存
Write-Host "`n🧹 清理缓存文件..." -ForegroundColor Cyan
Get-ChildItem -Path "." -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path "." -Recurse -File -Filter "*.pyc" | Remove-Item -Force
Write-Host "✅ 缓存清理完成" -ForegroundColor Green

# 3. 终止占用端口的进程
Write-Host "`n🔧 释放端口..." -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Write-Host "✅ 端口已释放" -ForegroundColor Green

# 4. 检查内存
$memory = Get-CimInstance -ClassName Win32_OperatingSystem
$freeMemory = [math]::Round($memory.FreePhysicalMemory / 1MB, 2)
Write-Host "`n💾 可用内存: $freeMemory GB" -ForegroundColor Cyan

# 5. 检查磁盘
$disk = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB, 2)
Write-Host "💿 磁盘空间: $freeSpaceGB GB`n" -ForegroundColor Cyan

Write-Host "✅ 检查完成，准备启动服务..." -ForegroundColor Green
```

## Important Notes

- **Always use virtual environment**: Prevents dependency conflicts
- **Auto-cleanup**: Removes cache files to free disk space and avoid stale code
- **Resource monitoring**: Terminates high-memory processes to prevent system slowdown
- **Port management**: Automatically frees required ports
- **Memory alerts**: Warns when system resources are low
- **Disk space**: Alerts when C: drive is running low

## Best Practices

1. Run this check before every project start
2. If memory consistently > 80%, consider adding more RAM or closing other apps
3. If disk space < 5GB, clean up temporary files and unused programs
4. Monitor for memory leaks in long-running processes
5. Regularly clean `__pycache__` and `node_modules/.cache`
