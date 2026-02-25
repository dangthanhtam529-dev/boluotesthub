# 安全修复记录

## 发现的问题
- Git 历史记录中泄露了敏感信息（Apifox Token）
- 日志文件中包含 DingTalk access_token

## 修复措施
1. 从代码文件中移除了真实的 API Token
2. 将日志目录添加到 .gitignore
3. 更新了 start.bat 中的占位符

## 需要用户执行的操作
1. 在 Apifox 平台撤销已泄露的 Token
2. 生成新的 Token 并更新本地配置
3. 强制推送清理后的 Git 历史

## 时间戳
修复时间: 2026-02-25
