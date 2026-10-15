# API 边界草案

> 全部为待实现接口。当前 FastAPI 仅有框架默认文档，不返回虚构课程、分数或学习记录。

前缀 `/api/v1`；JSON 使用 snake_case；后续统一错误对象 `{code, message, request_id}`。列表接口分页；身份由认证依赖确认，不能信任客户端提交的 user_id。写作答和奖励使用幂等键；服务端判断对错和分数。

| 模块 | 方法与路径 | 职责 |
| --- | --- | --- |
| 身份 | POST `/auth/register`、`/auth/login`；POST `/auth/logout` | 账户与会话 |
| 学习档案 | GET/PATCH `/me/profile` | 学习目标、辅助语言和偏好 |
| 内容 | GET `/lessons`、`/lessons/{id}` | 只读取已审核且可用的课程版本 |
| 汉语资源 | GET `/characters/{id}`、`/phonetics/{id}` | 字形、拼音与授权音频/笔顺元数据 |
| 文化 | GET `/culture-cards`、`/culture-cards/{id}` | 分级文化内容及关联课程 |
| 测评 | POST `/assessments`；GET `/assessments/{id}` | 分维度测评会话及结果 |
| 学习会话 | POST `/learning-sessions`；GET `/learning-sessions/{id}` | 创建及恢复本人会话 |
| 作答 | POST `/learning-sessions/{id}/attempts` | 接收任务 ID、内容版本、答案、耗时、幂等键；返回判定、反馈与状态摘要 |
| 提示 | POST `/learning-sessions/{id}/hints` | 按既有提示历史返回下一等级及原因 |
| 复习 | GET `/me/reviews` | 到期复习任务 |
| 进度 | GET `/me/progress` | 分维度进度、数据充分程度、建议 |
| 内容管理 | POST `/admin/content`；POST `/admin/content/{id}/review` | 创建候选版本与审核，需管理员权限 |

接口需处理未认证、无权限、未知资源、内容版本冲突、校验失败、限流与外部服务失败。服务端不得在返回未作答任务时泄露标准答案。语音评分、书写识别与商业化接口在专项方案验证后另行定义。
