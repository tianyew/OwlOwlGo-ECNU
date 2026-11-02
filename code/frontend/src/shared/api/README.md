# API client

`demo.ts` 提供本地异步 mock 接口：`getQuestions`、`submitAnswers`、`getTopics`、`getPlan`。本轮通过固定数据支持完整交互，后续在该层替换为 HTTP 请求并对齐后端契约。

演示题目包含答案和解析，仅用于本地原型；正式测评需要服务端计分和不含答案的题目接口。认证、错误映射等 HTTP 能力尚待实现。
