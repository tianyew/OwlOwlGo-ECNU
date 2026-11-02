# 开发与配置指南

安装与启动见[根目录 README](../README.md#快速开始)。当前前端为可独立运行的汉语项目静态入口，后端处于骨架阶段。

## Docker Compose

先在仓库根目录复制配置模板（macOS / Linux 使用 `cp .env.example .env`，Windows PowerShell 使用 `Copy-Item .env.example .env`），按本机环境修改后执行：

```bash
docker compose -f infrastructure/compose.yaml up --build
```

网关计划访问地址为 `http://localhost:8080`。容器配置属于工程骨架，首次正式部署前仍需完成依赖锁定、健康检查和生产配置评审。

## 配置说明

主要环境变量定义在 [.env.example](../.env.example)：

| 变量 | 用途 | 示例 |
| --- | --- | --- |
| `APP_ENV` | 当前运行环境 | `development` |
| `APP_DEBUG` | 是否开启调试模式 | `true` |
| `SECRET_KEY` | 会话或令牌签名密钥 | 本地随机字符串 |
| `DATABASE_URL` | PostgreSQL 连接地址 | `postgresql+psycopg://...` |
| `REDIS_URL` | 可选缓存服务地址 | `redis://localhost:6379/0` |
| `VITE_API_BASE_URL` | 前端请求的 API 地址 | `http://localhost:8000/api/v1` |
| `LLM_PROVIDER` | AI 服务供应商标识 | 后续确定 |
| `LLM_API_KEY` | AI 服务密钥 | 仅保存在本地环境 |
| `LLM_MODEL` | 使用的模型名称 | 后续确定 |

不得把真实 API Key、Token、密码、真实学习数据或个人配置提交到 Git。

当前后端配置模块和前端 API 客户端均为占位文件，尚未接入这些环境变量；本地后端启动不会自动读取根目录 `.env`。Docker Compose 使用 `env_file` 将配置注入后端容器。接入配置模块时需同步更新本文。

## 开发与测试

### 前端命令

```bash
cd code/frontend
npm run dev       # 启动开发服务器
npm run build     # 类型检查并构建
npm run lint      # 代码检查
npm run test      # 执行测试
```

### 后端命令

```bash
cd code/backend
python -m uvicorn app.main:app --reload
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

### 计划测试范围

- 单元测试：掌握度更新、任务评分、干预规则和游戏化规则；
- 集成测试：认证、API、数据库事务和 LLM 降级；
- 契约测试：前端类型与 OpenAPI 响应一致性；
- 端到端测试：测评、关卡、失败、提示、迁移题和报告；
- AI 评测：答案正确性、格式、难度、提示泄露和内容安全。

前端使用 package-lock.json 锁定依赖，CI 执行 npm ci 和 npm run build；后端检查 Python 语法。业务测试在具体功能实现时补充，当前不配置无测试文件的业务测试门禁。

测试目录目前只有说明文件，尚无可执行用例；ESLint 配置也尚未建立。以上命令列出开发阶段的工具入口，不能视为现有完整测试门禁。协作流程见[贡献指南](../CONTRIBUTING.md)，跨系统测试职责见[测试说明](../tests/README.md)。
