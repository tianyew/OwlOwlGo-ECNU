# RAG 基础模块与调用指南

调用已部署服务的同学请先看 [RAG 接口与调用方法](rag-api.md)，包含完整参数、登录鉴权及 curl、Python、前端示例。

当前已实现教学知识的入库、分块、Embedding、pgvector 精确余弦检索、版本替换和删除。它向伴学、学习规划、出题模块返回带来源的材料；回复生成由各业务模块负责。个人偏好、对话记录和学习成绩仍由各自业务模块管理。

## 代码位置

| 路径（相对 code/backend） | 用途 |
| --- | --- |
| `app/schemas/retrieval.py` | 文档、查询、过滤器和结果契约 |
| `app/domain/retrieval/chunking.py` | 段落/句子优先的确定性分块 |
| `app/integrations/embedding/client.py` | 同步 OpenAI 兼容 Embedding 适配器 |
| `app/db/repositories/knowledge.py` | pgvector 建表、事务写入、过滤与查询 |
| `app/services/retrieval.py` | `IngestionService` 与 `RetrievalService` |
| `app/services/knowledge_cli.py` | 管理员建表、入库、查询、删除命令 |
| `app/api/endpoints/knowledge.py` | 登录检索和授权文档入库接口 |

路由遵循新结构 `app/api/endpoints/`，通过 `app/api/router.py` 汇总。HTTP 鉴权复用 `app/api/dependencies.py`。RAG 默认关闭；普通学习功能不依赖向量服务。

## 本地准备

需要 PostgreSQL 17 和 pgvector。已有的 `postgres:17-alpine` 镜像没有 vector 扩展，可以使用可选 Compose 覆盖文件。以下命令在仓库根目录运行：

```bash
docker compose -f infrastructure/compose.yaml -f infrastructure/compose.rag.yaml up -d database
```

已有数据库先备份；这会切换同一主版本的数据库镜像，挂载原数据卷。不要使用 `down -v`。团队共享数据库也可以由管理员安装 pgvector，无需使用本地 Docker。

在 `code/backend/.env` 配置以下字段。地址填写账号控制台给出的完整 OpenAI 兼容 `/v1` 基地址，模型和维度必须由该服务支持：

```dotenv
RAG_ENABLED=false
RAG_EMBEDDING_BASE_URL=https://你的服务地址/compatible-mode/v1
RAG_EMBEDDING_API_KEY=你的向量服务密钥
RAG_EMBEDDING_MODEL=text-embedding-v4
RAG_EMBEDDING_DIMENSIONS=1024
RAG_EMBEDDING_REVISION=1
```

