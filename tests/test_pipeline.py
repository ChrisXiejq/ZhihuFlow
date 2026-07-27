from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zhihuflow.app.config import DirectorConfig
from zhihuflow.app.director import ContentDirector
from zhihuflow.content.policy import PolicyGate
from zhihuflow.content.style import detect_ai_flavor
from zhihuflow.content.writer import _word_count_zh
from zhihuflow.core.schemas import ArticlePackage, FeedbackEvent, SourceRef
from zhihuflow.ops.delivery import EmailDelivery
from zhihuflow.ops.feedback import FeedbackIngestor
from zhihuflow.ops.scheduler import DailyScheduler
from zhihuflow.research.agent import ResearchAgent
from zhihuflow.research.sources import ResearchScout, StaticSource, TrendScout
from zhihuflow.research.subagents import ParallelResearchOrchestrator
from zhihuflow.runtime.sandbox import LocalSandbox, SandboxViolation
from zhihuflow.storage.memory import MemoryStore
from zhihuflow.web.server import WebConsoleConfig, WebConsoleState


def make_director(tmp_path: Path) -> ContentDirector:
    refs = [
        SourceRef(title="Context engineering for long-horizon AI agents", url="local://context", source="offline"),
        SourceRef(title="Agent workflow orchestration and tool contracts", url="local://workflow", source="offline"),
        SourceRef(title="Evaluation patterns for AI coding agents", url="local://eval", source="offline"),
    ]
    source = StaticSource(name="offline", refs=refs)
    return ContentDirector(
        memory=MemoryStore(tmp_path / "zhihuflow.sqlite3"),
        trend_scout=TrendScout([source]),
        research_agent=ResearchAgent(ResearchScout([source])),
        parallel_research=ParallelResearchOrchestrator(ResearchScout([source])),
    )


class PipelineTest(unittest.TestCase):
    def test_pipeline_generates_article_with_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            result = director.run(DirectorConfig(seeds=["context engineering", "AI agent workflow"]))

            self.assertTrue(result.trace_id.startswith("trace_"))
            self.assertTrue(result.article.body_markdown.startswith("# "))
            self.assertGreaterEqual(result.article.body_markdown.count("\n## "), 4)
            self.assertGreaterEqual(_word_count_zh(result.article.body_markdown), 1500)
            self.assertLessEqual(_word_count_zh(result.article.body_markdown), 2500)
            self.assertIn("参考来源", result.article.body_markdown)
            self.assertGreater(result.quality.overall_score, 0)
            self.assertTrue(result.policy.approved_for_draft)
            self.assertTrue(result.artifacts["article_markdown"].startswith("art_"))
            self.assertTrue(result.artifacts["quality_report"].startswith("art_"))

            events = director.memory.events(result.trace_id)
            event_types = [event["event_type"] for event in events]
            self.assertIn("workflow.started", event_types)
            self.assertIn("research.parallel.completed", event_types)
            self.assertIn("claim_graph.updated", event_types)
            self.assertIn("quality.evaluated", event_types)
            self.assertIn("policy.checked", event_types)
            self.assertGreaterEqual(len(director.memory.claim_edges(result.trace_id)), 1)
            director.memory.close()

    def test_journal_replay_reuses_completed_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["context engineering"])
            first = director.run(config, trace_id="trace_replay_test")
            second = director.run(config, trace_id="trace_replay_test")

            self.assertEqual(first.trace_id, second.trace_id)
            events = director.memory.events("trace_replay_test")
            self.assertTrue(any(event["event_type"] == "workflow.step.replayed" for event in events))
            director.memory.close()

    def test_policy_gate_blocks_absolute_gmv_claim(self) -> None:
        package = ArticlePackage(
            topic="Agent",
            titles=["title"],
            opening_hook="hook",
            outline=[],
            body_markdown="这个系统保证提升 GMV，必爆。",
            citations=[],
            commercial_angle="保证转化",
            cta="无需人工审核",
            trace_id="trace_test",
        )
        report = PolicyGate().review(package)

        self.assertEqual(report.overall_risk.value, "HIGH")
        self.assertFalse(report.approved_for_draft)

    def test_ai_flavor_detector_flags_template_language(self) -> None:
        text = "首先，我们需要多维度分析。其次，这具有重要意义。最后，综上所述，需要持续优化。"
        hits = detect_ai_flavor(text)

        self.assertGreaterEqual(len(hits), 4)

    def test_feedback_ingestor_persists_growth_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp) / "zhihuflow.sqlite3")
            ingestor = FeedbackIngestor(store)
            summary = ingestor.ingest(
                FeedbackEvent(
                    trace_id="trace_feedback",
                    article_id="zhihu_1",
                    views=1000,
                    likes=30,
                    favorites=20,
                    comments=5,
                    leads=4,
                    revenue_cents=19900,
                )
            )

            self.assertEqual(summary["engagement_rate"], 0.055)
            self.assertEqual(summary["lead_rate"], 0.004)
            events = store.events("trace_feedback")
            self.assertTrue(any(event["event_type"] == "feedback.ingested" for event in events))
            store.close()

    def test_sandbox_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = LocalSandbox(str(Path(tmp) / "sandbox"))
            artifact = sandbox.write_text("reports/a.md", "hello")

            self.assertEqual(artifact.relative_path, "reports/a.md")
            with self.assertRaises(SandboxViolation):
                sandbox.write_text("../escape.md", "bad")

    def test_scheduler_run_once_writes_outputs_without_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            scheduler = DailyScheduler(director, EmailDelivery(), output_dir=str(Path(tmp) / "scheduled"))
            result = scheduler.run_once(DirectorConfig(seeds=["context engineering"]), dry_run_email=True)

            self.assertTrue(Path(result.article_path).exists())
            self.assertTrue(Path(result.summary_path).exists())
            self.assertFalse(result.delivery.delivered)

    def test_web_console_settings_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state = WebConsoleState(
                WebConsoleConfig(
                    settings_path=str(tmp_path / "settings.json"),
                    history_path=str(tmp_path / "history.json"),
                    output_dir=str(tmp_path / "runs"),
                ),
                lambda offline: make_director(tmp_path),
            )
            settings = state.save_settings(
                {
                    "schedule_enabled": True,
                    "email_delivery_enabled": True,
                    "offline": True,
                    "daily_at": "08:30",
                    "seeds": "Agent memory\nAI coding agent",
                    "min_chars": 600,
                    "max_chars": 700,
                }
            )

            self.assertTrue(settings["schedule_enabled"])
            self.assertTrue(settings["email_delivery_enabled"])
            self.assertTrue(settings["offline"])
            self.assertEqual(settings["daily_at"], "08:30")
            self.assertEqual(settings["seeds"], ["Agent memory", "AI coding agent"])
            self.assertEqual(settings["min_chars"], 800)
            self.assertEqual(settings["max_chars"], 800)

    def test_web_console_reads_history_article_inside_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "runs"
            output_dir.mkdir()
            article_path = output_dir / "trace_demo.md"
            article_path.write_text("# demo", encoding="utf-8")
            history_path = tmp_path / "history.json"
            history_path.write_text(
                '[{"trace_id":"trace_demo","article_path":"' + str(article_path) + '"}]',
                encoding="utf-8",
            )
            state = WebConsoleState(
                WebConsoleConfig(
                    settings_path=str(tmp_path / "settings.json"),
                    history_path=str(history_path),
                    output_dir=str(output_dir),
                ),
                lambda offline: make_director(tmp_path),
            )

            self.assertEqual(state.article_text("trace_demo"), "# demo")


if __name__ == "__main__":
    unittest.main()
