# ZhihuFlow Install

## Goal

Run a local Agent system that searches AI frontier topics, builds an evidence-backed research brief, and generates a Zhihu-style technical article draft with traceable sources and policy checks.

## Success Criteria

- `python -m zhihuflow.cli run --offline` completes without external API keys.
- A Markdown article is written to `.zhihuflow/latest_article.md`.
- A structured run summary is written to `.zhihuflow/latest_run.json`.
- `python -m zhihuflow.cli inspect <trace_id>` shows the event log for replay and debugging.

## Operating Rules

- Do not commit `.zhihuflow/` because it contains local run history.
- Do not put model API keys in code. Use `ZHIHUFLOW_OPENAI_API_KEY`, `ZHIHUFLOW_OPENAI_BASE_URL`, and `ZHIHUFLOW_OPENAI_MODEL`.
- Treat model output as draft content. Publishing requires human review.
- Preserve source citations and policy reports when editing generated articles.

## Steps

1. Confirm Python 3.11+:

   ```bash
   python --version
   ```

2. Run the offline demo:

   ```bash
   python -m zhihuflow.cli run --offline
   ```

3. Run with real public trend sources:

   ```bash
   python -m zhihuflow.cli run \
     --seed "LLM agent" \
     --seed "context engineering" \
     --seed "AI coding agent"
   ```

4. Optional model provider:

   ```bash
   export ZHIHUFLOW_OPENAI_API_KEY="..."
   export ZHIHUFLOW_OPENAI_BASE_URL="https://api.openai.com/v1"
   export ZHIHUFLOW_OPENAI_MODEL="gpt-4o-mini"
   python -m zhihuflow.cli run
   ```

5. Optional Alibaba Cloud Bailian / DashScope provider:

   ```bash
   python3 -m zhihuflow.cli \
     --env-file /Users/bytedance/my/SoloOps/.env \
     model-check --provider aliyun_bailian

   python3 -m zhihuflow.cli \
     --env-file /Users/bytedance/my/SoloOps/.env \
     run --seed "AI coding agent memory"
   ```

   The `.env` file is read locally and secrets are not printed. Prefer rotating keys if they have been pasted into chats or logs.

6. Inspect a trace:

   ```bash
   python -m zhihuflow.cli inspect trace_xxx
   ```

## Harness Layout

```text
zhihuflow/
  app/                   Director and run configuration
  content/               Writer, policy, quality eval, human-writing style
  core/                  Schemas and journaled workflow
  models/                Deterministic, OpenAI-compatible, Bailian providers
  ops/                   Email delivery, scheduler, growth feedback
  research/              Sources, research agent, parallel subagents
  runtime/               Middleware, sandbox, skills, tools
  storage/               SQLite memory and long-term memory
skills/
  builtin/
    deep-research/
    human-writing/
    zhihu-writing/
    policy-review/
```

## Human Writing Check

ZhihuFlow intentionally avoids wrapping model output in a fixed article template. The writer prompt loads `human-writing` and asks for concrete scenes, clear judgment, and uneven emphasis. `PolicyGate` also flags obvious AI-style phrases such as `首先`, `其次`, `综上所述`, `多维度`, `持续优化`, and `具有重要意义`.

Article output constraints:

- Chinese article length target: `1500-2500` characters/word-like units.
- Markdown output must include one `#` title and at least four `##` sections.
- The final section must include references.

## Product Harness Commands

```bash
# Run with default four-perspective parallel research.
python3 -m zhihuflow.cli run --offline

# Inspect the evidence-to-claim graph.
python3 -m zhihuflow.cli claims trace_xxx

# Ingest Zhihu growth feedback.
python3 -m zhihuflow.cli feedback \
  --trace-id trace_xxx \
  --article-id zhihu_article_id \
  --views 1200 --likes 48 --favorites 36 --comments 9 \
  --leads 6 --revenue-cents 29900

# Write a controlled artifact. Path escapes are rejected.
python3 -m zhihuflow.cli sandbox-write reports/demo.txt --content "sandbox artifact ok"
```

## Daily Schedule And Email Delivery

ZhihuFlow uses SMTP email delivery first because it is more stable than writing directly to Zhihu drafts.

Required environment. Copy `.env.example` to `.env`, then fill the QQ Mail authorization code:

```bash
cp .env.example .env

export ZHIHUFLOW_EMAIL_FROM="your_account@qq.com"
export ZHIHUFLOW_EMAIL_TO="target@example.com"
export ZHIHUFLOW_SMTP_USER="your_account@qq.com"
export ZHIHUFLOW_SMTP_PASSWORD="QQ Mail authorization code"
export ZHIHUFLOW_SMTP_HOST="smtp.qq.com"
export ZHIHUFLOW_SMTP_PORT="465"
```

Authorization code path: QQ Mail web -> Settings -> Account -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV -> enable `POP3/SMTP` or `IMAP/SMTP` -> generate authorization code.

Run once without sending email:

```bash
python3 -m zhihuflow.cli schedule --once --offline --dry-run-email
```

Run once and send email:

```bash
python3 -m zhihuflow.cli --env-file .env schedule --once
```

Run every day at 09:00:

```bash
python3 -m zhihuflow.cli --env-file .env schedule --daily-at 09:00
```

## TODO

- [ ] Add more trend sources for Product Hunt, GitHub trending, arXiv categories, and curated RSS.
- [ ] Add post-publish analytics import for Zhihu metrics.
- [ ] Add a web UI over the same memory store.
- [ ] Add eval golden sets for title quality, citation quality, and policy risk.

## EXECUTE NOW

Start with:

```bash
python -m zhihuflow.cli run --offline
```
