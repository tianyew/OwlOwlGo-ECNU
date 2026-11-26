# OwlOwlGo

[![CI](https://github.com/tianyew/OwlOwlGo-ECNU/actions/workflows/ci.yml/badge.svg)](https://github.com/tianyew/OwlOwlGo-ECNU/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

OwlOwlGo 是面向成年汉语学习者的 AI 游戏化汉语学习 H5 应用，目标是根据作答表现调整任务难度，并在合适时机提供渐进提示与讲解。项目采用 Vue 3 + TypeScript 前端和 Python + FastAPI 后端。

**当前状态：已实现服务端判分的学习原型。** 支持账号与会话、8 题拼音声调前测、4 个方向共 20 个单元、每个方向 10 题后测，以及基于真实作答的七维 × 六层证据画像。题库与课程由后端统一提供，登录用户的草稿、判分、完成记录和分析保存在 JSON 文件中。DeepSeek 可选用于前测建议，配置见[学习分析说明](docs/software/learning-agent.md)。操作与验收见[完整学习链路](docs/software/server-unit-demo.md)。账号、会话和限流已接入 PostgreSQL；RAG、LangGraph 和动态课程生成仍待实现。

## 快速开始

### 环境要求

- Node.js 22+、npm 10+；
- Python 3.12+。

账号注册和登录使用 FastAPI + PostgreSQL 17，不依赖 LLM 服务。先按[账号体系](docs/software/accounts.md)启动 Docker 数据库并配置后端 `DATABASE_URL`；旧 JSON 账号可保留 ID 导入。课程与题目浏览也需要启动后端，游客可预览，登录后可提交测验。学习记录暂时仍保存在 JSON 文件中。

### 1. 获取代码

```bash
git clone https://github.com/tianyew/OwlOwlGo-ECNU.git
cd OwlOwlGo-ECNU
```

### 2. 启动后端

在仓库根目录打开终端：

```bash
cd code/backend
python -m venv .venv
```

激活虚拟环境（按操作系统选择）：

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

先按[账号说明](docs/software/accounts.md#本地启动docker-数据库--本机后端)准备 PostgreSQL 和 `.env`，然后安装依赖、建表并启动：

```bash
python -m pip install -e ".[dev]"
python -m app.db.manage init
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. 启动前端

在仓库根目录另开一个终端：

```bash
cd code/frontend
npm install
npm run dev
```

Windows PowerShell 若无法执行 `npm.ps1`，使用 `npm.cmd install` 和 `npm.cmd run dev`。

## 使用与调用示例

- 前端入口：<http://localhost:5173>，前测、诊断、兴趣方向与预设学习规划 Demo；
- API 文档：<http://localhost:8000/docs>，包含注册、登录、当前用户与退出接口。

后端启动后，可读取已有的 OpenAPI 描述：

```bash
curl http://localhost:8000/openapi.json
```

Windows PowerShell 可使用 `Invoke-RestMethod http://localhost:8000/openapi.json`。当前响应包含账号、课程、全部测验的取题和提交、学习进度、画像与前测分析接口。

前测、全部单元和后测已接入后端判分与进度保存，运行和验收步骤见[完整学习链路](docs/software/server-unit-demo.md)。

## 仓库结构

```text
OwlOwlGo-ECNU/
├─ docs/                     # 正式文档与课程交付物
│  ├─ requirements/          # 问题定义、功能与非功能需求
│  ├─ algorithm/             # 算法说明、技术调研与选型依据
│  ├─ software/              # 软件架构设计
│  ├─ mgmt/                  # 项目计划、沟通与风险管理
│  ├─ retrospection/         # 迭代复盘与经验总结
│  ├─ adr/                   # 架构决策记录
│  └─ development.md         # 配置、部署与开发命令
├─ code/                     # 源码与各模块依赖
│  ├─ backend/               # API、业务编排、数据访问与后端测试
│  │  └─ app/domain/         # 学习者、任务、干预和游戏化领域规则
│  └─ frontend/              # H5 客户端与前端测试
├─ tests/                    # 跨系统测试、API 契约与 AI 评测
├─ figures/                  # 图表及可编辑源文件
├─ infrastructure/           # Docker、Nginx 与部署配置
├─ scripts/                  # 开发辅助脚本
├─ .github/                  # CI、Issue 与 PR 模板
├─ .env.example              # 环境变量模板
├─ CONTRIBUTING.md           # 协作规范
├─ LICENSE                   # MIT 许可证
└─ README.md                 # 项目入口
```

源码按前后端独立维护；模块测试分别放在 `code/backend/tests/` 和 `code/frontend/tests/`，跨系统测试放在根目录 `tests/`。核心策略规划放在 `code/backend/app/domain/`，各层职责见[后端说明](code/backend/README.md)和[前端说明](code/frontend/README.md)。

## 文档与协作

| 入口 | 内容 |
| --- | --- |
| [文档索引](docs/README.md) | 正式文档与课程成果导航 |
| [工程问题定义](docs/requirements/problem_definition.md) | 背景、目标用户与 MVP 边界 |
| [功能规格](docs/requirements/functional_spec.md) / [非功能需求](docs/requirements/nonfunctional_spec.md) | 详细需求与验收标准 |
| [系统架构](docs/software/architecture.md) | 技术栈、模块关系与设计约束 |
| [当前代码架构](docs/software/code-architecture.md) | 已实现模块、调用关系、结构评估与维护边界 |
| [开发与配置指南](docs/development.md) | 环境配置、容器启动与开发检查 |
| [项目计划](docs/mgmt/project-plan.md) | 17 周安排、完成度与风险 |
| [贡献指南](CONTRIBUTING.md) | 分支、提交、Issue 与 PR 流程 |

本项目为[智能软件工程实践课程](https://github.com/bettermorn/IntelligentSWEPractice)作品。正式需求与设计随代码保存在 `docs/`；会议纪要、FAQ 和讨论资料使用 GitHub Wiki；任务与缺陷使用 Issues/Projects 管理。

## License

[MIT License](LICENSE)

## 汉语产品与架构设计

- [产品定义与目标用户](docs/requirements/problem_definition.md)
- [页面设计与功能优先级](docs/software/product-design.md)
- [系统架构与模块职责](docs/software/architecture.md)
- [数据模型草案](docs/software/data-model.md)
- [API 边界草案](docs/software/api-contract.md)
