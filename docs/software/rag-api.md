# RAG 接口与调用方法

面向伴学、学习规划、出题和前端模块的开发同学。配置好的 RAG 服务提供文档入库和教学资料检索。业务模块可以提交正文自动完成切片、向量化与存储，再查询相关片段用于讲解、参考材料或引用。

远程调用需要服务地址和本站账号，入库还需维护者授予写入权限；调用方不需要数据库密码或 Embedding 密钥。部署和 CLI 维护见 [RAG 基础模块指南](rag.md)。

| 方法 | 路径 | 用途 | 权限 |
| --- | --- | --- | --- |
| POST | `/api/v1/knowledge/documents` | 文档入库及版本更新，自动切片和向量化 | 登录且用户 ID 在入库名单中 |
| POST | `/api/v1/knowledge/search` | 查询相关片段及来源 | 登录用户 |

## 接入准备

向服务维护者取得可访问的服务基地址和账号。示例地址如下，按实际部署替换：

| 调用环境 | 基地址示例 |
| --- | --- |
| 本机直接运行 FastAPI | `http://127.0.0.1:8000` |
| 本机 Docker 网关 | `http://127.0.0.1:8080` |
| 同学部署的共享服务 | `http://服务器地址:实际端口` |
| 本项目 Vue 前端 | 使用相对路径 `/api/v1/...`，由 Vite 或网关代理 |

`127.0.0.1` 表示调用者自己的电脑；访问其他同学的服务时必须换成对方的地址。登录和检索应使用同一个基地址，避免混用 `localhost` 与 `127.0.0.1` 导致 Cookie 无法复用。

维护者需确认后端已设置 `RAG_ENABLED=true` 并重启，数据库已初始化，当前 Embedding 配置下已有可检索资料。CLI 检索成功不代表 HTTP 服务已经启用。

接口描述可通过同一 FastAPI 服务的 `/docs` 和 `/openapi.json` 查看；当前 Docker 网关只代理 `/api/`，访问文档时需使用可达的 FastAPI 地址。

## 登录鉴权

入库和检索请求都需要登录 Cookie `owl_session`，目前使用账号会话鉴权。Embedding API Key 是后端配置，不用于调用此接口；当前没有供调用方使用的独立 RAG API Key 或 Bearer Token。

### 登录

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

替换成已有本站账号。成功返回 `200` 和用户信息，并通过 `Set-Cookie` 设置会话：

```json
{
  "id": "用户 UUID",
  "username": "your_username",
  "display_name": "用户昵称"
}
```

后续请求由 HTTP 客户端自动携带 Cookie。可用 `GET /api/v1/auth/me` 确认登录状态；`POST /api/v1/auth/logout` 退出，成功返回 `204`。首次创建账号请通过本站注册流程完成。

浏览器请求必须与目标服务同源，即协议、主机和端口一致。前端使用项目已有代理和相对路径；仅设置 `credentials: "include"` 不能放开跨源限制。Python 和命令行客户端正常使用 Cookie 即可，无需自行设置 `Origin`。

## 文档入库接口

```http
POST /api/v1/knowledge/documents
Content-Type: application/json
Cookie: owl_session=登录后由客户端保存的值
```

### 开通入库权限

维护者在 `code/backend/.env` 中配置允许写入的现有用户 UUID，保存后重启后端：

```dotenv
RAG_ENABLED=true
RAG_INGEST_USER_IDS=["00000000-0000-0000-0000-000000000001"]
```

将示例 UUID 替换为调用者登录后 `GET /api/v1/auth/me` 返回的 `id`；多个 ID 以 JSON 数组填写。默认值 `[]` 表示没有账号能通过 HTTP 入库。用户名叫 `admin` 也不会自动获得权限。该名单授予共享知识库的新增、替换与审核状态设置权限，只配置负责资料维护的账号。CLI 和 Python 内部服务继续由受信任的维护者执行，不使用这份 HTTP 权限名单。

### 入库请求

请求体与 CLI 使用的 `KnowledgeDocument` JSON 格式一致。下面以本地联调用的示例为例；正式资料经教学审核后才能填写 `approved/public`：

