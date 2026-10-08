# Backend

OwlOwlGo 后端，规划使用 FastAPI、Pydantic、SQLAlchemy 和 PostgreSQL。

采用分层结构：

- `app/api/`：HTTP 路由、依赖和版本入口；
- `app/core/`：配置、安全、日志和通用基础设施；
- `app/domain/`：不依赖 Web 框架的核心学习领域规则；
- `app/services/`：应用用例编排；
- `app/db/`：数据库会话、模型和仓储实现；
- `app/schemas/`：输入输出数据结构；
- `app/integrations/`：LLM 等外部服务适配；
- `tests/`：后端自动化测试。

