# 源码

- [backend/](backend/README.md)：FastAPI 服务、业务编排、数据库与外部服务适配。
- [frontend/](frontend/README.md)：Vue H5 客户端、页面、状态与交互。

核心学习规则规划放在 `backend/app/domain/`，保持无 Web 框架与数据库依赖；I/O 和应用用例由后端其他层负责。当前没有独立的公共引擎包。

模块测试就近放在 `backend/tests/` 和 `frontend/tests/`；跨系统测试位于根目录 [tests/](../tests/README.md)。从仓库根目录执行的启动与安装命令见 [README](../README.md#快速开始)。