```json
{
  "document_id": "tone-sandhi-http-demo",
  "title": "第三声变调接口示例",
  "text": "两个第三声音节相连时，前一个通常读作第二声。例如“你好”连读接近 ní hǎo。",
  "source": "团队自编联调资料",
  "license": "项目内部测试使用",
  "content_version": 1,
  "review_status": "approved",
  "visibility": "public",
  "answer_visibility": "teaching",
  "language": "zh",
  "direction_ids": ["daily"],
  "knowledge_point_ids": ["tone_sandhi_3"],
  "difficulty": 1
}
```

| 字段 | 类型 | 必填 | 默认值 | 约束及含义 |
| --- | --- | --- | --- | --- |
| `document_id` | string | 是 | 无 | 1–120 字符，仅字母、数字、下划线、点、连字符；文档的稳定 ID |
| `title` | string | 是 | 无 | 1–200 字符 |
| `text` | string | 是 | 无 | 1–200000 字符，纯文本或 Markdown 正文 |
| `source` | string | 是 | 无 | 1–1000 字符，来源描述或地址 |
| `license` | string | 是 | 无 | 1–200 字符，许可说明 |
| `content_version` | integer | 是 | 无 | 大于等于 1；更新正文或元数据时递增 |
| `review_status` | string | 否 | `draft` | `draft` 或 `approved` |
| `visibility` | string | 否 | `internal` | `internal` 或 `public` |
| `answer_visibility` | string | 否 | `teaching` | `teaching` 或 `answer` |
| `language` | string | 否 | `zh` | 1–20 字符，资料语言 |
| `direction_ids` | string[] | 否 | `[]` | 最多 20 项，方向标签 |
| `knowledge_point_ids` | string[] | 否 | `[]` | 最多 50 项，知识点标签 |
| `difficulty` | integer/null | 否 | `null` | 1–6，资料难度标签 |

字符串会去除首尾空白，未知字段会返回 422。提交 JSON 文件时直接将文件内容作为请求体；本接口不接收 multipart 文件、服务器文件路径或远程下载地址，也不解析 PDF/Word。纯文本或 Markdown 文件可由调用方读取后放入 `text`。

入库自动执行“校验 → 切片 → Embedding → 事务存储”。当前默认每片最多 1000 字符、相邻重叠约 100 字符，调用方不需要提交切片或向量。请求同步等待完成，返回成功后资料已写入；不是后台任务受理通知。

省略审核和可见性字段时，资料按 `draft/internal` 保存，入库成功也不会被公共检索召回。检索仍须同时满足 `approved + public + teaching`。

### 入库响应与更新规则

新增、更新、相同版本相同内容重复提交，成功均返回 `200`：

```json
{
  "document_id": "tone-sandhi-http-demo",
  "content_version": 1,
  "chunk_count": 1,
  "chunk_ids": ["tone-sandhi-http-demo:v1:0"],
  "embedding_key": "当前 Embedding 配置生成的标识"
}
```

`chunk_count` 是实际片段数，`chunk_ids` 按切片顺序排列；`embedding_key` 可与检索响应核对。响应不包含完整向量。

更新使用相同 `document_id` 和更大的 `content_version`，仍调用本接口。正文、来源、许可、审核状态或任何元数据变更都需递增版本；同版本不同内容、旧版本覆盖新版本均返回 409。同版本同内容可重复提交，Embedding 配置变更后也可据此重建向量；重复提交仍会调用 Embedding。更新会替换旧片段，仅保留当前版本。

Embedding 或数据库失败返回 503，已有版本保持完整。若客户端超时，服务端可能仍在执行；确认状态或以相同版本相同内容重试，避免直接修改内容后复用版本号。

### 入库调用示例

下面的 curl 复用已登录的 `RAG_BASE_URL` 和 `RAG_COOKIE_JAR`。在仓库根目录执行，且账号需已开通入库权限：

```bash
curl --fail-with-body -sS --max-time 300 -b "$RAG_COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  --data-binary @code/backend/examples/rag/tone-sandhi.json \
  "$RAG_BASE_URL/api/v1/knowledge/documents"
```

若示例已入库且正文或元数据有变化，请先递增文件中的 `content_version`。Python 同样复用已登录的 `httpx.Client`：

```python
import json
from pathlib import Path


def upload_document(client, json_path):
    document = json.loads(Path(json_path).read_text(encoding="utf-8"))
    response = client.post(
        "/api/v1/knowledge/documents", json=document, timeout=300.0,
    )
    response.raise_for_status()
    return response.json()
```

