---
name: "post-task-check"
description: "任务执行后检查系统状态，包括内存、服务、端口、数据库。Invoke after completing any task that involves backend/frontend services, database operations, or project restart."
---

# Post-Task System Check

## 触发条件
每次完成任务后，如果任务涉及以下操作，必须执行此检查：
- 启动/重启前后端服务
- 数据库操作（创建表、插入数据等）
- 修改配置文件
- 端口相关操作

## 检查清单

### 1. 内存使用情况
```powershell
# 查看系统内存
Get-WmiObject -Class Win32_OperatingSystem | Select-Object @{Name="TotalMemoryGB";Expression={[math]::Round($_.TotalVisibleMemorySize/1MB,2)}}, @{Name="FreeMemoryGB";Expression={[math]::Round($_.FreePhysicalMemory/1MB,2)}}

# 查看Python/Node进程内存
Get-Process | Where-Object { $_.ProcessName -match "python|node|uvicorn" } | Select-Object ProcessName, Id, @{Name="MemoryMB";Expression={[math]::Round($_.WorkingSet/1MB,2)}}
```

### 2. 服务状态检查
```powershell
# 检查后端服务 (端口 8000/8080)
$backendPort = 8000  # 或 8080
$backendRunning = Test-NetConnection -ComputerName localhost -Port $backendPort -WarningAction SilentlyContinue
Write-Host "Backend (port $backendPort): $($backendRunning.TcpTestSucceeded)"

# 检查前端服务 (端口 5173/5174)
$frontendPort = 5173  # 或 5174
$frontendRunning = Test-NetConnection -ComputerName localhost -Port $frontendPort -WarningAction SilentlyContinue
Write-Host "Frontend (port $frontendPort): $($frontendRunning.TcpTestSucceeded)"
```

### 3. 端口占用检查
```powershell
# 检查常用端口占用情况
$ports = @(8000, 8080, 5173, 5174, 3000, 3306, 27017)
foreach ($port in $ports) {
    $connection = netstat -ano | findstr ":$port " | findstr "LISTENING"
    if ($connection) {
        Write-Host "Port $port is occupied"
    } else {
        Write-Host "Port $port is free"
    }
}
```

### 4. 数据库检查

#### MySQL 检查
```powershell
# 检查数据库连接和表
# 需要在backend目录下执行
.\venv\Scripts\python.exe -c "
from sqlmodel import Session, select
from app.core.db import engine
from app.models.execution import TestExecution
from app.models.user import User

with Session(engine) as session:
    # 检查表是否存在
    try:
        exec_count = session.exec(select(TestExecution)).all()
        print(f'TestExecution table exists, records: {len(exec_count)}')
    except Exception as e:
        print(f'TestExecution table error: {e}')
    
    try:
        user_count = session.exec(select(User)).all()
        print(f'User table exists, records: {len(user_count)}')
    except Exception as e:
        print(f'User table error: {e}')
"
```

#### MongoDB 检查
```powershell
# 检查MongoDB连接
.\venv\Scripts\python.exe -c "
from app.core.mongodb import get_mongodb
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def check_mongodb():
    try:
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        await client.admin.command('ping')
        db = client.test_platform
        collections = await db.list_collection_names()
        print(f'MongoDB connected. Collections: {collections}')
    except Exception as e:
        print(f'MongoDB error: {e}')

asyncio.run(check_mongodb())
"
```

## 执行流程

1. **重启项目前**：
   - 检查端口占用情况
   - 结束占用端口的进程
   - 验证进程已终止

2. **任务完成后**：
   - 检查内存使用情况
   - 验证前后端服务正常运行
   - 检查数据库表是否存在
   - 验证数据是否正确写入

3. **发现问题时**：
   - 记录错误信息
   - 尝试自动修复（如重启服务、清理端口）
   - 如无法修复，向用户报告

## 报告模板

```
=== 系统状态检查报告 ===

[内存状态]
- 总内存: XX GB
- 可用内存: XX GB
- Python/Node进程内存使用: XX MB

[服务状态]
- 后端服务 (端口 XXXX): 运行中/已停止
- 前端服务 (端口 XXXX): 运行中/已停止

[端口占用]
- 端口 8000: 占用/空闲
- 端口 8080: 占用/空闲
- 端口 5173: 占用/空闲
- 端口 5174: 占用/空闲

[数据库状态]
- MySQL连接: 正常/异常
- TestExecution表: 存在，记录数 X
- User表: 存在，记录数 X
- MongoDB连接: 正常/异常
- MongoDB集合: [list]

[结论]
系统状态: 正常/需要关注
建议操作: XXX
```
