## [2026-02-19 19:00] Radix UI SelectItem 空值导致页面崩溃

### 现象
- 前端定时任务页面点击"新增任务"按钮后，页面跳转到错误页面
- 显示 "Something went wrong. Please try again."
- 没有发送任何后端网络请求

### 影响范围
- 定时任务管理页面无法打开新增/编辑对话框
- 所有使用 Radix UI Select 组件且包含空值选项的页面

### 复现步骤
1. 打开定时任务管理页面
2. 点击"新增任务"按钮
3. 页面崩溃，显示错误页面

### 根因
- Radix UI 的 `SelectItem` 组件不允许 `value=""` 空字符串
- 代码中使用了 `<SelectItem value="">无</SelectItem>` 作为"无"选项
- React 渲染时抛出错误，导致整个页面崩溃

### 解决方案
- 使用非空占位值 `__none__` 替代空字符串：
  ```tsx
  <SelectItem value="__none__">无</SelectItem>
  ```
- 表单提交时将 `__none__` 转换为 `null`：
  ```tsx
  project_id: taskForm.project_id === "__none__" ? null : taskForm.project_id || null
  ```
- 编辑/重置表单时使用 `__none__` 作为默认值

### 验证方式
- 刷新页面后点击"新增任务"按钮
- 对话框正常打开，不再崩溃

### 相关位置
- frontend: src/routes/_layout/scheduled-tasks.tsx

---

## [2026-02-19 20:00] APScheduler ThreadPoolExecutor 无法执行 async 函数

### 现象
- 定时任务触发后显示"执行成功"，但执行历史为空
- 后端日志显示：`RuntimeWarning: coroutine 'execute_scheduled_task' was never awaited`
- 任务实际上没有执行

### 影响范围
- 所有定时任务无法正常执行
- 手动触发任务也无法执行

### 复现步骤
1. 创建一个定时任务
2. 等待任务触发时间或点击"立即触发"
3. 查看执行历史为空
4. 查看后端日志有 coroutine warning

### 根因
- APScheduler 配置使用 `ThreadPoolExecutor`（同步执行器）
- `execute_scheduled_task` 是 async 函数
- ThreadPoolExecutor 无法 await async 函数，导致协程未被调度执行

### 解决方案
- 添加同步包装器函数：
  ```python
  def run_scheduled_task(task_id: str):
      """同步包装器，供 APScheduler 调用"""
      import asyncio
      asyncio.run(execute_scheduled_task(task_id))
  ```
- 将 `add_job` 的 `func` 参数从 `execute_scheduled_task` 改为 `run_scheduled_task`
- 手动触发 API 使用 `asyncio.to_thread()` 调用同步包装器

### 验证方式
- 触发任务后查看执行历史
- 确认有执行记录且状态正确

### 相关位置
- backend: app/services/scheduler_service.py
- backend: app/api/routes/scheduled_tasks.py

---

## [2026-02-19 20:05] 单次执行任务过期后无法手动触发

### 现象
- 单次执行任务设置的时间已过
- 点击"立即触发"按钮显示"已触发执行"
- 但执行历史没有任何记录

### 影响范围
- 所有过期的单次执行任务
- 任务不在调度器中的情况

### 复现步骤
1. 创建一个单次执行任务，时间设为过去
2. 点击"立即触发"按钮
3. 查看执行历史为空

### 根因
- `trigger_job` 方法只在任务存在于调度器中时才能触发
- 单次任务过期后，APScheduler 会将其从调度器中移除
- `trigger_job` 检测到任务不存在，什么都不做

### 解决方案
- 修改 `trigger_task` API：
  ```python
  job = scheduler_service._scheduler.get_job(job_id)
  if job:
      scheduler_service.trigger_job(task_id)
  else:
      # 任务不在调度器中，直接执行
      await asyncio.to_thread(run_scheduled_task, str(task_id))
  ```

### 验证方式
- 创建过期任务后点击触发
- 确认执行历史有记录

### 相关位置
- backend: app/api/routes/scheduled_tasks.py

---

## [2026-02-13 11:25] 终端启动服务命令被 trae-sandbox 误解析

### 现象
- 在终端直接运行 uvicorn / 组合 PowerShell 命令时，出现 `unexpected argument ...` 或命令无输出直接退出
- 导致"启动项目"流程看起来很复杂（需要绕过终端命令解析问题）

### 影响范围
- 后端/前端 dev server 无法用常规单条命令稳定常驻启动
- 多行 PowerShell/带括号与引号的命令更容易失败

### 复现步骤
- 在 Trae 终端执行包含括号/引号/多行的 PowerShell 命令（例如带 try/catch 的命令）
- 或直接运行 `python -m uvicorn ...` 但进程很快退出

### 根因
- 终端命令通过 `trae-sandbox` 包装执行时，对某些字符/多行/引号组合的解析不稳定，导致参数被拆分或被当成额外参数

