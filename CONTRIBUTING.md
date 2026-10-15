# 贡献指南

## 开始协作

1. 从最新 `main` 创建分支：`feature/<topic>`、`fix/<topic>`、`docs/<topic>`。
2. 在对应 Issue 中确认目标和验收标准。
3. 小步提交，完成后创建 Pull Request，并关联 Issue。
4. 至少一名成员评审通过且检查通过后合并。

## 提交信息

采用约定式提交，例如：

```text
feat: add adaptive intervention endpoint
fix: prevent answer leakage in level-2 hints
docs: refine MVP acceptance criteria
test: cover mastery update rules
chore: configure lint workflow
```

常用类型为 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`。

## Issue 与 Pull Request

Issue 至少写明背景、目标、交付物、验收标准、负责人和截止时间。Pull Request 应说明改了什么、为什么改、如何验证、已知限制，并附关联 Issue。

需求或架构变化不能只改代码：同步更新 README 或 `docs/` 中对应文档。重大技术决定后续记录到 `docs/adr/`。

## 代码质量

- 新功能应包含能验证核心行为的测试；
- 合并前运行格式检查、静态检查和相关测试；
- 不在业务代码中硬编码密钥、外部服务地址或个人配置；
- 策略规则需配置化，并记录策略版本；
- AI 输出必须经过结构与业务校验，不直接信任模型返回值。

## 配置与敏感信息

严禁提交 `.env`、API Key、访问 Token、数据库密码、真实用户数据、个人本地配置和未经授权的第三方题库。仓库只提交 `.env.example`，其中使用无效占位值并写明变量用途。

如发生泄露，应立即撤销并轮换凭据，再清理 Git 历史；只删除最新版本的文件不足以消除历史泄露。

## 文档位置

- `README.md`：项目入口、快速了解和当前状态；
- `docs/`：随代码版本对应的正式需求、设计、测试和发布文档；
- `docs/requirements/`、`docs/algorithm/`、`docs/software/`：需求、算法调研与软件设计；
- `docs/mgmt/`、`docs/retrospection/`：正式项目计划、风险管理与迭代复盘；
- `code/backend/`、`code/frontend/`：前后端源码、依赖及各模块测试；
- `tests/`：跨系统测试、API 契约与 AI 评测；
- GitHub Wiki：会议纪要、FAQ、学习资料和过程讨论；
- GitHub Issues/Projects：任务、缺陷、进度与验收状态。

