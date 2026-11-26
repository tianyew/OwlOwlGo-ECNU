# Database migrations

当前初始迁移为版本 1，由 `app/db/session.py` 的 `initialize_schema` 执行，表定义位于 `app/db/models/accounts.py`。运行 `python -m app.db.manage init` 建立账号、会话、限流和版本记录表；使用 PostgreSQL 事务与 advisory lock 串行化迁移，重复执行不删除数据。

尚未引入 Alembic。后续表结构变更必须新增明确的版本迁移（或引入 Alembic 并建立版本 1 基线），不能仅修改 metadata 后调用 `create_all`。API 启动仅检查版本，不自动修改 schema。导入旧数据见 `python -m app.db.manage import-json --help` 和[账号文档](../../../docs/software/accounts.md)。