### 解决方案
- 新增并使用 `app.scripts.spawn_dev`：用 Python `subprocess.Popen(..., DETACHED_PROCESS)` 启动后端/前端并写入日志文件，避免终端解析干扰
- 如需排查启动问题，查看：
  - `backend/.dev/backend.err.log`
  - `frontend/.dev/frontend.err.log`

### 验证方式
- 运行 `python -m app.scripts.spawn_dev` 后，端口监听正常：
  - `127.0.0.1:8000`（后端）
  - `127.0.0.1:5173`（前端）

### 相关位置
- backend: app/scripts/spawn_dev.py

---

## [2026-02-17 10:30] 执行记录不显示项目名称

### 现象
- 项目详情页执行测试后，测试执行列表不显示项目名称
- 执行记录的 `project_name` 字段为空

### 影响范围
- 测试执行模块列表无法显示关联的项目名称
- 项目详情页与测试执行模块数据不一致

### 复现步骤
1. 进入项目详情页
2. 执行一个测试套件或测试场景
3. 切换到测试执行模块查看执行记录
4. 观察项目名称列为空

### 根因
- 创建执行记录时只设置了 `project_id`，未设置 `project_name`
- `TestExecutionCreate` 模型中 `project_name` 字段可选，创建时未填充
- 后端 `create_and_run_execution` 端点没有根据 `project_id` 查询项目名称

### 解决方案
- 在 `create_and_run_execution` 端点中添加逻辑：
  ```python
  project_name = None
  if body.project_id:
      project = get_project(session=session, project_id=body.project_id)
      if project:
          project_name = project.name
  ```
- 创建执行记录时同时设置 `project_id` 和 `project_name`

### 验证方式
- 项目详情页执行测试
- 测试执行模块列表正确显示项目名称
- 数据一致性验证通过

### 相关位置
- backend: app/api/routes/executions/routes.py
- backend: app/crud/project.py

---

## [2026-02-13 20:43] 项目管理 API 返回 500 错误 - UUID 类型转换问题

### 现象
- 访问 `/api/v1/projects/` 接口返回 500 Internal Server Error
- 错误信息：`AttributeError: 'str' object has no attribute 'hex'`

### 影响范围
- 项目管理页面无法加载项目列表
- 所有涉及 project_id 参数的查询都会失败

### 复现步骤
1. 创建一个项目（成功写入数据库）
2. 访问项目列表 API `/api/v1/projects/`
3. 后端返回 500 错误

### 根因
- `project_id` 参数在 API 层以字符串形式传入
- 数据库字段 `Collection.project_id` 和 `TestExecution.project_id` 定义为 UUID 类型
- SQLModel/SQLAlchemy 在执行查询时需要 UUID 对象，但传入的是字符串
- 字符串无法直接与 UUID 字段比较，导致 `value.hex` 调用失败

### 解决方案
- 在 `app/crud/project.py` 中新增 `_to_uuid()` 辅助函数：
  ```python
  def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
      if isinstance(value, uuid.UUID):
          return value
      return uuid.UUID(value)
  ```
- 在所有涉及 project_id/collection_id 查询的地方，使用 `_to_uuid()` 转换参数：
  - `get_project()`
  - `delete_project()`
  - `get_project_stats()`
  - `get_collections_by_project()`
  - `get_collection()`
  - `delete_collection()`

### 验证方式
- 命令行测试：
  ```python
  from app.crud.project import get_project_stats
  from app.core.db import engine
  from sqlmodel import Session
  s = Session(engine)
  print(get_project_stats(session=s, project_id='da0ffa00-4276-468b-a6e6-a4ddc9e632ca'))
  # 输出: total_collections=0 total_executions=0 ...
  ```
- 前端页面 `/projects` 正常加载项目列表

### 相关位置
- backend: app/crud/project.py
- backend: app/api/routes/projects/routes.py

---

## [2026-02-16 18:35] Apifox 测试套件和测试场景同步返回空数据

### 现象
- 前端项目管理页面点击"同步"按钮后，测试套件和测试场景列表为空
- 后端 API `/api/v1/projects/{id}/apifox-collections` 返回空数组 `{"data": []}`
- 用户确认在 Apifox 中已创建测试套件和测试场景，且能成功执行

### 影响范围
- 项目管理模块无法同步 Apifox 的测试套件和测试场景
- 用户无法查看和选择要执行的测试集合

### 复现步骤
1. 打开项目管理页面
2. 点击"同步"按钮
3. 观察测试套件和测试场景列表为空

### 根因分析

#### 第一阶段：数据库字段格式问题
- 数据库中 `apifox_project_id` 字段包含前导空格
- 导致 API 请求 URL 格式错误

#### 第二阶段：API 端点返回空内容
- 使用 HTTP API 端点获取数据：
  - `GET https://api.apifox.com/api/v1/projects/{id}/test-suites`
  - `GET https://api.apifox.com/api/v1/projects/{id}/test-scenarios`
- 这些端点返回 HTTP 200 但内容为空（Content-Length: 0）
- 测试其他端点如 `/api/v1/test-suites/{id}` 返回重定向页面