前端可复用下文的 `postJson`：

```javascript
async function ingestDocument(document) {
  return postJson('/api/v1/knowledge/documents', document);
}
```

长文档会产生多批 Embedding 请求，建议先用短文档联调。当前项目 Nginx 网关为此路径设置 2 MiB 请求体上限和 300 秒读取超时；额外部署代理也需配置相应限制。字符上限是正文长度，网络请求大小还包括 JSON 编码和元数据。生产长文档批量导入可继续使用 CLI。

## 检索接口

```http
POST /api/v1/knowledge/search
Content-Type: application/json
Cookie: owl_session=登录后由客户端保存的值
```

### 最小请求

```json
{
  "query": "两个第三声连在一起怎么读？"
}
```

### 完整请求

```json
{
  "query": "两个第三声连在一起怎么读？",
  "filters": {
    "knowledge_point_id": "tone_sandhi_3",
    "language": "zh"
  },
  "top_k": 4,
  "max_context_chars": 6000,
  "min_score": 0.0
}
```

### 请求字段

| 字段 | 类型 | 必填 | 默认值 | 约束及含义 |
| --- | --- | --- | --- | --- |
| `query` | string | 是 | 无 | 去除首尾空白后 1–2000 字符，用户问题 |
| `filters` | object | 否 | `{}` | 缩小检索范围，字段见下表 |
| `top_k` | integer | 否 | `4` | 1–10，最多返回多少个片段 |
| `max_context_chars` | integer | 否 | `6000` | 200–16000，返回片段正文的总字符预算；不是 token 数 |
| `min_score` | number | 否 | `0.0` | -1 到 1，最低余弦相似度 |

请求对象和过滤器均不接受未定义字段。返回数量可能小于 `top_k`：没有足够资料、分数不足或正文超出字符预算时都会减少结果。预算只计算 `text`，不包含标题、来源等字段；超预算的片段整片跳过，不截断，也不额外补召回。

### 过滤字段

以下字段均可省略或设为 `null`。指定多个字段时取 AND，ID 必须与资料入库时的元数据一致。

| 字段 | 类型 | 约束 | 示例及匹配方式 |
| --- | --- | --- | --- |
| `direction_id` | string | 1–100 字符 | `"daily"`，资料的 `direction_ids` 包含此值 |
| `knowledge_point_id` | string | 1–100 字符 | `"tone_sandhi_3"`，资料的 `knowledge_point_ids` 包含此值 |
| `language` | string | 1–20 字符 | `"zh"`，精确匹配资料语言 |
| `difficulty` | integer | 1–6 | 精确匹配资料的难度标签，不是用户能力评分 |
| `document_id` | string | 1–120 字符 | `"tone-sandhi-intro"`，仅检索指定文档 |

未命中时先尝试移除过滤器，确认不是 ID、语言或难度标签不匹配。

### 成功响应

以下为结构示例；分数和配置标识以实际响应为准。

```json
{
  "hits": [
    {
      "chunk_id": "tone-sandhi-intro:v1:0",
      "document_id": "tone-sandhi-intro",
      "title": "第三声变调示例",
      "text": "两个第三声音节相连时，前一个通常读作第二声。例如“你好”连读接近 ní hǎo。",
      "source": "OwlOwlGo 团队自编示例；正式使用前需教学审核",
      "license": "项目内部示例，仅供开发验证",
      "content_version": 1,
      "score": 0.77
    }
  ],
  "embedding_key": "当前 Embedding 配置生成的标识"
}
```

| 字段 | 含义 |
| --- | --- |
| `hits` | 按相似度从高到低排列的片段列表 |
| `hits[].chunk_id` | 片段引用标识，引用时与 `content_version` 一起保留 |
| `hits[].document_id` | 所属文档 ID |
| `hits[].title` | 文档标题 |
| `hits[].text` | 可供业务模块使用的参考正文 |
| `hits[].source` | 资料来源描述，不保证是 URL |
| `hits[].license` | 资料使用许可说明 |
| `hits[].content_version` | 当前文档版本 |
| `hits[].score` | 余弦相似度，越大越相近；不是答案正确率 |
| `embedding_key` | 服务地址、模型、维度和 revision 生成的配置标识，用于排查索引是否匹配 |

无命中正常返回 `200` 和 `{"hits": [], "embedding_key": "..."}`。调用方可提示暂无相关材料，或使用已有课程内容降级；空结果与服务故障应分别处理。

