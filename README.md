# ZhihuFlow

> 多模态内容增长 Agent：帮助创作者与小团队完成「趋势洞察 → 创意导演 → 内容生产 → 合规审核 → 辅助发布 → 效果复盘」的闭环。

ZhihuFlow 当前 MVP 聚焦 **AI/LLM/Agent 前沿话题发现 → 证据研究 → 知乎风格技术长文生成 → 合规审查 → Trace 复盘**。它不是批量发帖或规避平台限制的工具；所有发布均遵循平台授权能力、频控与人工确认策略。

## 快速运行

无需 API key 的离线演示：

```bash
python -m zhihuflow.cli run --offline
```

运行后会生成：

- `.zhihuflow/latest_article.md`：知乎风格技术文章草稿
- `.zhihuflow/latest_run.json`：结构化结果、证据、合规报告
- `.zhihuflow/zhihuflow.sqlite3`：event log、workflow journal、artifacts、claims

查看 Trace：

```bash
python -m zhihuflow.cli inspect <trace_id>
```

接入真实 OpenAI-compatible 模型时设置：

```bash
export ZHIHUFLOW_OPENAI_API_KEY="..."
export ZHIHUFLOW_OPENAI_BASE_URL="https://api.openai.com/v1"
export ZHIHUFLOW_OPENAI_MODEL="gpt-4o-mini"
python -m zhihuflow.cli run --seed "LLM agent" --seed "context engineering"
```

使用阿里云百炼 / DashScope Qwen，可通过本地 `.env` 加载配置，不会把密钥写入 ZhihuFlow：

```bash
python3 -m zhihuflow.cli \
  --env-file .env \
  model-check --provider aliyun_bailian

python3 -m zhihuflow.cli \
  --env-file .env \
  run --seed "AI coding agent memory" --seed "context engineering agent workflow"
```

更多 Agent 安装与运行规则见 [Install.md](Install.md)。

## DeerFlow-style Harness 设计

ZhihuFlow 参考 DeerFlow 2.0 的 Harness 思路实现了轻量版本：

- **Lead Agent**：`ContentDirector` 是唯一入口，负责计划、委派和收敛。
- **Skills**：`skills/builtin/*/SKILL.md` 按需加载，包括 deep-research、zhihu-writing、policy-review。
- **Human Writing**：`human-writing` Skill 专门约束去 AI 味，要求明确判断、具体场景、非对称结构和删除模板套话。
- **Tools**：`ToolRegistry` 记录工具契约、输入 schema 和风险等级，避免工具能力散落在 prompt 里。
- **Middleware**：`MiddlewareChain` 在每个 workflow step 前后注入上下文预算和工具风险契约。
- **Sub-agent Research**：`ParallelResearchOrchestrator` 按论文、工程、社区、商业四个视角并行研究，再合并成一个 ResearchBrief。
- **Memory**：SQLite 保存 event log、workflow journal、artifacts、claims 和 claim graph；`.zhihuflow/memory.json` 保存长期记忆。
- **Checkpointer**：`JournaledWorkflow` 支持同一 trace 下的 step replay。
- **Context Offloading**：当状态过大时写入 briefing，而不是把所有历史塞进模型上下文。
- **Policy Gate**：发布前检查夸大收益、自动发布、平台规避、引用不足和明显 AI 模板表达等风险。
- **Quality Eval**：`QualityEvaluator` 对 evidence、human voice、specificity、commercial safety、structure 做确定性评分。
- **Growth Loop**：`feedback` CLI 写入知乎浏览、赞藏、评论、线索、收入数据，形成 GMV 反馈闭环。
- **Sandbox**：`LocalSandbox` 为 Skill/Tool artifact 提供受控写入边界，防止路径逃逸。

## 分包结构

`zhihuflow/` 已按产品边界拆分：

```text
zhihuflow/
  app/          Director、运行配置、顶层编排
  content/      Writer、PolicyGate、QualityEvaluator、去 AI 味规则
  core/         dataclass schemas、journaled workflow
  models/       Bailian / OpenAI-compatible / deterministic provider
  ops/          邮件投递、每日调度、知乎反馈写入
  research/     趋势源、研究 Agent、并行 Sub-agent 研究
  runtime/      middleware、skills、tools、sandbox
  storage/      SQLite memory、long-term memory
  web/          Python Web API、React + TypeScript 前端包、静态构建产物
```

## 去 AI 味策略

当前写作链路不再把模型输出套进固定模板，而是让模型直接写完整正文，本地只补必要标题和参考来源。`human-writing` Skill 会要求：

