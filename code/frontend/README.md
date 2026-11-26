# Frontend

Vue 3 + TypeScript 客户端，支持账号、前测、四个方向的二十个单元、后测与真实证据画像。

运行 `npm ci`、`npm run dev`；`npm run build` 检查类型并构建，`npm test` 验证交互。
Vite 将 `/api` 转发到 `127.0.0.1:8000`，课程与取题均需启动后端。
游客可浏览题目和课程，登录后提交测验并保存记录。

`src/shared/api/curriculum.ts` 读取后端课程目录，`learning.ts` 处理进度、测验提交与画像，
`auth.ts` 处理身份接口。前端不维护正确答案或正式计分函数。
通用测验组件位于 `features/assessment/ServerUnitQuiz.vue`，支持作答分页、草稿恢复、提交和结果展示。
前测、单元和后测共用该组件；画像展示后端返回的证据矩阵。

`LearningJourney.vue` 负责页面组合与导航，`useLearningProgress.ts` 负责加载、保存队列、
版本冲突和分析请求。学习状态按账号实例隔离，由根组件在账号变化时重新挂载。
实际模块和后续边界见[当前代码架构](../../docs/software/code-architecture.md)。

运行与验收见[完整学习链路](../../docs/software/server-unit-demo.md)，
DeepSeek 前测建议配置见[学习分析说明](../../docs/software/learning-agent.md)。