服务端始终只检索 `approved + public + teaching` 的资料，并限定为当前 Embedding 配置生成的向量。调用方不能通过请求参数读取草稿、内部资料或测验答案片段。

## curl 调用

以下命令适用于 macOS/Linux shell。先替换基地址、账号、密码，再按顺序执行；登录和检索共用 Cookie 文件。若要调用上文的入库示例，在登录后、退出登录前执行，退出后 Cookie 将失效。

```bash
RAG_BASE_URL='http://127.0.0.1:8000'
RAG_COOKIE_JAR="$(mktemp)"

curl --fail-with-body -sS -c "$RAG_COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d '{"username":"your_username","password":"your_password"}' \
  "$RAG_BASE_URL/api/v1/auth/login"

curl --fail-with-body -sS -b "$RAG_COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d '{"query":"两个第三声连在一起怎么读？","top_k":4}' \
  "$RAG_BASE_URL/api/v1/knowledge/search"

curl --fail-with-body -sS -b "$RAG_COOKIE_JAR" \
  -X POST "$RAG_BASE_URL/api/v1/auth/logout"

rm -f "$RAG_COOKIE_JAR"
```

`--fail-with-body` 在 4xx/5xx 时保留错误正文并返回失败退出码。Cookie 文件包含登录凭证，用完删除，不要提交到仓库。

## Python 远程调用

后端环境已包含 `httpx`，独立 Python 项目可先安装 `httpx`。下面的代码由终端输入账号密码，自动保存 Cookie，并将服务故障与正常空结果分开处理。

```python
from getpass import getpass

import httpx

base_url = "http://127.0.0.1:8000"  # 共享服务换成维护者提供的地址

with httpx.Client(base_url=base_url, timeout=60.0) as client:
    login = client.post("/api/v1/auth/login", json={
        "username": input("本站账号："),
        "password": getpass("本站密码："),
    })
    login.raise_for_status()

    try:
        response = client.post("/api/v1/knowledge/search", json={
            "query": "两个第三声连在一起怎么读？",
            "filters": {"knowledge_point_id": "tone_sandhi_3"},
            "top_k": 4,
        })
        response.raise_for_status()
        result = response.json()
        if not result["hits"]:
            print("暂无相关材料")
        for hit in result["hits"]:
            print(hit["title"], hit["score"])
            print(hit["text"])
            print("来源：", hit["source"], "片段：", hit["chunk_id"])
    finally:
        client.post("/api/v1/auth/logout").raise_for_status()
```

`HTTPStatusError` 表示服务返回 4xx/5xx；`RequestError` 表示连接失败或超时，调用方应在自己的业务层处理。登录成功后复用客户端即可，无需为每次检索重新登录；上面退出登录是独立演示脚本的清理步骤。

## 前端调用

在本项目 Vue 前端中，已有登录态时直接调用检索函数；尚未登录时先调用登录函数。使用相对路径以复用 Vite/Nginx 同源代理。

```javascript
async function postJson(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(`${response.status}: ${body.detail ?? '请求失败'}`);
  }
  return body;
}

async function loginRag(username, password) {
  return postJson('/api/v1/auth/login', { username, password });
}

async function searchMaterials(query) {
  const { hits } = await postJson('/api/v1/knowledge/search', {
    query,
    top_k: 4,
    max_context_chars: 6000,
  });
  return hits;
}
```

浏览器自动保存和发送 HttpOnly Cookie，前端不需要读取 `owl_session`。前端也不需要配置 Embedding 密钥。将 `text` 作为文本展示；不要把资料正文直接当作可信 HTML 插入页面。

## 后端内部调用

同一 FastAPI 应用内可注入已经配置好的 `RetrievalService`，直接使用结构化契约。下面是业务函数示例；已有路由可在参数中声明 `service: Annotated[RetrievalService, Depends(retrieval_service)]`，并沿用当前路由的鉴权。

```python
from typing import Annotated

from fastapi import Depends

from app.api.dependencies import retrieval_service
from app.schemas.retrieval import RetrievalFilters, RetrievalQuery, RetrievalResult
from app.services.retrieval import RetrievalService

RagService = Annotated[RetrievalService, Depends(retrieval_service)]


def find_material(question: str, service: RetrievalService) -> RetrievalResult:
    return service.search(RetrievalQuery(
        query=question,
        filters=RetrievalFilters(knowledge_point_id="tone_sandhi_3"),
        top_k=4,
    ))
```

