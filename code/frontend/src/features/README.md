# Feature modules

当前可执行模块包括 `auth`（账号）、`home`（首页）、`assessment`（学习旅程、测验与画像）、`phonetics`（前测入口）和 `companion`（伴学界面）。
`profile`、`characters`、`scenarios`、`culture`、`review`、`progress` 仍是预留目录；画像目前实现在 `assessment` 内。

业务状态优先放在 feature 的 composable 中；组件通过 props 和事件连接，HTTP 调用集中于 `shared/api`。
当前代码架构见仓库 `docs/software/code-architecture.md`，长期设计见 `docs/software/architecture.md`。
