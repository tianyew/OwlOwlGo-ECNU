# Repositories

封装持久化查询，使领域层和应用服务不直接依赖 SQLAlchemy 查询细节。

`accounts.py` 定义账号仓储协议和 JSON 实现，`postgres_accounts.py` 为 PostgreSQL 实现。
`learning.py` 保存学习进度、草稿、幂等提交与分析，目前仍为 JSON 实现。
两个 JSON 仓储共用 `app.db.json_store.JsonFileStore` 的文件锁和原子写入；
每次读改写必须在同一文件锁内完成，仓储之间不通过继承复用业务方法。