#### 第三阶段：发现正确的获取方式
- 查阅 Apifox CLI 文档发现：
  - `apifox test-suite list --project <projectId>` - 列出测试套件
  - `apifox test-scenario list --project <projectId>` - 列出测试场景
- CLI 命令成功返回数据（JSON 格式）

### 解决方案

1. **修复数据库字段格式**
   - 清理 `apifox_project_id` 字段的前导空格
   - 后端代码添加 `.strip()` 处理

2. **改用 CLI 命令获取数据**
   ```python
   # 获取测试套件
   cmd = f"npx apifox test-suite list --project {project_id} --access-token {token}"
   
   # 获取测试场景
   cmd = f"npx apifox test-scenario list --project {project_id} --access-token {token}"
   ```

3. **解析 CLI 返回的 JSON 数据**
   ```json
   {
     "success": true,
     "data": [
       {"id": 8145, "name": "测试套件名称", "folder": ""},
       {"id": 8146, "name": "另一个套件", "folder": ""}
     ]
   }
   ```

### 验证方式
- 执行 CLI 命令测试：
  ```bash
  npx apifox test-suite list --project 7822130 --access-token <token>
  ```
- 成功返回 2 个测试套件（ID: 8145, 8146）
- 前端同步功能正常显示测试套件和场景

### 关键发现
- Apifox 的 HTTP API 端点对测试套件/场景的列表查询支持有限
- 应使用 Apifox CLI 命令进行数据获取
- CLI 文档地址：https://docs.apifox.com/5637756m0

### 相关位置
- backend: app/services/apifox.py (get_project_collections 方法)
- backend: app/api/routes/projects/routes.py
- frontend: src/routes/_layout/projects.$projectId.tsx

---

## [2026-02-19 21:30] 缺陷管理页面一直转圈 - loading 状态未正确重置

### 现象
- 访问缺陷管理页面时，页面一直显示加载中（转圈）
- 项目下拉框无内容，新增按钮无法点击

### 影响范围
- 缺陷管理模块完全无法使用

### 复现步骤
1. 登录系统后访问缺陷管理页面
2. 页面一直显示加载状态

### 根因
- `loading` 初始值为 `true`
- `fetchProjects` 函数在没有项目或请求失败时，没有将 `loading` 设置为 `false`
- 导致页面永远处于加载状态

### 解决方案
- 在 `fetchProjects` 函数的所有分支中添加 `setLoading(false)`：
  ```tsx
  const fetchProjects = async () => {
    try {
      const data = await apiGet<{ data: Project[] }>("/api/v1/projects/")
      setProjects(data.data || [])
      if (data.data && data.data.length > 0 && !selectedProject) {
        setSelectedProject(data.data[0].id)
      } else {
        setLoading(false)  // 无项目时重置
      }
    } catch (error) {
      console.error("Failed to fetch projects:", error)
      setLoading(false)  // 出错时重置
    }
  }
  ```

### 验证方式
- 刷新缺陷管理页面
- 页面正常显示（不再转圈）

### 相关位置
- frontend: src/routes/_layout/defects.tsx

---

## [2026-02-19 21:35] 缺陷管理页面 API 请求未携带认证 Token

### 现象
- 缺陷管理页面项目下拉框无内容
- 新增按钮禁用无法点击
- 后端返回 `{"detail":"Not authenticated"}`

### 影响范围
- 缺陷管理模块所有 API 调用失败
- 无法获取项目列表、缺陷列表、枚举值等

### 复现步骤
1. 登录系统后访问缺陷管理页面
2. 打开浏览器开发者工具查看网络请求
3. 所有缺陷相关 API 返回 401 或 "Not authenticated"

### 根因
- 缺陷管理页面使用原生 `fetch` + `credentials: "include"` 方式请求
- 项目其他页面使用 `apiGet/apiPost/apiPut/apiDelete` 封装函数
- 封装函数会从 localStorage 读取 token 并添加 `Authorization: Bearer {token}` 头
- 原生 fetch 方式没有添加 Bearer token，导致认证失败

### 解决方案
- 将所有 `fetch` 调用替换为封装的 API 函数：
  ```tsx
  // 之前
  const response = await fetch(`${API_BASE}/api/v1/projects/`, {
    credentials: "include",
  })
  
  // 之后
  const data = await apiGet<{ data: Project[] }>("/api/v1/projects/")
  ```
- 涉及的函数：
  - `fetchProjects` → `apiGet`
  - `fetchEnums` → `apiGet`
  - `fetchDefects` → `apiGet`
  - `fetchStats` → `apiGet`
  - `fetchModules` → `apiGet`
  - `handleSaveDefect` → `apiPost` / `apiPut`
  - `handleDeleteDefect` → `apiDelete`
  - `handleUpdateStatus` → `apiPut`
- 移除未使用的 `API_BASE` 常量
- 添加 `import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"`

### 验证方式
- 刷新缺陷管理页面
- 项目下拉框正确显示项目列表
- 新增按钮可点击

### 相关位置
- frontend: src/routes/_layout/defects.tsx
- frontend: src/lib/api.ts (API 封装函数)
