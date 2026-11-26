# Application services

当前 `agents/dispatcher.py` 按事件选择已注册的前测分析 Agent；`agents/assessment.py` 调用模型适配器，校验结构化输出及逐题证据引用。
普通学习读写与分析编排仍由 API 路由连接仓储和 Agent，尚未形成完整的学习用例服务层。

后续根据实际用例建立，以下文件尚未实现：

- `assessment_service.py`：测评流程；
- `learning_session_service.py`：学习会话与下一题；
- `attempt_service.py`：作答、状态更新和反馈事务；
- `intervention_service.py`：主动求助与策略编排；
- `report_service.py`：学习报告；
- `content_service.py`：题库与 AI 候选内容审核。

