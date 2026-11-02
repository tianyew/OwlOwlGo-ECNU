# API 边界草案

> 全部为待实现接口。当前 FastAPI 仅有框架默认文档，不返回虚构课程、分数或学习记录。

> 2026-11-02：新增正式业务的方向、测评提交和计划生成/修订契约，对应 FR-2、FR-12、FR-13。

前缀 `/api/v1`；JSON 使用 snake_case；后续统一错误对象 `{code, message, request_id}`。列表接口分页；身份由认证依赖确认，不能信任客户端提交的 user_id。写作答和奖励使用幂等键；服务端判断对错和分数。

| 模块 | 方法与路径 | 职责 |
| --- | --- | --- |
| 身份 | POST `/auth/register`、`/auth/login`；POST `/auth/logout` | 账户与会话 |
| 学习档案 | GET/PATCH `/me/profile` | 学习目标、辅助语言、direction_ids、daily_minutes、profile_version；修改携带 expected_version |
| 学习方向 | GET `/learning-directions` | 已启用方向、语言目标、适用范围、资料覆盖说明 |
| 内容 | GET `/lessons`、`/lessons/{id}` | 只读取已审核且可用的课程版本 |
| 汉语资源 | GET `/characters/{id}`、`/phonetics/{id}` | 字形、拼音与授权音频/笔顺元数据 |
| 文化 | GET `/culture-cards`、`/culture-cards/{id}` | 分级文化内容及关联课程 |
| 测评 | POST `/assessments`；GET `/assessments/{id}` | 分维度测评会话及结果 |
| 测评作答与完成 | POST `/assessments/{id}/attempts`；POST `/assessments/{id}/complete` | 校验题目版本并保存作答，满足完成条件后发布诊断快照；均需幂等键 |
| 学习计划 | POST `/learning-plans`；GET `/learning-plans/{id}` | 提交规划任务；读取当前计划、单元详情和实际进度 |
| 计划修订 | POST `/learning-plans/{id}/revisions`；GET `/learning-plans/{id}/revisions` | 根据新目标、诊断或表现生成新版本；读取本人修订历史 |
| 运行状态 | GET `/runs/{id}` | 查询本人规划等异步任务的阶段、结果、失败或回退原因 |
| 学习会话 | POST `/learning-sessions`；GET `/learning-sessions/{id}` | 创建及恢复本人会话；计划内学习校验 plan_revision_id、plan_unit_id 和先修条件 |
| 作答 | POST `/learning-sessions/{id}/attempts` | 接收任务 ID、内容版本、答案、耗时、幂等键；返回判定、反馈与状态摘要 |
| 提示 | POST `/learning-sessions/{id}/hints` | 按既有提示历史返回下一等级及原因 |
| 复习 | GET `/me/reviews` | 到期复习任务 |
| 进度 | GET `/me/progress` | 分维度进度、数据充分程度、建议 |
| 内容管理 | POST `/admin/content`；POST `/admin/content/{id}/review` | 创建候选版本与审核，需管理员权限 |

接口需处理未认证、无权限、未知资源、内容版本冲突、校验失败、限流与外部服务失败。服务端不得在返回未作答任务时泄露标准答案。语音评分、书写识别与商业化接口在专项方案验证后另行定义。

## 前测到计划的接口衔接

1. 创建测评，提交各题答案，再调用完成接口。服务端校验完成条件并返回 `assessment_id、diagnosis_version、dimension_results、evidence_status`；规则版本和题目版本可追溯。
2. 获取方向目录，通过学习档案接口保存选择和时间安排。前端提供 `expected_version`，冲突返回 409 和最新版本；服务端校验方向存在且启用。
3. 创建计划请求携带 `assessment_id、diagnosis_version、profile_version` 和幂等键。服务端读取本人档案、当前知识状态和审核内容，创建计划记录及运行记录，返回 HTTP 202 `{plan_id, run_id, status}`；此时不代表计划生成成功。
4. 客户端查询运行状态。`SUCCEEDED/FALLBACK` 返回 `plan_id、plan_revision_id`；`FAILED/CANCELLED` 返回明确原因且不覆盖已有计划。完成后获取计划及单元详情。
5. 修订请求额外携带 `base_plan_revision_id` 与 `reason`。用户修改方向、重测或阶段表现触发的修订共用同一服务；旧版本继续可读，完成后原子切换当前版本。

计划响应包含 `plan_id、plan_revision_id、goals、direction_ids、assessment_ref、profile_version、units、revision_reason`。每个单元包含 `unit_id、lesson_id、content_version、order、learning_goals、estimated_minutes、prerequisite_unit_ids、completion_criteria、progress、selection_reason`。可以附来源引用，不返回未作答题目的答案。

运行状态为 `QUEUED/BUILDING_CONTEXT/SELECTING_CONTENT/GENERATING/VALIDATING/SUCCEEDED/FALLBACK/FAILED/CANCELLED`；规则流程可跳过生成阶段。`FALLBACK` 必须附 `fallback_reason`，说明使用了规则路径。计划版本状态与运行状态分别管理。

## 一致性与失败行为

- 前测未完成、无有效诊断或方向不可用时，拒绝规划请求并返回可理解的原因（422）。
- 幂等键按用户和操作范围保存，请求体一致时返回同一结果/运行；同键不同请求体返回 409。
- 接收请求和激活计划时均校验档案、基准计划、内容及学习状态版本。执行中输入过时的运行标记 `CANCELLED`，返回 `stale_inputs`；客户端读取最新信息后重新提交。
- 每个计划最多一个 ACTIVE 修订；事务与唯一约束防止重复任务或并发修订重复生效。最终结果、当前修订指针与运行结果一并提交。
- 模型失败可以使用经过相同先修/内容校验的规则计划；内容不足无法规划则失败，保留已有计划。
- 所有测评、计划、修订、单元、会话和 run ID 都做服务端归属校验；模型不得通过工具直接激活计划或写完成进度。
