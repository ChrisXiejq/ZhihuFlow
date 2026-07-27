from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from zhihuflow.app.config import DirectorConfig
from zhihuflow.app.director import ContentDirector
from zhihuflow.core.schemas import FeedbackEvent, SourceRef, to_jsonable
from zhihuflow.models.providers import load_env_file, model_from_env
from zhihuflow.ops.delivery import EmailDelivery
from zhihuflow.ops.feedback import FeedbackIngestor
from zhihuflow.ops.scheduler import DailyScheduler
from zhihuflow.research.agent import ResearchAgent
from zhihuflow.research.sources import ResearchScout, StaticSource, TrendScout
from zhihuflow.research.subagents import ParallelResearchOrchestrator
from zhihuflow.runtime.sandbox import LocalSandbox
from zhihuflow.storage.longterm import LongTermMemory
from zhihuflow.storage.memory import MemoryStore
from zhihuflow.web.server import WebConsoleConfig, run_web_console


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zhihuflow", description="ZhihuFlow AI topic research and Zhihu article agent.")
    parser.add_argument("--db", default=".zhihuflow/zhihuflow.sqlite3", help="SQLite memory database path.")
    parser.add_argument("--env-file", default=None, help="Optional .env path. Values are loaded without printing secrets.")
    parser.add_argument("--memory-file", default=".zhihuflow/memory.json", help="Local long-term memory JSON path.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Discover a hot AI topic and generate a Zhihu-style article draft.")
    run.add_argument("--seed", action="append", default=[], help="Seed query. Can be passed multiple times.")
    run.add_argument("--out", default=".zhihuflow/latest_article.md", help="Output markdown path.")
    run.add_argument("--json", default=".zhihuflow/latest_run.json", help="Output structured run summary.")
    run.add_argument("--trace-id", default=None, help="Resume an existing trace id.")
    run.add_argument("--offline", action="store_true", help="Use built-in fallback topics by disabling network sources.")
    run.add_argument("--no-parallel-research", action="store_true", help="Disable perspective-based parallel research.")
    run.add_argument("--research-workers", type=int, default=4, help="Parallel research worker count.")
    run.add_argument("--min-chars", type=int, default=1500, help="Target minimum article length.")
    run.add_argument("--max-chars", type=int, default=2500, help="Target maximum article length.")

    schedule = sub.add_parser("schedule", help="Run daily article generation and email delivery.")
    schedule.add_argument("--seed", action="append", default=[], help="Seed query. Can be passed multiple times.")
    schedule.add_argument("--daily-at", default="09:00", help="Local time HH:MM for daily generation.")
    schedule.add_argument("--once", action="store_true", help="Run one scheduled job immediately and exit.")
    schedule.add_argument("--offline", action="store_true", help="Use offline sources.")
    schedule.add_argument("--dry-run-email", action="store_true", help="Generate article but do not send email.")
    schedule.add_argument("--out-dir", default=".zhihuflow/scheduled", help="Scheduled run output directory.")
    schedule.add_argument("--min-chars", type=int, default=1500)
    schedule.add_argument("--max-chars", type=int, default=2500)

    inspect = sub.add_parser("inspect", help="Inspect a trace event log.")
    inspect.add_argument("trace_id")

    claims = sub.add_parser("claims", help="Inspect claim graph for a trace.")
    claims.add_argument("trace_id")

    feedback = sub.add_parser("feedback", help="Ingest Zhihu performance feedback for a generated article.")
    feedback.add_argument("--trace-id", required=True)
    feedback.add_argument("--article-id", required=True)
    feedback.add_argument("--views", type=int, default=0)
    feedback.add_argument("--likes", type=int, default=0)
    feedback.add_argument("--favorites", type=int, default=0)
    feedback.add_argument("--comments", type=int, default=0)
    feedback.add_argument("--follows", type=int, default=0)
    feedback.add_argument("--leads", type=int, default=0)
    feedback.add_argument("--revenue-cents", type=int, default=0)
    feedback.add_argument("--notes", default="")

    sandbox = sub.add_parser("sandbox-write", help="Write a text artifact into the local sandbox.")
    sandbox.add_argument("relative_path")
    sandbox.add_argument("--content", required=True)

    check = sub.add_parser("model-check", help="Call the configured model with a tiny prompt.")
    check.add_argument("--provider", default=None, help="Provider override: aliyun_bailian, openai-compatible, or mock.")

    web = sub.add_parser("web", help="Launch the local ZhihuFlow web console.")
    web.add_argument("--host", default="127.0.0.1", help="Web console host.")
    web.add_argument("--port", type=int, default=8765, help="Web console port.")
    web.add_argument("--settings", default=".zhihuflow/web_settings.json", help="Web settings JSON path.")
    web.add_argument("--history", default=".zhihuflow/web_history.json", help="Web history JSON path.")
    web.add_argument("--out-dir", default=".zhihuflow/web_runs", help="Web-generated article output directory.")
    web.add_argument("--poll-seconds", type=int, default=20, help="Scheduler polling interval.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.env_file:
        load_env_file(args.env_file)
    if args.command == "web":
        def director_factory(offline: bool) -> ContentDirector:
            return build_director(MemoryStore(args.db), LongTermMemory(args.memory_file), offline=offline)

        run_web_console(
            WebConsoleConfig(
                host=args.host,
                port=args.port,
                settings_path=args.settings,
                history_path=args.history,
                output_dir=args.out_dir,
                env_file=None,
                poll_seconds=args.poll_seconds,
            ),
            director_factory,
        )
        return 0
    store = MemoryStore(args.db)
    long_term_memory = LongTermMemory(args.memory_file)
    try:
        if args.command == "run":
            seeds = args.seed or ["LLM agent", "context engineering", "AI coding agent", "Agentic RAG"]
            director = build_director(store, long_term_memory, offline=args.offline)
            result = director.run(
                DirectorConfig(
                    seeds=seeds,
                    parallel_research=not args.no_parallel_research,
                    research_workers=args.research_workers,
                    target_min_chars=args.min_chars,
                    target_max_chars=args.max_chars,
                ),
                trace_id=args.trace_id,
            )
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result.article.body_markdown, encoding="utf-8")
            json_path = Path(args.json)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
            print(
                json.dumps(
                    {
                        "trace_id": result.trace_id,
                        "risk": result.policy.overall_risk.value,
                        "quality": result.quality.overall_score,
                        "article": str(out_path),
                        "summary": str(json_path),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        if args.command == "schedule":
            seeds = args.seed or ["LLM agent", "context engineering", "AI coding agent", "Agentic RAG"]
            director = build_director(store, long_term_memory, offline=args.offline)
            scheduler = DailyScheduler(director, EmailDelivery(), output_dir=args.out_dir)
            config = DirectorConfig(seeds=seeds, target_min_chars=args.min_chars, target_max_chars=args.max_chars)
            if args.once:
                result = scheduler.run_once(config, dry_run_email=args.dry_run_email)
                print(json.dumps(to_jsonable(result), ensure_ascii=False))
                return 0
            scheduler.run_forever(config, args.daily_at, dry_run_email=args.dry_run_email)
            return 0
        if args.command == "inspect":
            print(json.dumps(store.events(args.trace_id), ensure_ascii=False, indent=2))
            return 0
        if args.command == "claims":
            print(
                json.dumps(
                    {
                        "claims": store.claims(args.trace_id),
                        "edges": store.claim_edges(args.trace_id),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "feedback":
            ingestor = FeedbackIngestor(store, long_term_memory)
            summary = ingestor.ingest(
                FeedbackEvent(
                    trace_id=args.trace_id,
                    article_id=args.article_id,
                    views=args.views,
                    likes=args.likes,
                    favorites=args.favorites,
                    comments=args.comments,
                    follows=args.follows,
                    leads=args.leads,
                    revenue_cents=args.revenue_cents,
                    notes=args.notes,
                )
            )
            print(json.dumps(summary, ensure_ascii=False))
            return 0
        if args.command == "sandbox-write":
            artifact = LocalSandbox().write_text(args.relative_path, args.content)
            print(json.dumps(to_jsonable(artifact), ensure_ascii=False))
            return 0
        if args.command == "model-check":
            model = model_from_env(args.provider)
            text = model.generate(
                "你是 ZhihuFlow 的模型连通性检查器。只输出一句中文短句。",
                "请用一句话回答：模型连接正常。",
                temperature=0.0,
            )
            print(json.dumps({"model": model.model_id, "response_preview": text[:120]}, ensure_ascii=False))
            return 0
    finally:
        store.close()
    return 2


def build_director(store: MemoryStore, long_term_memory: LongTermMemory, *, offline: bool = False) -> ContentDirector:
    if not offline:
        return ContentDirector(memory=store, long_term_memory=long_term_memory)
    refs = [
        SourceRef(title="Context engineering for long-horizon AI agents", url="local://context", source="offline"),
        SourceRef(title="Agent workflow orchestration and tool contracts", url="local://workflow", source="offline"),
        SourceRef(title="Evaluation patterns for AI coding agents", url="local://eval", source="offline"),
        SourceRef(title="Human writing style for technical content", url="local://human-writing", source="offline"),
    ]
    static = StaticSource(name="offline", refs=refs)
    scout = ResearchScout([static])
    return ContentDirector(
        memory=store,
        trend_scout=TrendScout([static]),
        research_agent=ResearchAgent(scout),
        parallel_research=ParallelResearchOrchestrator(scout),
        long_term_memory=long_term_memory,
    )


if __name__ == "__main__":
    raise SystemExit(main())
