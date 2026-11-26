# 账号体系与 PostgreSQL

账号、会话和认证限流支持 PostgreSQL 17，通过 SQLAlchemy + psycopg 接入。前端接口不变：注册、登录、当前用户、退出仍使用 `/api/v1/auth/*`。配置了 `DATABASE_URL` 后，所有账号读写都进入数据库；连接失败不会回退到 JSON。

学习草稿、测验记录和分析暂时保存在 `learning.json`。账号迁移保留 UUID，因此原有学习记录仍能关联。

## 本地启动：Docker 数据库 + 本机后端

先启动 Docker Desktop。仓库根目录的 `.env` 保存 Docker 参数，`code/backend/.env` 保存本机后端参数。新环境可从各自 `.env.example` 创建；已有文件只追加或修改以下字段，保留已有模型密钥。

根目录 `.env`：

```dotenv
POSTGRES_PASSWORD=replace_with_a_random_password
POSTGRES_PORT=5432
```

后端 `code/backend/.env`：

```dotenv
DATABASE_URL=postgresql+psycopg://owlowlgo:replace_with_a_random_password@127.0.0.1:5432/owlowlgo
OWL_SEED_DEMO_ACCOUNT=false
OWL_SECURE_COOKIES=false
```

两处密码必须一致。本地开发建议使用随机十六进制密码；若密码含 `@`、`:`、`/` 等字符，需要在 URL 中百分号编码。修改宿主机端口时也需同步修改后端 URL。默认用户名和数据库名均为 `owlowlgo`。

在仓库根目录启动数据库：

```bash
docker compose --env-file .env -f infrastructure/compose.yaml up -d database
```

数据库端口只绑定 `127.0.0.1`，数据保存在 `infrastructure_postgres_data` 命名卷。`POSTGRES_PASSWORD` 只在空数据卷初始化时设置数据库密码；已有卷的密码不会随 `.env` 自动更改。

在后端目录安装依赖、建表、启动服务：