Embedding 密钥独立于 DeepSeek 聊天密钥。适配器按照兼容协议向 `/embeddings` 发送文本批次，验证返回数量、顺序、维度和非零有限向量；不自动重试、不跟随重定向，错误不返回上游响应正文。服务配置以供应商账号实际可用模型为准。[百炼 Embedding 文档](https://help.aliyun.com/zh/model-studio/embedding)

进入 `code/backend`，使用已安装项目依赖的 Python 环境：

```bash
python -m app.services.knowledge_cli init
python -m app.services.knowledge_cli ingest examples/rag/tone-sandhi.json
python -m app.services.knowledge_cli search '两个第三声怎么连读'
```

测试示例需标记为 `approved/public/teaching` 才能被召回；当前示例已用于本地链路验证，正式资料仍需教学审核。若修改已入库文档的审核状态或可见性，递增 `content_version` 后重新入库。请勿直接导入含测验答案的整个课程 JSON。

也可把正文独立保存在 UTF-8 文本或 Markdown 文件中，元数据 JSON 可以省略 `text`：

```bash
python -m app.services.knowledge_cli ingest /path/to/metadata.json --text-file /path/to/lesson.md
python -m app.services.knowledge_cli delete tone-sandhi-intro
```

`init` 独立于账号迁移，可重复执行；初始化角色需要创建扩展和表的权限，普通运行角色只需对应表的读写权限。表为 `rag_documents`、`rag_chunks`、`rag_schema_versions`，扩展放在 `public` schema。API 启动不自动建表，也不调用模型。

## 后端同学调用

完成初始化后设置 `RAG_ENABLED=true` 并重启后端。同步路由可注入公共服务：

```python
from typing import Annotated
from fastapi import Depends
from app.api.dependencies import retrieval_service
from app.schemas.retrieval import RetrievalFilters, RetrievalQuery
from app.services.retrieval import RetrievalService

# 在同步 endpoint 的参数里使用：
# service: Annotated[RetrievalService, Depends(retrieval_service)]

def find_material(service: RetrievalService):
    return service.search(RetrievalQuery(
        query="第三声变调怎么理解",
        filters=RetrievalFilters(knowledge_point_id="tone_sandhi_3"),
        top_k=4,
        max_context_chars=6000,
        min_score=0.0,
    ))
```

非 HTTP 服务也可直接构造 `RetrievalService(PostgresKnowledgeRepository(engine), CompatibleEmbedder(settings))`，两类服务与具体聊天模型解耦。入库使用同一组依赖构造 `IngestionService`，调用 `ingest(KnowledgeDocument(...))`。也可调用 `POST /api/v1/knowledge/documents` 提交相同的文档 JSON，由服务自动切片、向量化并事务写入；HTTP 写入仅允许 `RAG_INGEST_USER_IDS` 指定的登录账号。

当前数据库和 HTTP 客户端都是同步实现；在 `async def` 或异步工作流中，使用受限线程池调用，避免阻塞事件循环。检索失败会抛出 `EmbeddingUnavailable` 或数据库异常，调用方可以退回课程精确查询，不能把失败包装成“没有相关资料”。无命中则正常返回空 `hits`。

`RetrievalResult.hits` 每项包含 `chunk_id/document_id/title/text/source/license/content_version/score`。`score` 为余弦相似度，不是正确概率；阈值需要用真实查询评测。将片段作为参考数据提供给模型，并保留片段 ID 用于引用；资料中的指令不能成为系统指令。

## HTTP 入库权限

在 `code/backend/.env` 中设置允许入库的用户 UUID 列表，并重启后端：

```dotenv
RAG_ENABLED=true
RAG_INGEST_USER_IDS=["00000000-0000-0000-0000-000000000001"]
```

将示例 UUID 替换为登录用户在 `GET /api/v1/auth/me` 中的实际 `id`。默认 `[]` 禁止全部 HTTP 写入，普通登录用户仍可检索；CLI 不受这份 HTTP 权限名单影响。请求 `POST /api/v1/knowledge/documents`，JSON 与 CLI 入库文件一致。成功返回文档版本、切片数量和 ID；新增、更新和重复导入均返回 200，版本冲突为 409。完整字段和 curl/Python 示例见 [入库接口](rag-api.md#文档入库接口)。

## HTTP 检索调用

`POST /api/v1/knowledge/search`，复用登录 Cookie 和同源检查：

```json
{
  "query": "第三声变调怎么理解",
  "filters": {"knowledge_point_id": "tone_sandhi_3", "language": "zh"},
  "top_k": 4,
  "max_context_chars": 6000,
  "min_score": 0.0
}
```

返回 `{"hits": [...], "embedding_key": "..."}`。未登录为 401，格式错误为 422，禁用/服务故障为 503。过滤字段支持 `direction_id/knowledge_point_id/language/difficulty/document_id`，均为 AND 关系；列表元数据采用包含匹配。服务端始终额外限定 `approved + public + teaching`，调用方无法通过过滤器放开限制。当前没有可读取答案片段的通道；后续若需要，必须结合后端提交状态单独授权。

## 数据生命周期与范围

- 每篇文档最多 200,000 字符，当前每片最多 1,000 字符、重叠 100 字符。优先在后半部分的段落/句末切分，超长段落硬切；计量是字符数，并非 token 数。首版不解析 Markdown 语法树，不自动补充上级标题。
- 文档按 ID 更新，只保留当前版本。来源、审核状态、可见性和正文等任一变更都需增加 `content_version`；同版本同内容可重复导入，同版本不同内容及旧版本覆盖会被拒绝。需要保留所有历史正文时，在正式内容版本库补充归档。
- 入库先完成所有 Embedding，再在同一事务里替换元数据和片段。同文档写入/删除串行加锁，失败回滚；重复入库仍会请求 Embedding，应避免无意义批量重导。
- Embedding 的地址、模型、维度和 revision 共同生成索引标识。查询只读取同标识数据；更换配置后须重新导入资料。标识不包含密钥，轮换密钥不要求重建。
- 下线资料可调用 `delete()`，同步删除文档及全部片段；保留文档但撤销可见性时，以更高内容版本重新导入 `draft/internal`。首版不缓存检索结果。
- 查询按余弦距离精确排序，并限制结果数和正文总字符数；超出预算的整片跳过。首版不建立近似索引、不做关键词混合检索或重排序，也没有相关性质量达标结论。资料规模增长后再按实际延迟评估索引与混合检索。[pgvector 检索说明](https://github.com/pgvector/pgvector)

## 验证

```bash
python -m pytest -q
ruff check app tests
```

默认跳过真实数据库测试。数据库测试使用 `OWL_TEST_DATABASE_URL`，也可在专用测试库配置下使用 `--postgres`；需要 pgvector 与创建独立 schema 的权限。不要指向普通业务库。CI 已使用 pgvector 镜像，覆盖真实余弦排序、元数据过滤、草稿/内部/答案隔离、版本冲突、事务回滚、服务重建、Embedding 版本隔离和级联删除；向量服务协议使用 MockTransport 验证，不产生外部模型费用。

验收检索质量时，另外准备真实审核材料、预期来源和汉语/拼音/英文查询集合，统计 Recall@k、无关结果和延迟。本次功能测试不等于真实模型的教学检索质量评测。
