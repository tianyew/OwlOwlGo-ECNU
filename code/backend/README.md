# Backend

OwlOwlGo 后端使用 FastAPI 和 Pydantic。账号、会话和认证限流通过 SQLAlchemy + psycopg 存入 PostgreSQL；学习进度暂时保存在 JSON 文件中。配置 `DATABASE_URL` 启用数据库，空值保留旧 JSON 兼容模式。

注册、登录、会话查询和退出已实现。课程目录、全部前测/单元/后测的判分、幂等提交、草稿恢复和证据画像也已实现，见[完整学习链路](../../docs/software/server-unit-demo.md)。Docker 数据库启动、建表、旧账号导入与配置见[账号说明](../../docs/software/accounts.md)。测试：`.venv/bin/python -m pytest`；真实数据库测试加 `--postgres`。

采用分层结构：

- `app/api/`：HTTP 路由、依赖和版本入口；
- `app/core/`：配置、安全、日志和通用基础设施；
- `app/domain/`：不依赖 Web 框架的核心学习领域规则；
- `app/services/`：应用用例编排；
- `app/db/`：数据库会话、模型和仓储实现；
- `app/schemas/`：输入输出数据结构；
- `app/integrations/`：LLM 等外部服务适配；
- `tests/`：后端自动化测试。

## 日志

启动后端后，应用日志同时输出到控制台和 `code/backend/logs/app.log`，目录自动创建。
日志包含时间、级别、模块、启动/停止事件，以及请求的方法、路由模板、状态码和耗时。
请求日志不记录请求体、查询参数、Cookie 或 Authorization；异常记录调用栈和类型，省略可能包含数据库参数等敏感信息的异常消息。
Uvicorn 和第三方库保留原有日志配置，不写入此应用日志文件。

在 `code/backend/.env` 中可设置 `OWL_LOG_FILE`（相对路径以后端目录为基准）、
`OWL_LOG_LEVEL`（默认 `INFO`，支持 `DEBUG/INFO/WARNING/ERROR/CRITICAL`）、
`OWL_LOG_MAX_BYTES`（默认 10 MiB）和 `OWL_LOG_BACKUP_COUNT`（默认 5）。
达到大小上限后自动轮转为 `app.log.1` 等文件；日志目录已被 Git 忽略。
当前文件轮转适用于单进程后端；多 worker 部署时应为每个进程配置独立文件或使用集中日志服务。
Docker 中如需保留日志，可将 `OWL_LOG_FILE` 设为 `/app/local-data/logs/app.log`，使用现有持久卷。

业务代码使用模块名获取 logger，避免在日志消息中加入密码、令牌或用户提交的内容：

```python
import logging

logger = logging.getLogger(__name__)
logger.info("assessment_completed")
```

