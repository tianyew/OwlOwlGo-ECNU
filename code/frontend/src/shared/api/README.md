# API client

`curriculum.ts` 通过后端 `/api/v1/learning/curriculum` 获取课程。
`learning.ts` 处理草稿进度、通用测验提交、前测重置、画像和 DeepSeek 分析。
`auth.ts` 提供账号与会话接口。`demo.ts` 仅保留兼容类型导出。

题目接口不返回正确答案与解析；正式提交后才返回本账号的成绩和反馈。
分数、完成状态和画像均使用后端结果。游客可浏览，登录后才能提交。
