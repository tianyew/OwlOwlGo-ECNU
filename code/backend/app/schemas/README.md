# Schemas

按 API 资源维护输入输出结构，并单独定义学习事件和 LLM 结构化输出契约。

`auth.py` 定义账号请求与公开用户结构；`learning.py` 定义学习状态与保存请求；
`unit_quiz.py` 定义测验答案、提交与重测请求。领域计算放在 `app.domain`，不在 schema 中加载题库或生成分析证据。

