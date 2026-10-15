# 算法与技术调研

本目录用于保存学习者状态估计、任务推荐、干预策略及 AI 内容校验的技术文档。当前尚未形成独立算法调研成果，需求中的策略约束见[功能规格](../requirements/functional_spec.md)。

后续文档按以下职责维护：

- `research.md`：候选方法、论文与资料来源、方案比较及选型依据。
- 各策略说明：输入输出、规则或公式、参数含义、复杂度和验证方式。

算法实现放在 `code/backend/app/domain/`，LLM 适配与校验实现放在 `code/backend/app/integrations/llm/`。形成重要设计选择时同步记录[架构决策](../adr/README.md)。
