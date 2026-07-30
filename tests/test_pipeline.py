from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zhihuflow.agents.architecture import ArchitectureAgent
from zhihuflow.agents.distribution import DistributionAgent
from zhihuflow.agents.editor import EditorAgent
from zhihuflow.agents.material import MaterialAgent
from zhihuflow.app.config import DirectorConfig
from zhihuflow.app.director import ContentDirector
from zhihuflow.content.policy import PolicyGate
from zhihuflow.content.style import detect_ai_flavor
from zhihuflow.content.writer import _has_academic_depth_elements, _word_count_zh
from zhihuflow.core.schemas import ArticlePackage, FeedbackEvent, SourceRef
from zhihuflow.ops.delivery import EmailDelivery
from zhihuflow.ops.feedback import FeedbackIngestor
from zhihuflow.ops.scheduler import DailyScheduler
from zhihuflow.research.agent import ResearchAgent
from zhihuflow.research.sources import ResearchScout, StaticSource, TrendScout, infer_topic, make_trend_card
from zhihuflow.research.subagents import ParallelResearchOrchestrator
from zhihuflow.runtime.context import ContextPacker
from zhihuflow.runtime.sandbox import LocalSandbox, SandboxViolation
from zhihuflow.runtime.skills import SkillRegistry
from zhihuflow.runtime.tools import build_default_tool_registry
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
            self.assertGreaterEqual(len(result.materials.cards), 1)
            self.assertGreaterEqual(len(result.blueprint.sections), 4)
            self.assertTrue(result.editorial.revision_suggestions)
            self.assertGreaterEqual(len(result.distribution.review_checklist), 4)
            self.assertTrue(result.article.body_markdown.startswith("# "))
            self.assertGreaterEqual(result.article.body_markdown.count("\n## "), 4)
            self.assertGreaterEqual(_word_count_zh(result.article.body_markdown), 1500)
            self.assertLessEqual(_word_count_zh(result.article.body_markdown), 2500)
            self.assertNotIn("## 参考来源", result.article.body_markdown)
            self.assertNotIn("ev_", result.article.body_markdown)
            self.assertNotIn("http://", result.article.body_markdown)
            self.assertNotIn("https://", result.article.body_markdown)
            self.assertNotIn("近期来源共同指向", result.article.body_markdown)
            self.assertNotIn("适合做成兼具技术解释和落地判断的知乎长文", result.article.body_markdown)
            self.assertNotIn("值得写的原因", result.article.body_markdown)
            self.assertNotIn("对知乎创作者来说", result.article.body_markdown)
            self.assertNotIn("```mermaid", result.article.body_markdown.lower())
            self.assertNotIn("```plantuml", result.article.body_markdown.lower())
            self.assertTrue(_has_academic_depth_elements(result.article.body_markdown))
            self.assertGreater(result.quality.overall_score, 0)
            self.assertTrue(result.policy.approved_for_draft)
            self.assertTrue(result.artifacts["article_markdown"].startswith("art_"))
            self.assertTrue(result.artifacts["quality_report"].startswith("art_"))

            events = director.memory.events(result.trace_id)
            event_types = [event["event_type"] for event in events]
            self.assertIn("workflow.started", event_types)
            self.assertIn("research.parallel.completed", event_types)
            self.assertIn("material_agent.completed", event_types)
            self.assertIn("architecture_agent.completed", event_types)
            self.assertIn("editor_agent.completed", event_types)
            self.assertIn("distribution_agent.completed", event_types)
            self.assertIn("claim_graph.updated", event_types)
            self.assertIn("quality.evaluated", event_types)
            self.assertIn("policy.checked", event_types)
            self.assertGreaterEqual(len(director.memory.claim_edges(result.trace_id)), 1)
            self.assertIn("material_board", result.artifacts)
            self.assertIn("article_blueprint", result.artifacts)
            self.assertIn("editorial_report", result.artifacts)
            self.assertIn("distribution_plan", result.artifacts)
            self.assertIn("context_pack", result.artifacts)
            self.assertIn("harness_report", result.artifacts)
            self.assertIn("progressive_skill_loading", result.harness.borrowed_patterns)
            self.assertIn("attachment_context_injection", result.harness.borrowed_patterns)
            self.assertGreaterEqual(len(result.harness.selected_skills), 3)
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
        text = "首先，我们需要多维度分析。其次，这具有重要意义。该话题由 2 条近期来源共同指向，适合做成知乎长文。对知乎创作者来说，这是值得写的原因。最后，综上所述，需要持续优化。"
        hits = detect_ai_flavor(text)

        self.assertGreaterEqual(len(hits), 4)

    def test_trend_summary_uses_reader_facing_language(self) -> None:
        refs = [
            SourceRef(title="Agent workflow orchestration and tool contracts", url="local://a", source="offline"),
            SourceRef(title="Agent workflow runtime observability", url="local://b", source="offline"),
        ]
        card = make_trend_card("Agent Workflow 编排正在替代单次 Prompt 工程", refs)

        self.assertNotIn("近期来源共同指向", card.summary)
        self.assertNotIn("适合做成", card.summary)
        self.assertIn("workflow", card.summary.lower())

    def test_dynamic_workflow_topic_is_not_collapsed_to_generic_workflow(self) -> None:
        topic = infer_topic("A runtime for dynamic workflow orchestration", "Dynamic Workflow")

        self.assertEqual(topic, "Dynamic Workflow 正在让 Agent 从固定流程走向运行时自适应编排")

    def test_explicit_seed_has_priority_over_source_title(self) -> None:
        topic = infer_topic("Agent workflow orchestration and tool contracts", "Agent Memory")

        self.assertEqual(topic, "Agent Memory 从向量库升级为可审计的组织记忆")

    def test_explicit_new_seed_is_preserved_without_topic_branch(self) -> None:
        topic = infer_topic("Agent workflow orchestration and tool contracts", "Multi Agent")

        self.assertEqual(topic, "Multi Agent")

    def test_explicit_product_seed_is_not_swallowed_by_coding_rule(self) -> None:
        topic = infer_topic("AI coding agent runtime", "Claude Code Agent Harness 设计优势")

        self.assertEqual(topic, "Claude Code Agent Harness 设计优势")

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

    def test_multi_agent_outputs_are_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["context engineering"])
            trend = director.trend_scout.discover(["context engineering"])[0]
            research = director.parallel_research.build_brief(trend, config.audience, config.max_sources)
            materials = MaterialAgent().build_board(trend, research)
            blueprint = ArchitectureAgent().design(trend, research, materials, config)
            article = director.writer.write(trend, research, "trace_agent_unit", config, blueprint, materials)
            editorial = EditorAgent().review(article, blueprint)
            quality = director.quality_evaluator.evaluate(article, research)
            policy = director.policy.review(article)
            distribution = DistributionAgent().prepare(article, quality, policy, editorial)

            self.assertGreaterEqual(len(materials.cards), 1)
            self.assertTrue(blueprint.code_plans)
            self.assertTrue(blueprint.diagram_plan)
            self.assertNotIn("mermaid", " ".join(element for section in blueprint.sections for element in section.required_elements).lower())
            self.assertTrue(editorial.revision_suggestions)
            self.assertTrue(distribution.zhihu_summary)
            self.assertTrue(distribution.review_checklist)
            director.memory.close()

    def test_article_blueprints_and_fallbacks_vary_by_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["dynamic workflow"])
            dynamic_trend = make_trend_card(
                "Dynamic Workflow 正在让 Agent 从固定流程走向运行时自适应编排",
                [SourceRef(title="Dynamic workflow runtime", url="local://dynamic", source="offline")],
            )
            memory_trend = make_trend_card(
                "Agent Memory 从向量库升级为可审计的组织记忆",
                [SourceRef(title="Agent memory governance", url="local://memory", source="offline")],
            )
            dynamic_research = director.parallel_research.build_brief(dynamic_trend, config.audience, config.max_sources)
            memory_research = director.parallel_research.build_brief(memory_trend, config.audience, config.max_sources)
            dynamic_materials = MaterialAgent().build_board(dynamic_trend, dynamic_research)
            memory_materials = MaterialAgent().build_board(memory_trend, memory_research)
            dynamic_blueprint = ArchitectureAgent().design(dynamic_trend, dynamic_research, dynamic_materials, config)
            memory_blueprint = ArchitectureAgent().design(memory_trend, memory_research, memory_materials, config)
            dynamic_article = director.writer.write(dynamic_trend, dynamic_research, "trace_dynamic", config, dynamic_blueprint, dynamic_materials)
            memory_article = director.writer.write(memory_trend, memory_research, "trace_memory", config, memory_blueprint, memory_materials)

            dynamic_headings = [line for line in dynamic_article.body_markdown.splitlines() if line.startswith("## ")]
            memory_headings = [line for line in memory_article.body_markdown.splitlines() if line.startswith("## ")]
            self.assertNotEqual(dynamic_blueprint.title_candidates[0], memory_blueprint.title_candidates[0])
            self.assertNotEqual(dynamic_headings[:4], memory_headings[:4])
            self.assertIn("Dynamic Workflow", dynamic_article.body_markdown)
            self.assertIn("Memory", memory_article.body_markdown)
            self.assertNotIn("```mermaid", dynamic_article.body_markdown.lower())
            self.assertNotIn("```mermaid", memory_article.body_markdown.lower())
            self.assertNotIn("我会怎么把它放进真实工程流程", memory_article.body_markdown)
            self.assertIn("从研究视角看，Memory 是状态更新问题", memory_article.body_markdown)
            self.assertIn("可撤销性", memory_article.body_markdown)
            self.assertNotIn("Dynamic Workflow 的价值，不是让流程图更复杂", memory_article.body_markdown)
            director.memory.close()

    def test_same_topic_fallback_can_vary_by_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["dynamic workflow"])
            trend = make_trend_card(
                "Dynamic Workflow 正在让 Agent 从固定流程走向运行时自适应编排",
                [SourceRef(title="Dynamic workflow runtime", url="local://dynamic", source="offline")],
            )
            research = director.parallel_research.build_brief(trend, config.audience, config.max_sources)
            materials = MaterialAgent().build_board(trend, research)
            blueprint = ArchitectureAgent().design(trend, research, materials, config)
            first = director.writer.write(trend, research, "trace_variant_a", config, blueprint, materials)
            second = director.writer.write(trend, research, "trace_variant_b", config, blueprint, materials)
            first_title = first.body_markdown.splitlines()[0]
            second_title = second.body_markdown.splitlines()[0]

            self.assertNotEqual(first_title, second_title)
            self.assertNotEqual(
                [line for line in first.body_markdown.splitlines() if line.startswith("## ")][:2],
                [line for line in second.body_markdown.splitlines() if line.startswith("## ")][:2],
            )
            director.memory.close()

    def test_generic_blueprint_does_not_reuse_dynamic_workflow_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["AI coding agent"])
            trend = make_trend_card(
                "AI Coding Agent 正在从工具调用进化到工程运行时",
                [SourceRef(title="AI coding agent runtime", url="local://coding", source="offline")],
            )
            research = director.parallel_research.build_brief(trend, config.audience, config.max_sources)
            materials = MaterialAgent().build_board(trend, research)
            blueprint = ArchitectureAgent().design(trend, research, materials, config)
            headings = [section.heading for section in blueprint.sections]

            self.assertIn("先定义问题边界", blueprint.title_candidates[0])
            self.assertNotIn("真正难的不是流程图", blueprint.title_candidates[0])
            self.assertNotIn("为什么固定流程开始不够用了", headings)
            self.assertTrue(any("AI Coding Agent" in heading for heading in headings))
            director.memory.close()

    def test_new_topic_fallback_does_not_reuse_workflow_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["Multi Agent"])
            trend = make_trend_card(
                "Multi Agent",
                [SourceRef(title="Multi-agent collaboration and evaluation", url="local://multi-agent", source="offline")],
            )
            research = director.parallel_research.build_brief(trend, config.audience, config.max_sources)
            materials = MaterialAgent().build_board(trend, research)
            blueprint = ArchitectureAgent().design(trend, research, materials, config)
            article = director.writer.write(trend, research, "trace_new_topic", config, blueprint, materials)
            headings = [line for line in article.body_markdown.splitlines() if line.startswith("## ")]

            self.assertIn("Multi Agent", article.body_markdown)
            self.assertTrue(_has_academic_depth_elements(article.body_markdown))
            self.assertNotIn("Dynamic Workflow", article.body_markdown)
            self.assertNotIn("Agent Workflow 编排正在替代单次 Prompt 工程", article.body_markdown)
            self.assertTrue(any("Multi Agent" in heading for heading in headings))
            director.memory.close()

    def test_skill_registry_selects_topic_playbooks_without_code_branch(self) -> None:
        registry = SkillRegistry()

        harness_skills = registry.select_for_topic("Claude Code 源码解析与 Agent Harness 工程")
        subagent_skills = registry.select_for_topic("如何设计 Coordinator + Specialist + Critic 的多 Agent 架构")

        self.assertIn("agent-harness-engineering", harness_skills)
        self.assertIn("subagent-orchestration", subagent_skills)
        self.assertIn("Skill Meta List", registry.attachment_for_topic("Claude Code", harness_skills))

    def test_context_packer_builds_attachments_and_microcompact_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["Claude Code Agent Harness"])
            trend = make_trend_card(
                "Claude Code Agent Harness 的工程设计",
                [SourceRef(title="Claude Code prompt caching and skills", url="local://claude-code", source="offline")],
            )
            research = director.parallel_research.build_brief(trend, config.audience, config.max_sources)
            materials = MaterialAgent().build_board(trend, research)
            blueprint = ArchitectureAgent().design(trend, research, materials, config)
            packer = ContextPacker(SkillRegistry(), build_default_tool_registry(), budget_chars=2500)
            pack = packer.build(trend, research, materials, blueprint)

            self.assertIn("agent-harness-engineering", pack.selected_skills)
            self.assertTrue(any(attachment.name == "skill_meta_list" for attachment in pack.attachments))
            self.assertTrue(any(attachment.name == "material_microcompact" for attachment in pack.attachments))
            self.assertLessEqual(pack.estimated_chars, pack.budget_chars + 800)
            director.memory.close()

    def test_harness_playbook_changes_fallback_argument(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            director = make_director(Path(tmp))
            config = DirectorConfig(seeds=["Claude Code Agent Harness 设计优势"])
            trend = make_trend_card(
                "Claude Code Agent Harness 设计优势",
                [SourceRef(title="Claude Code prompt caching and skills", url="local://claude-code", source="offline")],
            )
            research = director.parallel_research.build_brief(trend, config.audience, config.max_sources)
            materials = MaterialAgent().build_board(trend, research)
            blueprint = ArchitectureAgent().design(trend, research, materials, config)
            pack = ContextPacker(SkillRegistry(), build_default_tool_registry()).build(trend, research, materials, blueprint)
            article = director.writer.write(trend, research, "trace_harness_playbook", config, blueprint, materials, pack)

            self.assertIn("Agent Loop", article.body_markdown)
            self.assertIn("Context Pack", article.body_markdown)
            self.assertIn("Harness Report", article.body_markdown)
            self.assertNotRegex(article.body_markdown, r"Harnes(?!s)")
            director.memory.close()

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
