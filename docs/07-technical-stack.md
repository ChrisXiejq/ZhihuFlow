# 技术选型

## 1. 默认技术栈与运营商映射

| 层 | 选择 | 本地/线上运营商 | 理由 |
| --- | --- | --- | --- |
| Web | React + TypeScript + Vite + TanStack Query + shadcn/ui | 本机 / ECS 容器 | 小团队开发快、类型安全、组件生态成熟 |
| API | Python 3.12 + FastAPI + Pydantic v2 | 本机 / ECS 容器 | 与 Agent/多模态生态贴近、Schema 强 |
| ORM/迁移 | SQLAlchemy 2 + Alembic | 随 API 运行 | 事务、迁移、测试成熟 |
| 工作流 | LangGraph | 随 Worker 运行 | 状态持久化、人工中断、分支清晰 |
| DB | PostgreSQL 16 + pgvector | 本地：Docker PostgreSQL；生产：阿里云 RDS PostgreSQL | 业务数据与向量检索统一，MVP 足够 |
| 缓存/队列 | Redis + Dramatiq 或 Celery | 本地：Docker Redis；生产：阿里云 Tair（兼容 Redis） | 处理异步生成与媒体任务 |
| 对象存储 | S3 API 抽象 | 本地：MinIO；生产：阿里云 OSS | 多媒体、渲染产物、数据库备份存储 |
| 媒体 | FFmpeg + Pillow + OCR 引擎 | 本机 / ECS Worker | 结果可复现、成本低 |
| 观测 | OpenTelemetry + Langfuse | stdout / SLS + Langfuse | Trace、成本、Prompt 与评测关联 |
| 身份 | Auth.js/自建 JWT + OIDC | 应用内；后续可对接 IdP | 多租户 RBAC 与后续企业 SSO 扩展 |
| 镜像/部署 | Docker Compose；后续 ACK | Docker Desktop / ECS + ACR | ECS 单机先跑通，后续可扩展 |
| 镜像仓库 | Docker Registry 接口 | 本地：本机 build；生产：阿里云 ACR（推荐） | 不在 ECS 手工构建生产镜像 |
| 域名/TLS | DNS + Caddy/Nginx + ACME | 阿里云 DNS/SSL 证书（可选） | HTTPS、反向代理和安全响应头 |
| 日志/告警 | JSON Log + OTel | 本地 stdout；生产：阿里云 SLS + Langfuse | 系统日志与 LLM Trace 分离 |

## 2. 生产组件选择矩阵

| 能力 | 本地测试 | ECS 试运行（最低成本） | 正式线上推荐 | 迁移触发条件 |
| --- | --- | --- | --- | --- |
| 应用 | Compose | ECS Compose | ECS 多实例/ACK | API 与 worker 互相抢资源或需高可用 |
| PostgreSQL | 容器 PostgreSQL | ECS 容器 PostgreSQL，仅演示 | RDS PostgreSQL 高可用系列 | 开始保留真实用户数据或需要自动备份/恢复 |
| 向量检索 | pgvector | pgvector | RDS PostgreSQL + pgvector（确认实例扩展支持） | 向量/检索负载明显独立时再评估专用向量库 |
| Redis | 容器 Redis | 容器 Redis，仅非关键缓存 | Tair Redis 开源版标准双副本 | 队列/会话不可丢或需要备份/监控 |
| 文件 | MinIO | ECS 磁盘，不建议 | OSS 私有 Bucket | 任意真实用户素材上传前 |
| 镜像 | local build | ECS pull | ACR | 需要 CI/CD 或多环境 |
| 密钥 | `.env.local` | ECS 环境文件（权限 600） | KMS/Secrets Manager 或严格受控环境变量 | 团队协作、密钥轮换或生产审计 |
| 日志 | stdout | Docker log + logrotate | SLS + OTel + Langfuse | 需要告警、检索和长期保留 |

**结论**：你的 ECS 适合部署 Web/API/Worker/反代；生产数据服务优先购买托管版。RDS PostgreSQL 支持高可用系列和 pgvector 等扩展能力，但具体版本、地域与规格支持情况必须在购买前用控制台/官方扩展列表核验。[RDS 产品系列](https://help.aliyun.com/zh/rds/apsaradb-rds-for-postgresql/product-editions/)；[RDS PostgreSQL 与 pgvector](https://help.aliyun.com/zh/rds/apsaradb-rds-for-postgresql/apsaradb-rds-for-postgresql-supports-postgresql-17)。

OSS 用于私有素材和渲染产物，默认阻止公共访问；应用通过短时预签名 URL 上传/下载。阿里云已默认对新建 Bucket 开启阻止公共访问，正符合 RedFlow 的素材隐私要求。[OSS 产品公告](https://help.aliyun.com/zh/oss/oss-product-bulletin/)

Tair 是兼容 Redis 协议的托管服务，可承载队列 Broker、任务状态缓存和限流；正式环境避免使用其无备份保障的单副本纯缓存模式。[Tair 文档](https://help.aliyun.com/zh/redis/)

## 3. 不绑定单一模型供应商

实现一个 `ModelProvider` 抽象：

```python
class ModelProvider(Protocol):
    async def generate_json(self, task: TaskSpec, schema: type[T]) -> T: ...
    async def describe_image(self, asset: AssetRef) -> ImageAnalysis: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

配置层按任务选择模型能力，而不是在业务代码中写具体模型名。开发环境可以用较低成本模型和 fixture；生产按质量/成本/数据策略切换供应商。

## 4. 依赖边界

- `domain` 不依赖 FastAPI、LangGraph 或第三方 SDK。
- `application` 定义 use case 和 ports。
- `infrastructure` 实现 DB、模型、对象存储、Publisher。
- `presentation` 只做 HTTP/SSE/UI。
- Agent 图调用 application ports，不直接操作 ORM session。

## 5. 本地开发最低配置

```text
Node.js 22+
Python 3.12+
Docker Desktop
PostgreSQL 16（或 Docker）
Redis 7（或 Docker）
MinIO（或 Docker）
FFmpeg
```

## 6. 环境变量类别

```text
DATABASE_URL
REDIS_URL
S3_ENDPOINT / S3_BUCKET / S3_ACCESS_KEY / S3_SECRET_KEY
JWT_SECRET
MODEL_PROVIDER_*           # 按供应商分组，禁止提交
OTEL_EXPORTER_OTLP_ENDPOINT
LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
PUBLISHER_*                # 仅授权平台接入使用
```

提交 `.env.example`，不提交 `.env`；CI 使用 secrets；生产使用 KMS/Secret Manager。
