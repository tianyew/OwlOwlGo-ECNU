# 项目文档与课程成果

[返回项目首页](../README.md)

本目录保存随代码版本维护的正式文档。详细功能、设计和项目管理信息通过下列入口查看。

| 分类 | 文档 | 内容 |
| --- | --- | --- |
| 需求分析 | [工程问题定义](requirements/problem_definition.md) | 5W1H、目标用户、痛点与产品边界 |
| 需求分析 | [功能规格](requirements/functional_spec.md) | 角色、功能树、业务规则、领域模型与验收标准 |
| 需求分析 | [非功能需求](requirements/nonfunctional_spec.md) | 性能、可靠性、安全、隐私与 AI 质量 |
| 算法设计 | [算法文档说明](algorithm/README.md) | 调研、策略与参数文档的维护要求 |
| 软件设计 | [系统架构与技术方案调研报告](software/architecture.md) | 架构与模块职责、核心技术选型、两周自学计划与 Milestone |
| 软件设计 | [页面与功能设计](software/product-design.md) | 页面结构、用户旅程、功能优先级 |
| 软件设计 | [数据模型](software/data-model.md) | 汉语内容、学习事件与复习关系 |
| 软件设计 | [API 边界](software/api-contract.md) | 版本化接口与调用约束 |
| 软件设计 | [架构决策记录](adr/README.md) | 决策的背景、选择与影响 |
| 开发与部署 | [开发与配置指南](development.md) | 环境变量、Docker Compose 与检查命令 |
| 项目管理 | [项目计划](mgmt/project-plan.md) | 17 周安排、工作项、里程碑与风险 |
| 项目管理 | [管理文档说明](mgmt/README.md) | 计划、沟通和风险文档的维护边界 |
| 迭代复盘 | [复盘文档说明](retrospection/README.md) | 迭代结果、问题与改进的记录要求 |

## 仓库职责与课程结构对应

参考课程的[成果目录建议](https://github.com/bettermorn/IntelligentSWEPractice#课程成果)，本仓库按文档、源码和测试职责组织：

| 职责 | 本仓库位置 | 维护约定 |
| --- | --- | --- |
| 需求文档 | `docs/requirements/` | 修改需求时同步更新规格与验收标准 |
| 算法文档 | `docs/algorithm/` | 保存调研、方案比较、策略说明和参数依据 |
| 软件设计 | `docs/software/`、`docs/adr/` | 架构说明与重要决策分别维护 |
| 项目管理 | `docs/mgmt/`、Issues/Projects | 计划记录里程碑，任务状态在协作平台维护 |
| 迭代复盘 | `docs/retrospection/` | 每次迭代追加结果与可跟踪的改进项 |
| 前后端源码 | `code/frontend/`、`code/backend/` | 各自维护依赖、启动命令与模块说明 |
| 核心规则 | `code/backend/app/domain/` | 规划中的纯领域逻辑不依赖 Web 框架 |
| 模块测试 | `code/backend/tests/`、`code/frontend/tests/` | 就近维护各模块的单元与集成测试 |
| 跨系统测试 | `tests/` | 端到端、API 契约、AI 评测与合成数据 |
| 图表 | `figures/` | 同时保留图表与可编辑源文件 |
| 部署与脚本 | `infrastructure/`、`scripts/` | 配置与辅助工具各自维护 |

算法调研、原型和复盘的具体成果随课程阶段补充，新增时同步登记本索引。当前测试与业务目录主要为骨架，目录存在不代表相关功能已经完成。

课程示例中的 `core_engine/` 职责目前由 `code/backend/app/domain/` 承担；纯领域逻辑集中在这里，数据库访问和 Web 编排放在后端其他层。后续出现独立复用需求时再拆分核心引擎。

会议纪要、FAQ、学习资料和过程讨论使用 GitHub Wiki。文档协作规则见[贡献指南](../CONTRIBUTING.md)。

