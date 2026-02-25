# 定时任务问题完整修复总结

## 问题描述

1. **钉钉显示"没有权限"**：定时任务执行完后，钉钉收到消息显示"CLI 执行失败：error 您没有权限访问指定的资源"
2. **任务卡住**：部分定时任务一直显示"正在运行"状态
3. **删除任务失败**：无法删除卡住的定时任务

## 根本原因分析

### 问题 1：钉钉显示"没有权限"
**真实原因**：Apifox CLI 在定时任务环境下执行失败，返回错误信息，该错误被原封不动发给钉钉。

**CLI 失败原因**：
- Windows 定时任务默认工作目录是 `C:\Windows\System32`，而不是项目目录
- 定时任务环境下 `.env` 文件未被加载，导致 `APIFOX_ACCESS_TOKEN` 和 `APIFOX_PROJECT_ID` 为空
- 定时任务环境下 `PATH` 环境变量不完整，找不到 `npx/npm`
- 字符编码设置不正确，CLI 输出乱码，掩盖了真实错误

### 问题 2：任务卡住
- 任务执行超时或异常时，状态更新逻辑未及时执行
- 没有超时自动恢复机制，卡住的任务永久保持 `running` 状态

### 问题 3：删除任务失败
- 删除任务时没有处理卡住的执行记录
- 没有强制删除选项

## 已执行的修复

### 修复 1：`app/services/apifox.py` - CLI 环境变量增强

**位置**：`run_collection` 方法（约 528-554 行）

**修复内容**：
```python
# 构建完整的环境变量
exec_env = os.environ.copy()
exec_env['PYTHONIOENCODING'] = 'utf-8'
exec_env['PYTHONUTF8'] = '1'

# 确保 Node.js/npm 在 PATH 中
node_paths = [
    r'C:\Program Files\nodejs',
    r'C:\Program Files (x86)\nodejs',
    os.path.expanduser(r'~\AppData\Roaming\npm'),
]
current_path = exec_env.get('PATH', '')
exec_env['PATH'] = ';'.join(node_paths) + ';' + current_path

result = subprocess.run(
    cli_command, 
    shell=True,
    capture_output=True, 
    text=True, 
    timeout=timeout,
    env=exec_env,  # 传递完整的环境变量
    encoding='utf-8',
    errors='replace'
)
```

**效果**：
- ✅ 确保 CLI 执行时有完整的环境变量
- ✅ 确保 UTF-8 编码，防止乱码
- ✅ 确保能找到 `npx` 命令

---

### 修复 2：`app/services/scheduler_service.py` - 定时任务环境增强

**位置 1**：`run_scheduled_task` 函数（约 281-321 行）

**修复内容**：
```python
# 切换工作目录到项目根目录
backend_dir = os.path.join(...)
project_root = os.path.dirname(backend_dir)
os.chdir(project_root)

# 设置字符编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 确保 npx/npm 能找到
npm_global_path = os.path.join(os.environ.get('APPDATA', ''), 'npm')
node_path = r"C:\Program Files\nodejs"
current_path = os.environ.get('PATH', '')
new_paths = [p for p in [node_path, npm_global_path] if os.path.exists(p)]
os.environ['PATH'] = os.pathsep.join(new_paths + [current_path])

# 重新加载 .env 文件
from dotenv import load_dotenv
load_dotenv(env_file_path, override=True)
```

**位置 2**：`execute_scheduled_task_with_retry` 函数（新增超时恢复逻辑）

**修复内容**：
```python
# 检查是否有卡住的旧执行记录
if old_execution and old_execution.status == "running":
    elapsed = (datetime.now() - old_execution.started_at).total_seconds()
    if elapsed > timeout_seconds * 2:
        # 标记为失败
        old_execution.status = "failed"
        old_execution.error_message = "任务执行超时，自动终止"
```

**位置 3**：异常处理块（新增状态恢复）

**修复内容**：
```python
except asyncio.TimeoutError:
    # 超时后立即恢复执行记录状态
    if execution and execution.status == "running":
        execution.status = "failed"
        execution.error_message = last_error
        execution.completed_at = get_datetime_china()
        session.commit()
```

**效果**：
- ✅ 定时任务环境下正确加载 `.env` 文件
- ✅ 定时任务环境下正确设置工作目录
- ✅ 定时任务环境下能找到 `npx` 命令
- ✅ 卡住的任务会自动恢复状态