- 开头给判断或真实场景，不写泛泛背景。
- 少用“首先、其次、最后、综上所述”等机械连接词。
- 每个核心观点落到一个工程细节、具体场景或反例。
- 允许第一人称判断和取舍，不追求面面俱到。
- 段落和标题不强求对称，避免咨询报告腔。

文章生成还有硬约束：

- 中文正文目标字数：`1500-2500`。
- Markdown 格式：必须有 1 个一级标题和至少 4 个二级标题。
- 文末必须保留 `参考来源`。

## 产品级能力命令

运行一次完整链路，默认开启四视角并行研究：

```bash
python3 -m zhihuflow.cli run --seed "AI agent harness product memory eval"
```

查看 claim graph：

```bash
python3 -m zhihuflow.cli claims trace_xxx
```

写入知乎增长反馈：

```bash
python3 -m zhihuflow.cli feedback \
  --trace-id trace_xxx \
  --article-id zhihu_article_id \
  --views 1200 --likes 48 --favorites 36 --comments 9 \
  --leads 6 --revenue-cents 29900
```

写入受控 Sandbox artifact：

```bash
python3 -m zhihuflow.cli sandbox-write reports/demo.txt --content "sandbox artifact ok"
```

## 本地 Web 控制台

前端源码位于 `zhihuflow/web/frontend/`，使用 React + TypeScript + Tailwind CSS + Radix UI。构建后的静态文件输出到 `zhihuflow/web/static/`，由 Python Web 服务托管。

首次修改前端后构建：

```bash
cd zhihuflow/web/frontend
pnpm install
pnpm run build
```

启动本地控制台：

```bash
python3 -m zhihuflow.cli --env-file .env web
```

打开 `http://127.0.0.1:8765` 后，可以在页面上完成核心操作：

- 开启或关闭每日发文任务。
- 设置定时发文时间、文章字数范围和搜索主题领域。
- 选择是否生成后发送到已配置邮箱。
- 手动触发一次发文任务。
- 查看历史生成文章、质量分、风险等级和文章预览。

Web 控制台的配置、历史和文章默认写入 `.zhihuflow/web_settings.json`、`.zhihuflow/web_history.json` 和 `.zhihuflow/web_runs/`，这些本地运行数据不会提交到 Git。

## 每日调度和邮箱投递

ZhihuFlow 当前选择 SMTP 邮件投递作为最稳定的自动化路径。知乎草稿箱没有稳定公开写入接口，直接写草稿箱更容易遇到登录态、风控和页面变更问题。

配置 QQ 邮箱授权码。推荐复制 `.env.example` 到本机 `.env`，再把授权码填进去：

```bash
cp .env.example .env
```

`.env.example` 已默认写成：

```bash
export ZHIHUFLOW_EMAIL_FROM="your_account@qq.com"
export ZHIHUFLOW_EMAIL_TO="target@example.com"
export ZHIHUFLOW_SMTP_USER="your_account@qq.com"
export ZHIHUFLOW_SMTP_PASSWORD="邮箱授权码，不是登录密码"
export ZHIHUFLOW_SMTP_HOST="smtp.qq.com"
export ZHIHUFLOW_SMTP_PORT="465"
```

QQ 邮箱授权码获取路径：登录 QQ 邮箱网页版 -> 设置 -> 账号 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务 -> 开启 `POP3/SMTP服务` 或 `IMAP/SMTP服务` -> 按页面提示验证后生成授权码。

立即跑一次但不发邮件：

```bash
python3 -m zhihuflow.cli schedule --once --offline --dry-run-email
```

立即生成并发送邮件：

```bash
python3 -m zhihuflow.cli --env-file .env \
  schedule --once
```

每天 09:00 生成并发送：

```bash
python3 -m zhihuflow.cli --env-file .env \
  schedule --daily-at 09:00
```

## 项目目标

- 为个人创作者缩短从热点发现到可审核长文草稿的时间。
- 以 **Content Director Agent** 统一账号目标、趋势证据、研究 claims、文章结构和商业 CTA。
- 提供可观测、可评测、可审计、可恢复的 Agent 工作流，而不是不可控的一次性生成脚本。
- 作为秋招求职项目，展示 Agent runtime、工具契约、event log、context offloading、policy gate 和内容增长场景的工程能力。

## MVP 边界

首版支持：AI 前沿种子词、公开趋势源、研究证据、claim 抽取、知乎文章草稿、合规报告、草稿导出、执行 Trace、workflow replay 和离线演示。

首版不支持：模拟登录、绕过验证码、批量矩阵发帖、虚假互动、未授权抓取私有内容、承诺收益或自动发布。
