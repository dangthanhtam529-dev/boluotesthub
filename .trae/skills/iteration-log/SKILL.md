---
name: "iteration-log"
description: "Record system iteration details including features, architecture changes, and improvements. Invoke when completing feature development, system optimization, or user asks to log iteration progress."
---

# System Iteration Log

This skill helps you maintain a detailed record of every system iteration, including feature additions, architecture improvements, bug fixes, and optimization efforts.

## When to Invoke

Invoke this skill when:
- Completing a significant feature development
- Making architecture changes or improvements
- Fixing critical bugs or issues
- Optimizing system performance
- User explicitly asks to "log iteration", "record progress", or "update changelog"
- After implementing any planned feature from the roadmap

## Document Structure

The iteration log is stored at: `.trae/documents/system-iteration-log.md`

### Log Entry Format

Each iteration entry should include:

```markdown
## [版本号/日期] - 迭代标题

### 变更类型
- [ ] 新功能 (Feature)
- [ ] 架构优化 (Architecture)
- [ ] Bug修复 (Bug Fix)
- [ ] 性能优化 (Performance)
- [ ] 重构 (Refactor)
- [ ] 文档更新 (Documentation)

### 变更概述
简要描述本次迭代的核心内容（2-3句话）

### 详细变更

#### 新增功能
1. 功能名称
   - 实现细节
   - 涉及文件：`path/to/file.py`
   - API接口：`POST /api/v1/xxx`

#### 架构变更
- 变更说明
- 影响范围
- 迁移注意事项

#### Bug修复
- 问题描述
- 根本原因
- 解决方案

### 技术细节
- 新增依赖：package-name@version
- 数据库变更：新增表/字段/索引
- 配置变更：环境变量/配置项

### 影响范围
- 后端：模块名
- 前端：页面/组件
- 数据库：表名
- 第三方服务：服务名

### 测试验证
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过
- 测试用例/场景描述

### 遗留问题
- 待解决问题1
- 待解决问题2

### 后续计划
- 下一步优化方向
- 相关Issue链接
```

## Usage Instructions

### 1. Starting a New Iteration

When beginning work on a new feature or change:

1. Read the current iteration log to understand context
2. Plan the changes with clear scope
3. Document the plan before implementation

### 2. During Development

Update the log entry as you:
- Complete each sub-feature
- Make architectural decisions
- Encounter and solve problems
- Add new dependencies or configurations

### 3. Completing an Iteration

Before marking an iteration as complete:
1. Fill in all sections of the log entry
2. List all affected files and APIs
3. Document any migration steps needed
4. Note any remaining issues or technical debt
5. Verify all tests pass

### 4. Review History

The log serves as:
- Historical record of system evolution
- Reference for similar future changes
- Onboarding material for new developers
- Source for release notes

## Example Entry

```markdown
## [v1.2.0] - 2024-01-15 - 日志系统专业化

### 变更类型
- [x] 新功能 (Feature)
- [x] 架构优化
- [ ] Bug修复
- [ ] 性能优化
- [ ] 重构
- [ ] 文档更新

### 变更概述
将项目中所有 print 语句替换为专业的 logging 系统，
实现结构化日志输出和请求链路追踪。

### 详细变更

#### 新增功能
1. 统一日志配置
   - 新增 `app/core/logging.py`
   - 支持 JSON/文本格式切换
   - 环境变量控制日志级别

2. Request-ID 链路追踪
   - 新增 `asgi-correlation-id` 中间件
   - 每个请求自动分配唯一ID
   - 日志自动注入 request_id

#### 架构变更
- 日志配置从分散改为集中管理
- 引入结构化日志字段规范

### 技术细节
- 新增依赖：asgi-correlation-id==4.3.0
- 配置变更：LOG_LEVEL, LOG_FORMAT 环境变量

### 影响范围
- 后端：apifox.py, mongodb_report.py, mongodb.py
- 配置：.env 新增日志相关配置

### 测试验证
- [x] 单元测试通过
- [x] 集成测试通过
- [x] 手动测试通过
- 验证日志输出格式正确
- 验证 request_id 正确传递

### 遗留问题
- 暂无

### 后续计划
- 考虑添加日志聚合（ELK/Loki）
- 添加慢查询日志告警
```

## Best Practices

1. **及时记录**：开发过程中随时更新，不要等到最后
2. **详细准确**：文件路径、API路径要准确无误
3. **关联Issue**：如果有相关Issue，务必链接
4. **标记影响**：清楚标记变更影响范围
5. **记录决策**：重要的技术决策要记录原因

## File Location

- 技能定义：`.trae/skills/iteration-log/SKILL.md`
- 迭代日志：`.trae/documents/system-iteration-log.md`
