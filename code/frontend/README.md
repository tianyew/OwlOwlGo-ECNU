# Frontend

OwlOwlGo 的 H5 客户端，规划使用 Vue 3、TypeScript、Vite 和 Pinia。

目录职责：

- `src/app/`：应用初始化、路由和全局状态；
- `src/features/`：按业务能力拆分的页面与交互；
- `src/shared/`：跨业务复用的组件、API 客户端、类型和工具；
- `src/styles/`：全局样式与设计变量；
- `tests/`：前端单元和组件测试。

当前以架构骨架为基础，已补充拼音与声调测评 Demo，其余业务能力按 features 下目录占位。

运行 npm ci、npm run dev 启动；npm run build 验证类型及生产构建。此阶段无需后端服务即可查看入口。

## 当前演示入口

已实现拼音与声调固定题目测评，运行 npm run dev 后访问 http://127.0.0.1:5173/。仅该模块提供交互；其他功能保留规划。题目内容与计分逻辑位于 src/features/phonetics，组件测试位于 tests/phonetics.test.ts。运行 npm test 检查交互流程。