```bash
cd code/backend
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m app.db.manage init
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`init` 是事务性的版本 1 建表迁移，允许重复执行，不删除已有记录。后端启动会检查 schema 版本；缺表或数据库不可达时启动失败，避免出现“看似登录成功但实际写入其他存储”的情况。未来字段变更需要新增版本迁移，不能仅修改模型后重复 `init`。

另开终端，在 `code/frontend` 执行 `npm run dev`，通过前端地址访问。Vite 将 `/api` 转发到后端，保持同源 Cookie。首次使用可直接注册自己的账号。

## 已有 JSON 账号迁移

迁移前停止正在运行的后端，备份 `local-data/accounts.json` 和 `local-data/learning.json`。在 `code/backend` 执行：

```bash
python -m app.db.manage import-json local-data/accounts.json --dry-run
python -m app.db.manage import-json local-data/accounts.json
```

导入行为：

- 保留用户 UUID、标准化账号、昵称、scrypt 密码哈希和创建时间，不要求用户改密码。
- 预演实际执行校验和写入，再回滚；正式导入使用一个数据库事务。
- 完全相同的已有记录跳过，可重复执行；ID、账号名或字段冲突时整批回滚，不覆盖。
- 原 JSON 文件保持不变。旧会话和旧限流计数不导入，迁移后需要重新登录。
- 学习记录继续读取原文件。若更改过数据位置，通过 `OWL_LEARNING_FILE` 指向原来的 `learning.json`。

已有演示账号也会原样导入。`OWL_SEED_DEMO_ACCOUNT=false` 只阻止自动创建，不删除既存账号。

## 表与字段

| 表 | 字段 | 约束与用途 |
| --- | --- | --- |
| `auth_users` | `id` UUID、`username`、`display_name`、`password_hash`、`created_at` | UUID 主键；账号唯一且必须小写；创建时间含时区 |
| `auth_sessions` | `token_hash`、`user_id`、`created_at`、`expires_at` | 只保存令牌 SHA-256 摘要；用户外键；删除用户时级联删除会话；时间为 Unix 秒 |
| `auth_attempts` | `key`、`count`、`expires_at` | 来源地址或账号名的摘要作为主键；固定窗口计数；事务行锁避免并发超额 |
| `auth_schema_versions` | `version` | 记录已应用的结构版本，当前为 1 |

密码不存明文。接口只返回 `id`、`username`、`display_name`。Cookie 使用 HttpOnly、SameSite=Strict；HTTPS 环境应设置 `OWL_SECURE_COOKIES=true`。重新登录在同一事务中替换旧会话；退出删除会话。过期会话立即拒绝，新建会话时清理过期记录。

查看数据库（在仓库根目录执行）：

```bash
docker compose --env-file .env -f infrastructure/compose.yaml exec database psql -U owlowlgo -d owlowlgo
```

```sql
\dt
SELECT id, username, display_name, created_at FROM auth_users;
SELECT count(*) FROM auth_sessions;
```

不需要查询或展示密码哈希。定期清理过期会话和限流计数，在后端目录执行：

```bash
python -m app.db.manage cleanup
```

## 配置

后端统一读取 `code/backend/.env`，进程环境变量优先；修改后重启。根目录 `.env` 不会被本机后端自动读取。

| 配置 | 默认值 | 用途 |
| --- | --- | --- |
| `DATABASE_URL` | 空 | PostgreSQL URL；空值显式使用旧 JSON 模式 |
| `OWL_ACCOUNT_FILE` | `local-data/accounts.json` | 仅旧 JSON 模式的账号文件，也决定学习文件默认目录 |
| `OWL_LEARNING_FILE` | 账号文件同目录的 `learning.json` | 学习数据文件，可独立配置 |
| `OWL_SECURE_COOKIES` | `false` | HTTPS 时设置 `true`，本地 HTTP 保持 `false` |
| `OWL_SEED_DEMO_ACCOUNT` | `false` | 仅本地演示需要时显式开启 `admin/admin` 创建 |
| `OWL_SESSION_SECONDS` | `604800` | 新会话有效期，范围 60 秒至 30 天 |
| `OWL_AUTH_WINDOW_SECONDS` | `300` | 认证限流窗口秒数 |
| `OWL_LOGIN_ACCOUNT_LIMIT` | `10` | 每账号每窗口登录尝试数 |
| `OWL_LOGIN_IP_LIMIT` | `60` | 每来源地址每窗口登录尝试数 |
| `OWL_REGISTER_IP_LIMIT` | `20` | 每来源地址每窗口注册尝试数 |

成功尝试也计入限流。超限返回 429 和 `Retry-After` 秒数，不继续计算密码哈希、不延长窗口，也不影响已有会话查询和退出。数据库计数由所有后端进程共享，重启不会清空。

## API 与前端行为

| 方法 | 路径 | 输入 | 结果 |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | username、password、display_name | 201 用户信息 + Cookie；重复账号 409 |
| POST | `/api/v1/auth/login` | username、password | 200 用户信息 + Cookie；错误凭据 401 |
| GET | `/api/v1/auth/me` | Cookie | 当前用户；无效或过期会话 401 |
| POST | `/api/v1/auth/logout` | Cookie | 204，删除会话并清除 Cookie |

账号为 3–32 位英文字母、数字或下划线，不区分大小写；注册密码 8–128 位；昵称 1–40 位。参数错误返回 422，不回显密码；运行期间数据库故障返回不包含内部详情的 503。

变更请求的 Origin 必须协议、主机、端口均同源；`Sec-Fetch-Site: cross-site` 被拒绝。账号响应使用 `Cache-Control: no-store`。前端账号请求 10 秒超时，可重新检查状态。学习接口返回 401 时返回登录表单；已保存记录在重新登录后恢复，未保存操作需要重新完成。

## 全容器启动与边界

```bash
docker compose --env-file .env -f infrastructure/compose.yaml up -d --build
```

Compose 等待数据库健康，再由 `database-init` 应用建表迁移，然后启动 API。容器内连接主机为 `database`，由 Compose 覆盖 `DATABASE_URL`。数据库使用 `postgres_data` 卷；学习文件使用 `account_data` 卷。已有本机学习文件不会自动复制进容器卷，切换全容器运行前需要单独迁移学习文件。网关地址为 `http://localhost:8080`。

不要使用 `down -v` 删除需要保留的数据。清空 `DATABASE_URL` 会回到旧 JSON 数据快照，不会同步 PostgreSQL 中后续新增的账号，不能当作无损回滚。

本地 Docker 数据库已进行实际集成测试；全容器应用和公网 HTTPS 部署需另行验收。HTTPS 反向代理要转发 Host、真实协议，并将 Uvicorn `FORWARDED_ALLOW_IPS` 限定为可信代理，才能正确执行来源检查和按真实客户端地址限流。

密码找回、邮箱验证和第三方登录尚未实现。学习记录仍是本地文件，因此整个系统还不能直接按多主机数据库应用部署。

## 测试

```bash
cd code/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q --postgres
```

默认跳过真实数据库测试。`--postgres` 使用后端配置的数据库，也可用 `OWL_TEST_DATABASE_URL` 指定测试库。数据库测试创建随机独立 schema，验证注册、会话、并发限流、重复账号、导入预演和回滚，结束后只清理该测试 schema。测试角色需要 CREATE SCHEMA 权限。CI 使用独立 PostgreSQL 服务运行这些测试。

实现参考 [SQLAlchemy PostgreSQL 文档](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) 和 [PostgreSQL 锁机制](https://www.postgresql.org/docs/17/explicit-locking.html)。
