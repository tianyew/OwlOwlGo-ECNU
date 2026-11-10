# Backend

OwlOwlGo 后端使用 FastAPI 和 Pydantic。当前账号体系使用 JSON 文档仓储；正式数据库待团队讨论，已有 SQLAlchemy/PostgreSQL 依赖暂保留。

注册、登录、会话查询和退出已实现。课程目录、全部前测/单元/后测的判分、幂等提交、草稿恢复和证据画像也已实现，见[完整学习链路](../../docs/software/server-unit-demo.md)。运行方式、JSON 数据位置及 MongoDB 迁移边界见 [账号说明](../../docs/software/accounts.md)。测试：`.venv/bin/python -m pytest`。

采用分层结构：

- `app/api/`：HTTP 路由、依赖和版本入口；
- `app/core/`：配置、安全、日志和通用基础设施；
- `app/domain/`：不依赖 Web 框架的核心学习领域规则；
- `app/services/`：应用用例编排；
- `app/db/`：数据库会话、模型和仓储实现；
- `app/schemas/`：输入输出数据结构；
- `app/integrations/`：LLM 等外部服务适配；
- `tests/`：后端自动化测试。