---

### 修复 3：`app/api/routes/scheduled_tasks.py` - 删除任务增强

**位置**：`delete_task_endpoint` 函数（约 150-195 行）

**修复内容**：
```python
@router.delete("/{task_id}", response_model=Message)
def delete_task_endpoint(
    ...,
    force: bool = False,  # 新增强制删除参数
):
    # 检查是否有正在运行的相关执行记录
    running_executions = get_executions(..., status=ExecutionStatus.RUNNING)
    
    if task_running_executions and not force:
        # 将这些执行记录标记为失败
        for exec_record in task_running_executions:
            exec_record.status = ExecutionStatus.FAILED
            exec_record.error_message = "任务被删除，执行终止"
            exec_record.completed_at = get_datetime_china()
        session.commit()
    
    scheduler_service.remove_job(task_id)
    cleanup_task_lock(str(task_id))
    delete_task(...)
```

**效果**：
- ✅ 删除任务时自动清理卡住的执行记录
- ✅ 支持强制删除参数 `force=true`

---

### 修复 4：新增诊断脚本

**文件**：`backend/test_scheduler_fix.py`

**用途**：验证修复是否生效

**运行方法**：
```bash
cd G:\agent_eaplore\full-stack-fastapi-template-master\backend
python test_scheduler_fix.py
```

---

## 验证步骤

### 步骤 1：运行诊断脚本
```bash
cd G:\agent_eaplore\full-stack-fastapi-template-master\backend
python test_scheduler_fix.py
```

**预期输出**：
```
✓ 所有检查通过！定时任务应该能正常工作。
```

### 步骤 2：重启后端服务
```bash
# 停止当前运行的后端
# 重新启动
cd G:\agent_eaplore\full-stack-fastapi-template-master\backend
python -m uvicorn app.main:app --reload
```

### 步骤 3：测试定时任务
1. 在 Web 界面手动触发一次定时任务
2. 观察后端日志，应该看到：
   - `定时任务环境信息 - 切换后工作目录：G:\agent_eaplore\full-stack-fastapi-template-master`
   - `定时任务环境信息 - 重新加载后 APIFOX_ACCESS_TOKEN 是否存在：True`
   - `Apifox CLI 执行前检查 - token 是否存在：True`
   - `Apifox CLI 执行成功`

3. 检查钉钉消息，应该收到**成功**通知，而不是"没有权限"错误

### 步骤 4：测试删除卡住的任务
```bash
# 在 API 中添加 force=true 参数
DELETE /api/v1/scheduled-tasks/{task_id}?force=true
```

---

## 技术细节

### 为什么手动执行正常，定时任务失败？

| 项目 | 手动执行 | 定时任务 |
|------|---------|---------|
| 工作目录 | 项目目录 | `C:\Windows\System32` |
| 环境变量 | 完整 | 缺失 |
| PATH | 包含 npm | 可能不包含 |
| 用户上下文 | 登录用户 | 服务账户 |
| .env 加载 | 已加载 | 未加载 |

### 关键修复点

1. **工作目录**：定时任务启动时显式 `os.chdir(project_root)`
2. **环境变量**：定时任务启动时显式 `load_dotenv(override=True)`
3. **PATH**：显式添加 `C:\Program Files\nodejs` 和 `%APPDATA%\npm`
4. **编码**：设置 `PYTHONIOENCODING=utf-8`
5. **状态恢复**：超时/异常后立即更新数据库状态

---

## 后续建议

1. **监控日志**：定期查看 `app.scheduler` 日志，确认没有卡住的任务
2. **设置超时**：为长时间运行的任务配置合适的 `timeout_seconds`
3. **告警机制**：可以添加钉钉告警，当任务连续失败时通知
4. **定期清理**：定期清理旧的执行日志，避免数据库膨胀

---

## 回滚方案

如果修复后出现问题，可以通过以下方式回滚：

1. 恢复 `app/services/apifox.py` 到修改前版本
2. 恢复 `app/services/scheduler_service.py` 到修改前版本
3. 恢复 `app/api/routes/scheduled_tasks.py` 到修改前版本
4. 重启后端服务

---

**修复完成时间**：2025-01-XX
**测试状态**：待验证
