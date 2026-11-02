# Frontend

Vue 3 + TypeScript 客户端，已实现账号注册、登录、退出、游客入口，以及前测 → 诊断 → 方向选择 → 预设学习规划。

运行 `npm ci`、`npm run dev`，打开终端显示的本地地址；`npm run build` 验证类型和构建，`npm test` 检查组件交互。

账号接口由 Vite 将 `/api` 代理到 `127.0.0.1:8000`，需启动后端；游客学习流程可独立运行。学习 mock 和真实账号 API 分别位于 `src/shared/api/demo.ts` 与 `auth.ts`。

页面按 `src/features` 划分；账号组件位于 `auth`，流程编排位于 `assessment`，拼音测评位于 `phonetics`。登录后的学习状态、账号与会话通过后端 JSON 保存，游客仅保留本次页面。DeepSeek 分析配置见 [接入说明](../../docs/software/learning-agent.md)。详见 [账号说明](../../docs/software/accounts.md) 与 [演示说明](../../docs/software/demo-guide.md)。
