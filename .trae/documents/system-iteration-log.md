# 系统迭代日志 (System Iteration Log)

本文档记录系统的每一次重要迭代，包括功能开发、架构优化、Bug修复等。

---

## 目录

- [v1.6.0 - 2026-02-19 - 定时任务模块](#v160---2026-02-19---定时任务模块)
- [v1.5.0 - 2026-02-17 - 通知告警模块](#v150---2026-02-17---通知告警模块)
- [v1.4.0 - 2026-02-17 - 项目详情与测试执行模块数据一致性优化](#v140---2026-02-17---项目详情与测试执行模块数据一致性优化)
- [v1.3.0 - 2026-02-16 - 项目详情页面与路由重构](#v130---2026-02-16---项目详情页面与路由重构)
- [v1.2.0 - 2024-02-13 - 项目管理与报告优化](#v120---2024-02-13---项目管理与报告优化)
- [v1.1.0 - 2024-02-13 - 报告分析与派生数据层](#v110---2024-02-13---报告分析与派生数据层)
- [v1.0.0 - 2024-02-09 - 初始版本](#v100---2024-02-09---初始版本)

---

## [v1.6.0] - 2026-02-19 - 定时任务模块

### 变更类型
- [x] 新功能
- [x] 架构优化
- [x] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
实现定时任务模块，支持 Cron 表达式、固定间隔、单次执行三种触发方式，
集成 APScheduler 调度器，支持任务管理、手动触发、执行历史查看等功能。

### 详细变更

#### 新增功能

1. **定时任务管理**
   - 支持三种触发类型：Cron 表达式、固定间隔、单次执行
   - 任务启用/禁用切换
   - 任务编辑和删除
   - 关联项目和通知规则

2. **调度器服务**
   - 使用 APScheduler AsyncIOScheduler
   - SQLAlchemyJobStore 持久化任务
   - 应用启动时自动恢复已启用的任务
   - misfire_grace_time 容错机制（5分钟）

3. **手动触发执行**
   - 支持立即触发任务执行
   - 兼容任务不在调度器中的情况

4. **执行历史记录**
   - 记录每次执行的状态、时间、错误信息
   - 支持查看任务执行日志

5. **前端管理页面**
   - 任务列表展示
   - 新增/编辑任务对话框
   - 执行历史标签页
   - 导航菜单集成

#### 架构变更

1. **数据模型**
   - `ScheduledTask` - 定时任务模型
   - `TaskExecutionLog` - 执行日志模型

2. **服务层**
   - `scheduler_service.py` - 调度器服务
   - `run_scheduled_task()` - 同步包装器（解决 async/sync 兼容问题）

3. **数据库表**
   - `scheduled_tasks` - 任务表
   - `task_execution_logs` - 执行日志表
   - `apscheduler_jobs` - APScheduler 持久化表

#### Bug修复

1. **Radix UI SelectItem 空值崩溃**
   - 问题：`SelectItem value=""` 导致页面崩溃
   - 解决：使用 `__none__` 作为占位值，提交时转换为 null

2. **APScheduler async/sync 兼容问题**
   - 问题：ThreadPoolExecutor 无法执行 async 函数
   - 解决：添加 `run_scheduled_task()` 同步包装器，使用 `asyncio.run()`

3. **单次任务过期后无法触发**
   - 问题：任务过期后被 APScheduler 丢弃，不在调度器中
   - 解决：手动触发时检查任务是否存在，不存在则直接调用执行函数

### 技术细节

- 新增依赖：APScheduler==3.10.4
- 新增文件：
  - `backend/app/models/scheduled_task.py` - 数据模型
  - `backend/app/crud/scheduled_task.py` - CRUD 操作
  - `backend/app/api/routes/scheduled_tasks.py` - API 路由
  - `backend/app/services/scheduler_service.py` - 调度器服务
  - `frontend/src/routes/_layout/scheduled-tasks.tsx` - 前端页面
- 数据库迁移：`c0f74d4a30db_add_scheduled_task_tables.py`

### 影响范围

- 后端：
  - `app/models/scheduled_task.py` - 新增模型
  - `app/crud/scheduled_task.py` - 新增 CRUD
  - `app/api/routes/scheduled_tasks.py` - 新增 API
  - `app/services/scheduler_service.py` - 新增服务
  - `app/api/main.py` - 路由注册
  - `app/main.py` - 启动时恢复任务
- 前端：
  - `src/routes/_layout/scheduled-tasks.tsx` - 新增页面
  - `src/components/Sidebar/AppSidebar.tsx` - 导航更新

### API 变更

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/v1/scheduled-tasks/` | GET | 任务列表 |
| `/api/v1/scheduled-tasks/` | POST | 创建任务 |
| `/api/v1/scheduled-tasks/{id}` | GET | 任务详情 |
| `/api/v1/scheduled-tasks/{id}` | PUT | 更新任务 |
| `/api/v1/scheduled-tasks/{id}` | DELETE | 删除任务 |
| `/api/v1/scheduled-tasks/{id}/enable` | POST | 启用任务 |
| `/api/v1/scheduled-tasks/{id}/disable` | POST | 禁用任务 |
| `/api/v1/scheduled-tasks/{id}/trigger` | POST | 立即触发 |
| `/api/v1/scheduled-tasks/{id}/logs` | GET | 执行日志 |
| `/api/v1/scheduled-tasks/logs/all` | GET | 所有执行日志 |

### 测试验证

- [x] 数据库迁移成功
- [x] 任务 CRUD API 正常
- [x] Cron 任务调度正常
- [x] 间隔任务调度正常
- [x] 单次任务调度正常
- [x] 手动触发执行正常
- [x] 执行历史记录正常
- [x] 前端页面正常显示

### 遗留问题

- 任务执行失败时的重试机制待实现
- 任务执行超时处理待完善

### 后续计划

- 实现任务执行重试机制
- 添加任务执行超时配置
- 实现任务执行结果通知

---

## [v1.5.0] - 2026-02-17 - 通知告警模块

### 变更类型
- [x] 新功能
- [ ] 架构优化
- [ ] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
实现通知告警模块，支持钉钉、企业微信等渠道的消息推送，
实现测试执行完成后自动触发通知，完善执行闭环。

### 详细变更

#### 新增功能

1. **通知渠道管理**
   - 支持钉钉机器人（Webhook + 加签）
   - 支持企业微信机器人（Webhook）
   - 支持邮件（预留）
   - 渠道测试发送功能

2. **通知规则管理**
   - 触发类型：执行完成、执行失败、阈值告警
   - 多渠道路由：一条规则可发送到多个渠道
   - 项目级规则：可关联特定项目或全局

3. **通知发送服务**
   - `NotificationService` - 消息发送核心服务
   - `NotificationBuilder` - 消息内容构建器
   - `NotificationTrigger` - 事件触发器

4. **执行完成触发通知**
   - 测试执行完成后自动触发通知
   - 通过率低于阈值时触发告警
   - 记录通知发送日志

5. **前端通知管理页面**
   - 通知渠道配置（增删改查）
   - 通知规则配置（增删改查）
   - 发送记录查看

#### 架构变更

1. **数据模型**
   - `NotificationChannel` - 通知渠道
   - `NotificationRule` - 通知规则
   - `NotificationLog` - 通知日志

2. **服务层**
   - `notification_service.py` - 消息发送
   - `notification_trigger.py` - 事件触发

### 技术细节

- 新增文件：
  - `backend/app/models/notification.py` - 数据模型
  - `backend/app/crud/notification.py` - CRUD 操作
  - `backend/app/api/routes/notifications.py` - API 路由
  - `backend/app/services/notification_service.py` - 发送服务
  - `backend/app/services/notification_trigger.py` - 触发器
  - `frontend/src/routes/_layout/notifications.tsx` - 前端页面

- 依赖说明：
  - 钉钉加签使用 `hmac` + `hashlib` 实现
  - HTTP 请求使用 `httpx` 异步客户端

### 影响范围

- 后端：
  - `app/models/notification.py` - 新增模型
  - `app/crud/notification.py` - 新增 CRUD
  - `app/api/routes/notifications.py` - 新增 API
  - `app/api/routes/executions/routes.py` - 集成通知触发
  - `app/services/notification_service.py` - 新增服务
  - `app/services/notification_trigger.py` - 新增触发器
- 前端：
  - `src/routes/_layout/notifications.tsx` - 新增页面
  - `src/components/Sidebar/AppSidebar.tsx` - 导航更新

### API 变更

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/v1/notifications/channels` | GET | 渠道列表 |
| `/api/v1/notifications/channels` | POST | 创建渠道 |
| `/api/v1/notifications/channels/{id}` | PUT | 更新渠道 |
| `/api/v1/notifications/channels/{id}` | DELETE | 删除渠道 |
| `/api/v1/notifications/channels/test` | POST | 测试发送 |
| `/api/v1/notifications/rules` | GET | 规则列表 |
| `/api/v1/notifications/rules` | POST | 创建规则 |
| `/api/v1/notifications/rules/{id}` | PUT | 更新规则 |
| `/api/v1/notifications/rules/{id}` | DELETE | 删除规则 |
| `/api/v1/notifications/logs` | GET | 发送记录 |

### 测试验证

- [x] 通知渠道 CRUD 正常
- [x] 通知规则 CRUD 正常
- [x] 钉钉消息发送正常
- [x] 企业微信消息发送正常
- [x] 执行完成触发通知正常
- [x] 前端页面正常显示

### 遗留问题

- 邮件发送功能待实现
- 定时报表推送待实现

### 后续计划

- 实现邮件发送功能
- 实现定时任务模块
- 实现定时报表推送

---

## [v1.4.0] - 2026-02-17 - 项目详情与测试执行模块数据一致性优化

### 变更类型
- [x] 新功能
- [x] 架构优化
- [x] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
解决项目详情页面与测试执行模块数据不一致的问题，实现执行记录按项目筛选、
项目名称自动填充、测试执行模块支持项目选择和筛选等功能。

### 详细变更

#### 新增功能

1. **执行记录按项目筛选**
   - 后端 `get_executions` 和 `count_executions` 支持 `project_id` 参数
   - 前端项目详情页执行历史按 `project_id` 筛选

2. **一键执行测试 API**
   - 新增 `POST /api/v1/executions/run` 端点
   - 一步完成创建执行记录并执行测试
   - 支持 `project_id`、`collection_id`、`collection_type`、`environment` 参数

3. **测试执行模块项目选择**
   - 新增项目下拉选择框，执行时可关联项目
   - 新增项目筛选下拉框，可按项目筛选执行记录
   - 移除原"项目名称"手动输入框

4. **项目名称自动填充**
   - 创建执行记录时根据 `project_id` 自动查询项目名称
   - 执行记录列表正确显示关联的项目名称

#### 架构变更

1. **API 参数传递方式**
   - 执行 API 从 Query 参数改为 JSON Body 参数
   - 新增 `ExecutionRunRequest` Pydantic 模型

2. **前端执行流程简化**
   - 原：创建执行记录 → 调用执行接口
   - 新：调用 `/run` 接口一步完成

#### Bug修复

1. **执行记录不显示项目名称**
   - 问题：项目详情页执行测试后，测试执行列表不显示项目名称
   - 原因：创建执行记录时只设置了 `project_id`，未设置 `project_name`
   - 解决：后端根据 `project_id` 自动查询并填充 `project_name`

2. **API 响应格式不一致**
   - 问题：前端请求 `/api/v1/projects/${projectId}/executions` 返回 404
   - 原因：后端没有该端点
   - 解决：前端改为使用 `/api/v1/executions/?project_id=${projectId}`

### 技术细节

- 文件变更：
  - 修改 `backend/app/crud/execution.py` - 添加 project_id 筛选
  - 修改 `backend/app/api/routes/executions/routes.py` - 新增 /run 端点
  - 修改 `backend/app/services/apifox.py` - 添加 access_token 参数
  - 修改 `frontend/src/routes/_layout/projects/$projectId.tsx` - 执行历史筛选
  - 修改 `frontend/src/routes/_layout/executions.tsx` - 项目选择和筛选

- 新增模型：
  - `ExecutionRunRequest` - 执行请求参数模型

### 影响范围

- 后端：
  - `app/crud/execution.py` - 筛选功能
  - `app/api/routes/executions/routes.py` - 新增 API
  - `app/services/apifox.py` - 参数扩展
- 前端：
  - `src/routes/_layout/projects/$projectId.tsx` - 项目详情执行
  - `src/routes/_layout/executions.tsx` - 测试执行模块

### API 变更

| 接口 | 方法 | 变更说明 |
|------|------|----------|
| `/api/v1/executions/run` | POST | 新增：一步创建并执行测试 |
| `/api/v1/executions/` | GET | 新增 `project_id` 查询参数 |

### 测试验证

- [x] 项目详情页执行测试正常
- [x] 执行记录正确关联项目
- [x] 执行记录列表显示项目名称
- [x] 测试执行模块项目筛选正常
- [x] 数据一致性验证通过

### 遗留问题

- 暂无

### 后续计划

- 完善项目成员管理
- 添加定时任务功能
- 完善告警通知系统

---

## [v1.3.0] - 2026-02-16 - 项目详情页面与路由重构

### 变更类型
- [x] 新功能
- [x] 架构优化
- [x] Bug修复
- [ ] 性能优化
- [x] 重构
- [ ] 文档更新

### 变更概述
重构前端路由结构，实现项目详情页面完整功能，包括测试套件/场景同步、
执行历史展示、项目统计概览、执行趋势图表、项目设置等功能。

### 详细变更

#### 新增功能

1. **项目详情页面**
   - 项目基本信息展示（名称、描述、Apifox项目ID）
   - 项目统计概览卡片（测试套件数、测试场景数、执行次数、通过率、平均耗时）
   - 最近7天执行趋势图表
   - 测试套件/场景列表展示（支持保存、执行操作）
   - 执行历史记录展示
   - 项目设置对话框（编辑项目信息）

2. **测试项详情对话框**
   - 显示测试套件/场景详细信息
   - 最近执行记录列表
   - 支持保存到项目和执行操作

3. **Apifox CLI 集成**
   - 使用 `npx apifox test-suite list` 获取测试套件
   - 使用 `npx apifox test-scenario list` 获取测试场景
   - 替代原有 HTTP API 方式（API返回空内容）

#### 架构变更

1. **前端路由重构**
   - 原 `projects.tsx` 拆分为布局路由
   - 新增 `projects/index.tsx` 项目列表页面
   - 新增 `projects/$projectId.tsx` 项目详情页面
   - 正确使用 TanStack Router 的嵌套路由机制

2. **API 响应格式修复**
   - 项目详情 API 直接返回对象，非 `{data: ...}` 格式
   - 前端代码适配正确响应格式

#### Bug修复

1. **路由导航问题**
   - 问题：点击"进入"按钮URL变化但页面不更新
   - 原因：`projects.tsx` 未使用 `<Outlet />` 渲染子路由
   - 解决：重构为布局路由 + 子路由结构

2. **API 响应解析错误**
   - 问题：`res.data` 为 undefined，项目数据无法加载
   - 原因：后端直接返回对象，前端期望 `{data: ...}` 格式
   - 解决：修改前端代码直接使用响应对象

3. **Apifox 同步返回空数据**
   - 问题：HTTP API 端点返回 200 OK 但内容为空
   - 原因：Apifox HTTP API 对测试套件/场景列表查询支持有限
   - 解决：改用 CLI 命令 `npx apifox test-suite/scenario list`

4. **数据库字段格式问题**
   - 问题：`apifox_project_id` 包含前导空格导致 API 请求失败
   - 解决：清理数据库数据，后端代码添加 `.strip()` 处理

### 技术细节

- 文件变更：
  - 新增 `frontend/src/routes/_layout/projects/index.tsx`
  - 新增 `frontend/src/routes/_layout/projects/$projectId.tsx`
  - 重构 `frontend/src/routes/_layout/projects.tsx` 为布局路由
  - 删除 `frontend/src/routes/_layout/projects.$projectId.tsx`
  - 修改 `backend/app/services/apifox.py` 使用 CLI 命令

- 依赖说明：
  - Apifox CLI 通过 `npx apifox` 运行，无需全局安装
  - CLI 文档：https://docs.apifox.com/5637756m0

### 影响范围

- 后端：
  - `app/services/apifox.py` - 同步方法改用 CLI
  - `app/api/routes/projects/routes.py` - API 响应格式
- 前端：
  - `src/routes/_layout/projects.tsx` - 布局路由
  - `src/routes/_layout/projects/index.tsx` - 项目列表
  - `src/routes/_layout/projects/$projectId.tsx` - 项目详情
  - `src/routeTree.gen.ts` - 自动生成路由配置
- 数据库：清理 `apifox_project_id` 字段空格

### API 变更

| 接口 | 变更说明 |
|------|----------|
| `GET /projects/{id}` | 响应格式确认：直接返回 ProjectPublic 对象 |
| `GET /projects/{id}/apifox-collections` | 改用 CLI 命令获取数据 |
| `GET /projects/{id}/apifox-info` | 改用 CLI 命令获取数据 |

### 测试验证

- [x] 项目列表页面正常显示
- [x] 点击"进入"按钮正确跳转到项目详情
- [x] 项目详情页面数据正确加载
- [x] Apifox 同步功能正常工作
- [x] 测试套件/场景列表正确显示
- [x] 执行历史正确展示
- [x] 项目设置保存功能正常

### 遗留问题

- 执行测试功能待验证完整流程
- 项目成员权限管理待实现
- 定时任务功能待实现

### 后续计划

- 完善执行测试流程
- 实现项目成员管理
- 添加定时任务功能
- 完善告警通知系统

---

## [v1.2.0] - 2024-02-13 - 项目管理与报告优化

### 变更类型
- [x] 新功能
- [x] 架构优化
- [x] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
新增项目管理模块，实现测试执行按项目隔离；优化报告解析逻辑，
修复测试用例统计不准确的问题；支持从 Apifox 同步项目测试集合。

### 详细变更

#### 新增功能

1. **项目管理模块**
   - Project 数据模型：项目名称、描述、Apifox项目ID关联
   - Collection 数据模型：测试集合，关联项目和 Apifox
   - 项目 CRUD API：创建、查询、更新、删除项目
   - 项目统计 API：获取项目执行统计信息

2. **Apifox 同步功能**
   - `GET /projects/{id}/sync` - 从 Apifox 同步测试集合
   - `apifox.get_project_collections()` - 获取 Apifox 项目下的测试套件/场景
   - `apifox.get_project_info()` - 获取 Apifox 项目信息

3. **项目级数据隔离**
   - TestExecution 新增 `project_id` 字段
   - MongoDB 报告新增 `project_id` 字段
   - 所有分析 API 支持 `project_id` 筛选参数

4. **前端项目管理页面**
   - 项目列表展示（卡片布局）
   - 创建/编辑项目对话框
   - 同步 Apifox 测试集合
   - 导航菜单更新

#### Bug修复

1. **报告统计不准确**
   - 问题：执行失败时只显示"操作失败"，不显示具体用例统计
   - 原因：使用了错误的统计字段（tests 而非 steps）
   - 解决：优先使用 `stats.steps` 统计，添加 fallback 逻辑

2. **原始报告缺少详细信息**
   - 问题：报告中没有 `executions` 数组，无法获取详细执行数据
   - 原因：Apifox CLI 默认不输出详细执行结果
   - 解决：添加 `--verbose` 参数获取完整数据

3. **失败用例信息不完整**
   - 问题：失败详情缺少 API 路径、方法等信息
   - 原因：未正确映射 failures 到 executions
   - 解决：通过 cursor.ref 建立 failures 与 executions 的映射关系

### 技术细节

- 数据库变更：
  - 新增 `projects` 表
  - 新增 `collections` 表
  - `testexecution` 表新增 `project_id` 字段
- 迁移文件：`1439c35dd6d0_add_projects_and_collections_tables.py`
- 新增依赖：httpx（用于 Apifox API 调用）

### 影响范围

- 后端：
  - `app/models/project.py` - 新增模型
  - `app/crud/project.py` - 新增 CRUD 操作
  - `app/api/routes/projects/` - 新增项目 API
  - `app/services/apifox.py` - 新增同步方法
  - `app/services/mongodb_report.py` - 支持 project_id 筛选
- 前端：
  - `src/routes/_layout/projects.tsx` - 项目管理页面
  - `src/components/Sidebar/AppSidebar.tsx` - 导航更新
  - `src/routeTree.gen.ts` - 路由配置
- 数据库：MySQL 新增2张表，修改1张表

### API 变更

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/v1/projects/` | GET | 项目列表 |
| `/api/v1/projects/` | POST | 创建项目 |
| `/api/v1/projects/{id}` | GET | 项目详情 |
| `/api/v1/projects/{id}` | PUT | 更新项目 |
| `/api/v1/projects/{id}` | DELETE | 删除项目 |
| `/api/v1/projects/{id}/sync` | POST | 同步 Apifox |
| `/api/v1/projects/{id}/collections` | GET | 测试集合列表 |
| `/api/v1/projects/{id}/collections` | POST | 添加测试集合 |

所有分析 API 新增 `project_id` 查询参数。

### 测试验证

- [x] 数据库迁移成功
- [x] 项目 CRUD API 正常工作
- [x] Apifox 同步功能正常
- [x] 报告统计显示正确（3用例，2成功，1失败）
- [x] 前端项目页面正常加载

### 遗留问题

- 项目详情页面待实现（测试集合管理、执行历史）
- 执行测试时需要支持选择项目
- 项目成员权限管理待实现

### 后续计划

- 实现项目详情页面
- 执行测试时关联项目
- 项目成员与权限管理
- 项目级别配置（告警、通知）

---

## [v1.1.0] - 2024-02-13 - 报告分析与派生数据层

### 变更类型
- [x] 新功能
- [x] 架构优化
- [ ] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
实现 MongoDB 派生数据层，支持报告摘要、失败详情、请求明细的独立存储，
并新增多个分析 API 接口支持趋势分析、失败归类、性能统计等功能。

### 详细变更

#### 新增功能

1. **派生数据集合**
   - `report_summaries` - 执行摘要（统计、指标、请求统计）
   - `report_failures` - 失败详情（按指纹去重）
   - `report_requests` - 请求明细（每个请求一条记录）
   - `report_notes` - 备注知识库（失败归类备注）

2. **分析 API 接口**
   - `GET /analytics/overview` - 概览统计
   - `GET /analytics/trend` - 趋势分析
   - `GET /analytics/failed-apis` - 失败API分析
   - `GET /analytics/performance` - 性能分析
   - `GET /analytics/failure-signatures` - 失败归类
   - `GET /analytics/flaky` - 不稳定用例识别
   - `GET /analytics/slow-apis` - 慢接口分析
   - `GET /analytics/compare` - 执行对比
   - `PUT /analytics/note` - 保存备注

3. **前端分析页面**
   - 报告分析页面 (`/reports`)
   - 支持概览、趋势、失败、性能、对比等多个标签页
   - 支持按集合ID和时间范围筛选

#### 架构变更

- **数据分层**：Raw（原始报告）+ Derived（派生数据）
- **失败指纹**：基于 api_path + method + status + error_norm 生成唯一指纹
- **错误归一化**：去除动态值（UUID、数字）便于错误聚合

### 技术细节

- 新增方法：
  - `MongoDBReportService.upsert_derived()` - 同步生成派生数据
  - `MongoDBReportService._extract_summary()` - 提取摘要
  - `MongoDBReportService._extract_requests()` - 提取请求明细
  - `MongoDBReportService._fingerprint_failure()` - 生成失败指纹
  - `MongoDBReportService._normalize_error()` - 错误归一化

### 影响范围

- 后端：`app/services/mongodb_report.py`, `app/api/routes/executions/routes.py`
- 前端：`src/routes/_layout/reports.tsx`
- 数据库：MongoDB 新增4个集合

### 测试验证

- [x] 执行测试后派生数据正确生成
- [x] 分析API返回正确数据
- [x] 前端页面正确展示分析结果

### 遗留问题

- 日志系统仍使用 print，需要专业化
- 缺少 MongoDB 索引优化
- 前端图表可视化可以增强

### 后续计划

- 实现专业日志系统
- 添加 MongoDB 索引
- 增强前端图表展示

---

## [v1.0.0] - 2024-02-09 - 初始版本

### 变更类型
- [x] 新功能
- [x] 架构优化
- [ ] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
基于 FastAPI 模板项目，实现 Apifox 测试执行平台的核心功能，
包括测试执行、报告存储、用户管理等基础模块。

### 详细变更

#### 新增功能

1. **测试执行模块**
   - Apifox CLI 集成
   - 测试套件/场景执行
   - 执行记录管理（CRUD）

2. **双数据库架构**
   - MySQL：执行记录、用户数据
   - MongoDB：完整测试报告

3. **用户认证系统**
   - JWT Token 认证
   - 用户管理（管理员功能）
   - 密码加密存储

4. **审计日志**
   - 操作日志记录
   - 日志查询接口

5. **前端页面**
   - 登录页面
   - 测试执行页面
   - 用户管理页面
   - 审计日志页面

### 技术细节

- 后端框架：FastAPI + SQLModel + Motor
- 前端框架：React + Vite + TanStack Router
- 数据库：MySQL 8.0 + MongoDB 7.0
- 认证：JWT + Argon2 密码哈希

### 影响范围

- 全新项目初始化

### 测试验证

- [x] 用户登录/登出
- [x] 测试执行流程
- [x] 报告存储到 MongoDB

### 遗留问题

- 报告分析功能待完善
- 日志系统待优化

### 后续计划

- 实现报告分析功能
- 完善日志系统

---

## 迭代统计

| 版本 | 日期 | 主要内容 | 状态 |
|------|------|----------|------|
| v1.6.0 | 2026-02-19 | 定时任务模块 | ✅ 已完成 |
| v1.5.0 | 2026-02-17 | 通知告警模块 | ✅ 已完成 |
| v1.4.0 | 2026-02-17 | 项目详情与测试执行模块数据一致性优化 | ✅ 已完成 |
| v1.3.0 | 2026-02-16 | 项目详情页面与路由重构 | ✅ 已完成 |
| v1.2.0 | 2024-02-13 | 项目管理与报告优化 | ✅ 已完成 |
| v1.1.0 | 2024-02-13 | 报告分析与派生数据层 | ✅ 已完成 |
| v1.0.0 | 2024-02-09 | 初始版本 | ✅ 已完成 |

---

## 待办事项

- [ ] 日志系统专业化
- [ ] MongoDB 索引优化
- [ ] 前端图表增强
- [x] 项目详情页面实现
- [x] 执行测试关联项目
- [ ] 项目成员权限管理
- [x] 定时任务功能
- [x] 告警通知系统
- [ ] 任务执行重试机制
- [ ] 任务执行超时配置

---

*本文档由 iteration-log 技能自动维护*