FastAPI 依赖会在服务未启用时返回 503。普通业务函数由调用者传入服务实例，`Depends` 只在 FastAPI 的依赖解析中生效。直接服务调用不经过 HTTP 登录检查，调用入口负责业务鉴权；仓储的资料可见性过滤仍然生效。

当前服务包含同步数据库和 Embedding I/O，适合直接在同步 `def` 路由中使用。在异步工作流或 `async def` 中，可交给线程池执行：

```python
from starlette.concurrency import run_in_threadpool

async def find_material_async(service, request):
    return await run_in_threadpool(service.search, request)
```

内部检索失败可能抛出 `EmbeddingUnavailable` 或 `SQLAlchemyError`。业务模块应捕获并按场景降级；需要在自己的调用链设置并发和总超时预算。

## 接入生成模块

取 `hits[].text` 作为参考材料，保留 `chunk_id`、`content_version` 和 `source` 用于引用。给生成模块的材料可以整理成：

```python
def build_reference_data(hits):
    return [{
        "chunk_id": hit["chunk_id"],
        "content_version": hit["content_version"],
        "source": hit["source"],
        "text": hit["text"],
    } for hit in hits]
```

通过 HTTP 获取的片段是字典；内部 `RetrievalResult` 可先调用 `model_dump()` 转成字典。资料作为参考数据传给模型，其中的文字不应被当作系统指令；生成结果的教学正确性、帮助等级和答案展示仍由业务模块检查。

## 错误与排查

错误体使用 `detail` 字段，例如：

```json
{"detail": "知识检索暂不可用，请稍后重试。"}
```

| 状态码或现象 | 常见原因 | 处理方法 |
| --- | --- | --- |
| `401` | 未登录、Cookie 未发送、会话过期 | 检查基地址及客户端 Cookie，重新登录 |
| `403` | 跨源请求、来源不匹配，或入库账号未授权 | 检查同源代理；入库时检查 `RAG_INGEST_USER_IDS` 是否包含当前用户 ID |
| 入库 `409` | 旧版本覆盖或同版本内容发生变化 | 检查资料版本，更新时递增 `content_version` |
| 入库 `413` | 网关请求体大小超限 | 缩小单次正文/元数据，检查代理请求体限制 |
| `422` | 问题或文档格式错误、字段拼错、范围超限 | 对照请求字段；未知字段也会被拒绝 |
| `503`，提示尚未启用 | `RAG_ENABLED=false` | 维护者启用并重启后端 |
| `503`，提示暂不可用 | Embedding 调用或数据库操作失败 | 联系维护者检查连接、扩展、表和模型配置 |
| 登录 `429` | 登录次数触发限流 | 按 `Retry-After` 等待，复用已有会话 |
| `200` 且 `hits=[]` | 无匹配资料、过滤过严、阈值/预算限制或索引配置不匹配 | 移除可选过滤，检查资料可见性及 Embedding 配置 |
| 连接被拒绝/超时 | 地址、端口、监听范围或网络不可达 | 确认服务已启动，远程调用使用可达地址 |

HTTP 入库和检索响应带 `Cache-Control: no-store`。当前有两个 RAG HTTP 接口，均无流式输出或聊天历史参数；文档列表、详情和删除仍未开放 HTTP 接口，删除由 CLI 或受信任后台服务完成。

## 联调验收

1. 登录成功，`GET /api/v1/auth/me` 返回当前用户。
2. 使用最小查询请求返回 `200`，命中已入库的第三声变调示例，来源与版本正确。
3. 添加 `knowledge_point_id` 过滤后仍能命中；使用不存在的文档 ID 返回空列表。
4. 退出登录后再次检索返回 `401`。
5. 已授权账号调用入库接口返回片段数和 ID；未授权账号返回 403。
6. 更新正文并递增版本后，检索返回新版本；同版本修改返回 409。
7. 业务界面分别处理有结果、空结果和服务故障，并能展示来源。

以上调用契约对应 [检索路由](../../code/backend/app/api/endpoints/knowledge.py)、[数据结构](../../code/backend/app/schemas/retrieval.py) 和 [服务实现](../../code/backend/app/services/retrieval.py)。
