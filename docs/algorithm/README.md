# 算法与技术调研

本目录用于保存学习者状态估计、任务推荐、干预策略及 AI 内容校验的技术文档。现有 [AI Agent 技术方案调研报告](../software/architecture.md)覆盖八方面选型、上下文记忆与两周学习计划，按课程要求统一存放在 `docs/software/architecture.md`，状态为待验证建议稿；需求中的策略约束见[功能规格](../requirements/functional_spec.md)。

后续文档按以下职责维护：

- [论文调研与课堂汇报摘要](research.md)：目前整理 RockStartIT AI Tutor 的技术设计、用户评价、研究局限及对 OwlOwlGo 的启示，区分论文证据与小组建议；后续可继续补充候选方法、方案比较及选型依据。
- 各策略说明：输入输出、规则或公式、参数含义、复杂度和验证方式。

算法实现放在 `code/backend/app/domain/`，LLM 适配与校验实现放在 `code/backend/app/integrations/llm/`。形成重要设计选择时同步记录[架构决策](../adr/README.md)。
