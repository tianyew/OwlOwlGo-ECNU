# 原型账号体系与 JSON 存储

状态：已实现注册、登录、当前账号查询、退出和刷新后的登录恢复。数据库尚未定案；本实现不代表团队已决定使用 MongoDB，也不替换原架构报告中的待评审方案。

## 启动与使用

在 `code/backend` 安装 `python -m pip install -e ".[dev]"`，运行 `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`。前端在 `code/frontend` 执行 `npm run dev`，通过前端地址访问。Vite 将 `/api` 转发到 `127.0.0.1:8000`，保持浏览器同源 Cookie。

首页可注册或登录，也可选择游客体验。默认演示账号为 `admin / admin`，无额外管理权限；后端启动时仅在账号不存在时创建，重启不会覆盖已有账号。设置 `OWL_SEED_DEMO_ACCOUNT=false` 可关闭自动创建（不会删除已经创建的账号）。账号为 3–32 位英文字母、数字或下划线，不区分大小写；密码 8–128 位；昵称 1–40 位。注册成功自动登录。退出后服务端会话失效。密码重置、邮箱验证和第三方登录尚未实现。

账号、会话及登录后的学习进度均持久保存。前测答案、主题与单元完成记录保存在同目录 `learning.json`；刷新或重新登录可恢复。详见 [学习进度与 DeepSeek 分析](learning-agent.md)。游客记录仍不持久保存。

Docker Compose 的账号文件保存在 `account_data` 命名卷中；容器重建仍保留账号。PostgreSQL 服务改为可选 `database` profile，尚未用于账号；不要用 `docker compose down -v` 清理需要保留的数据。反向代理转发含端口的 Host，以支持同源校验。容器部署配置本轮未做 Docker 实机验证。

## 数据位置与格式

默认文件：`code/backend/local-data/accounts.json`。首次写入时创建，已由 `.gitignore` 中 `local-data/` 规则排除。文件不放在前端资源目录。可用 `OWL_ACCOUNT_FILE` 环境变量指定另一绝对路径。配置通过进程环境读取，当前不自动读取 `.env` 文件。

顶层结构为 `schema_version: 1`、`users` 数组和 `sessions` 数组。每个元素是一份独立文档：

| 集合 | 字段 | 约定 |
| --- | --- | --- |
| users | `_id`, `username`, `display_name`, `password_hash`, `created_at`, `schema_version` | `_id` 为 UUID 字符串；username 标准化为小写；时间为 UTC ISO 字符串 |
| sessions | `_id`, `user_id`, `created_at`, `expires_at` | `_id` 为会话令牌 SHA-256 摘要；user_id 引用用户；时间为 Unix 秒 |

文件保存 scrypt 加盐密码哈希，不保存明文密码。接口只返回 `id`、`username`、`display_name`。原始随机会话令牌仅放在 HttpOnly、SameSite=Strict Cookie，7 天过期；重新登录会替换该浏览器旧会话，退出会删除服务端会话。过期会话在认证时立即拒绝，并在新建会话时清理。

JSON 仓储使用文件锁串行化读写，临时文件写入后原子替换，重复账号检查与创建在同一锁中完成。损坏文件会报错，不会自动覆盖为空数据。适合本机、小规模课程演示；每次操作读取整个文件，不适合多主机部署或大量账号。迁移或备份应停止服务后复制文件，避免不完整的手工编辑。

## API

| 方法 | 路径 | 输入 | 结果 |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | username、password、display_name | 201 用户信息 + 登录 Cookie；重复账号 409 |
| POST | `/api/v1/auth/login` | username、password | 200 用户信息 + 登录 Cookie；错误凭据 401 |
| GET | `/api/v1/auth/me` | Cookie | 200 当前用户；无效或过期会话 401 |
| POST | `/api/v1/auth/logout` | Cookie | 204，删除会话并清除 Cookie |

参数不合法返回 422；校验错误不回显密码。带 Origin 的变更请求必须同源；前后端通过开发代理或反向代理同源提供。不对外开放 CORS。所有账号响应使用 `Cache-Control: no-store`。

## 将来迁移 MongoDB

MongoDB 使用 BSON，文档结构接近 JSON，但 JSON 文件本身不提供数据库查询、索引与事务能力。[MongoDB 文档模型](https://www.mongodb.com/docs/manual/core/document/)

迁移工作可分为：

1. 实现 `AccountRepository` 协议的 MongoDB 适配器，在应用工厂替换 `JsonAccountRepository`，保持 API 与页面不变。
2. 将 `users` 中每个元素导入一条用户文档，保留字符串 `_id`、密码哈希和用户引用，不强制改为 ObjectId。
3. 对 `username` 建唯一索引，并将重复键错误映射到现有 409；导入前检查重复值。[唯一索引说明](https://www.mongodb.com/docs/manual/core/index-unique/)
4. 会话可以全部失效，让用户重新登录；若迁移会话，保留摘要和有效期。若采用 MongoDB TTL 索引，将有效期转成 BSON Date；应用仍需自行检查过期，不能仅依赖后台删除。
5. 保留并跑通仓储契约、并发注册、登录恢复、失效和退出测试，验证备份与回滚后再切换。

采用 JSON 文档能减少字段转换，但真正减少迁移成本的是仓储接口、稳定用户 ID 和清晰的数据约定。数据库选择仍应由团队结合部署与学习记录查询需求确认。

## 验收与边界

后端测试使用临时目录，不读写真实账号文件：`cd code/backend && .venv/bin/python -m pytest`。前端运行 `npm test`、`npm run build`。

本轮验收覆盖注册、重复账号、错误密码、会话恢复和轮换、退出、过期、跨来源请求拒绝、并发创建与损坏文件保护。前端覆盖注册确认、错误反馈、登录恢复和游客入口。

当前面向本机原型。公开部署前需补齐登录限流、密码找回及部署验收，使用 HTTPS 并设置 `OWL_SECURE_COOKIES=true`；本机 HTTP 开发保持 false。账号数据与哈希均不应提交仓库或随演示截图公开。
