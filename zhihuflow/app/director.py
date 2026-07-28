from __future__ import annotations

from typing import Any, Optional

from zhihuflow.agents.architecture import ArchitectureAgent
from zhihuflow.agents.distribution import DistributionAgent
from zhihuflow.agents.editor import EditorAgent
from zhihuflow.agents.material import MaterialAgent
from zhihuflow.app.config import DirectorConfig
from zhihuflow.content.evaluation import QualityEvaluator
from zhihuflow.content.policy import PolicyGate
from zhihuflow.content.writer import ZhihuWriter
from zhihuflow.core.schemas import (
    AgentRunResult,
    ArticleBlueprint,
    ArticlePackage,
    ArticleSectionPlan,
    DistributionPlan,
    EditorialReport,
    MaterialBoard,
    MaterialCard,
    PolicyFinding,
    PolicyReport,
    QualityMetric,
    QualityReport,
    ResearchBrief,
    ResearchClaim,
    RiskLevel,
    SourceRef,
    TrendCard,
    to_jsonable,
)
from zhihuflow.core.workflow import JournaledWorkflow, RuntimeContext
from zhihuflow.research.agent import ResearchAgent
from zhihuflow.research.sources import ResearchScout, TrendScout
from zhihuflow.research.subagents import ParallelResearchOrchestrator
from zhihuflow.runtime.middleware import ContextBudgetMiddleware, MiddlewareChain, ToolRiskMiddleware
from zhihuflow.runtime.skills import SkillRegistry
from zhihuflow.runtime.tools import ToolRegistry, build_default_tool_registry
from zhihuflow.storage.longterm import LongTermMemory
from zhihuflow.storage.memory import MemoryStore


class ContentDirector:
    def __init__(
        self,
        memory: MemoryStore,
        trend_scout: Optional[TrendScout] = None,
        research_agent: Optional[ResearchAgent] = None,
        writer: Optional[ZhihuWriter] = None,
        policy: Optional[PolicyGate] = None,
        quality_evaluator: Optional[QualityEvaluator] = None,
        skill_registry: Optional[SkillRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        long_term_memory: Optional[LongTermMemory] = None,
        parallel_research: Optional[ParallelResearchOrchestrator] = None,
        material_agent: Optional[MaterialAgent] = None,
        architecture_agent: Optional[ArchitectureAgent] = None,
        editor_agent: Optional[EditorAgent] = None,
        distribution_agent: Optional[DistributionAgent] = None,
    ) -> None:
        self.memory = memory
        self.skill_registry = skill_registry or SkillRegistry()
        self.tool_registry = tool_registry or build_default_tool_registry()
        self.long_term_memory = long_term_memory
        self.trend_scout = trend_scout or TrendScout()
        self.research_agent = research_agent or ResearchAgent(ResearchScout())
        self.parallel_research = parallel_research or ParallelResearchOrchestrator(ResearchScout())
        self.writer = writer or ZhihuWriter(None, self.skill_registry, self.tool_registry, self.long_term_memory)
        self.policy = policy or PolicyGate(self.skill_registry)
        self.quality_evaluator = quality_evaluator or QualityEvaluator()
        self.material_agent = material_agent or MaterialAgent()
        self.architecture_agent = architecture_agent or ArchitectureAgent()
        self.editor_agent = editor_agent or EditorAgent()
        self.distribution_agent = distribution_agent or DistributionAgent()

    def run(self, config: DirectorConfig, trace_id: Optional[str] = None) -> AgentRunResult:
        middleware = MiddlewareChain(
            [
                ContextBudgetMiddleware(),
                ToolRiskMiddleware(self.tool_registry.contracts()),
            ]
        )
        workflow = JournaledWorkflow(memory=self.memory, trace_id=trace_id, middleware=middleware)
        workflow.add_step("discover_trends", lambda ctx, state: self._discover(ctx, config))
        workflow.add_step("choose_trend", lambda ctx, state: self._choose(ctx, state["discover_trends"]))
        workflow.add_step("research", lambda ctx, state: self._research(ctx, _trend_from_payload(state["choose_trend"]), config))
        workflow.add_step(
            "build_material_board",
            lambda ctx, state: self._materials(
                ctx,
                _trend_from_payload(state["choose_trend"]),
                _research_from_payload(state["research"]),
            ),
        )
        workflow.add_step(
            "design_article_blueprint",
            lambda ctx, state: self._blueprint(
                ctx,
                _trend_from_payload(state["choose_trend"]),
                _research_from_payload(state["research"]),
                _materials_from_payload(state["build_material_board"]),
                config,
            ),
        )
        workflow.add_step(
            "write_article",
            lambda ctx, state: self._write(
                ctx,
                _trend_from_payload(state["choose_trend"]),
                _research_from_payload(state["research"]),
                config,
                _blueprint_from_payload(state["design_article_blueprint"]),
                _materials_from_payload(state["build_material_board"]),
            ),
        )
        workflow.add_step(
            "edit_article",
            lambda ctx, state: self._edit(
                ctx,
                _article_from_payload(state["write_article"]),
                _blueprint_from_payload(state["design_article_blueprint"]),
            ),
        )
        workflow.add_step(
            "evaluate_quality",
            lambda ctx, state: self._quality(
                ctx,
                _article_from_payload(state["write_article"]),
                _research_from_payload(state["research"]),
            ),
        )
        workflow.add_step("policy_check", lambda ctx, state: self._policy(ctx, _article_from_payload(state["write_article"])))
        workflow.add_step(
            "prepare_distribution",
            lambda ctx, state: self._distribution(
                ctx,
                _article_from_payload(state["write_article"]),
                _quality_from_payload(state["evaluate_quality"]),
                _policy_from_payload(state["policy_check"]),
                _editorial_from_payload(state["edit_article"]),
            ),
        )
        state = workflow.run({"config": to_jsonable(config)})
        trend = _trend_from_payload(state["choose_trend"])
        research = _research_from_payload(state["research"])
        materials = _materials_from_payload(state["build_material_board"])
        blueprint = _blueprint_from_payload(state["design_article_blueprint"])
        article = _article_from_payload(state["write_article"])
        editorial = _editorial_from_payload(state["edit_article"])
        quality = _quality_from_payload(state["evaluate_quality"])
        policy = _policy_from_payload(state["policy_check"])
        distribution = _distribution_from_payload(state["prepare_distribution"])
        artifacts = {artifact.kind: artifact.artifact_id for artifact in self.memory.artifacts(workflow.trace_id)}
        if self.long_term_memory:
            self.long_term_memory.remember_run(article.topic, workflow.trace_id, policy.overall_risk.value, len(research.sources))
        return AgentRunResult(
            trace_id=workflow.trace_id,
            trend=trend,
            research=research,
            materials=materials,
            blueprint=blueprint,
            article=article,
            editorial=editorial,
            quality=quality,
            policy=policy,
            distribution=distribution,
            artifacts=artifacts,
        )

    def _discover(self, ctx: RuntimeContext, config: DirectorConfig) -> list[dict[str, Any]]:
        cards = self.trend_scout.discover(config.seeds)
        ctx.event("trend.discovered", {"count": len(cards)})
        return [to_jsonable(card) for card in cards]

    def _choose(self, ctx: RuntimeContext, cards: list[dict[str, Any]]) -> dict[str, Any]:
        def score(card: dict[str, Any]) -> float:
            return (
                float(card["heat_score"]) * 0.22
                + float(card["technical_depth_score"]) * 0.28
                + float(card["zhihu_fit_score"]) * 0.25
                + float(card["gmv_fit_score"]) * 0.2
                - float(card["risk_score"]) * 0.15
            )

        chosen = max(cards, key=score)
        ctx.event("trend.chosen", {"trend_id": chosen["trend_id"], "topic": chosen["topic"], "score": round(score(chosen), 3)})
        return chosen

    def _research(self, ctx: RuntimeContext, trend: TrendCard, config: DirectorConfig) -> dict[str, Any]:
        if config.parallel_research:
            self.parallel_research.max_workers = config.research_workers
            brief = self.parallel_research.build_brief(trend=trend, audience=config.audience, max_sources=config.max_sources)
            ctx.event("research.parallel.completed", {"workers": config.research_workers, "queries": len(brief.search_queries)})
        else:
            brief = self.research_agent.build_brief(trend, config)
        self.memory.put_claims(ctx.trace_id, "research", brief.topic, brief.claims)
        self.memory.put_claim_graph(ctx.trace_id, brief.claims)
        self.memory.put_artifact(ctx.trace_id, "research_brief", brief.topic, brief)
        ctx.event("research.completed", {"sources": len(brief.sources), "claims": len(brief.claims)})
        return to_jsonable(brief)

    def _materials(self, ctx: RuntimeContext, trend: TrendCard, research: ResearchBrief) -> dict[str, Any]:
        board = self.material_agent.build_board(trend, research)
        self.memory.put_artifact(ctx.trace_id, "material_board", board.topic, board)
        ctx.event("material_agent.completed", {"cards": len(board.cards), "gaps": len(board.gaps)})
        return to_jsonable(board)

    def _blueprint(self, ctx: RuntimeContext, trend: TrendCard, research: ResearchBrief, materials: MaterialBoard, config: DirectorConfig) -> dict[str, Any]:
        blueprint = self.architecture_agent.design(trend, research, materials, config)
        self.memory.put_artifact(ctx.trace_id, "article_blueprint", blueprint.topic, blueprint)
        ctx.event("architecture_agent.completed", {"sections": len(blueprint.sections), "titles": len(blueprint.title_candidates)})
        return to_jsonable(blueprint)

    def _write(
        self,
        ctx: RuntimeContext,
        trend: TrendCard,
        research: ResearchBrief,
        config: DirectorConfig,
        blueprint: ArticleBlueprint,
        materials: MaterialBoard,
    ) -> dict[str, Any]:
        article = self.writer.write(trend, research, ctx.trace_id, config, blueprint=blueprint, materials=materials)
        self.memory.put_artifact(ctx.trace_id, "article_markdown", article.titles[0], article)
        ctx.event("article.created", {"package_id": article.package_id, "title": article.titles[0], "model": self.writer.model.model_id})
        return to_jsonable(article)

    def _edit(self, ctx: RuntimeContext, article: ArticlePackage, blueprint: ArticleBlueprint) -> dict[str, Any]:
        report = self.editor_agent.review(article, blueprint)
        self.memory.put_artifact(ctx.trace_id, "editorial_report", article.topic, report)
        ctx.event("editor_agent.completed", {"passed": report.passed, "missing": report.missing_elements})
        return to_jsonable(report)

    def _quality(self, ctx: RuntimeContext, article: ArticlePackage, research: ResearchBrief) -> dict[str, Any]:
        report = self.quality_evaluator.evaluate(article, research)
        self.memory.put_artifact(ctx.trace_id, "quality_report", article.topic, report)
        ctx.event("quality.evaluated", {"score": report.overall_score, "metrics": [metric.name for metric in report.metrics]})
        return to_jsonable(report)

    def _policy(self, ctx: RuntimeContext, article: ArticlePackage) -> dict[str, Any]:
        report = self.policy.review(article)
        self.memory.put_artifact(ctx.trace_id, "policy_report", article.topic, report)
        ctx.event("policy.checked", {"risk": report.overall_risk.value, "findings": len(report.findings)})
        return to_jsonable(report)

    def _distribution(
        self,
        ctx: RuntimeContext,
        article: ArticlePackage,
        quality: QualityReport,
        policy: PolicyReport,
        editorial: EditorialReport,
    ) -> dict[str, Any]:
        plan = self.distribution_agent.prepare(article, quality, policy, editorial)
        self.memory.put_artifact(ctx.trace_id, "distribution_plan", article.topic, plan)
        ctx.event("distribution_agent.completed", {"titles": len(plan.zhihu_titles), "checklist": len(plan.review_checklist)})
        return to_jsonable(plan)


def _source_from_payload(payload: dict[str, Any]) -> SourceRef:
    return SourceRef(**payload)


def _trend_from_payload(payload: dict[str, Any]) -> TrendCard:
    data = dict(payload)
    data["sources"] = [_source_from_payload(ref) for ref in data.get("sources", [])]
    return TrendCard(**data)


def _claim_from_payload(payload: dict[str, Any]) -> ResearchClaim:
    return ResearchClaim(**payload)


def _research_from_payload(payload: dict[str, Any]) -> ResearchBrief:
    data = dict(payload)
    data["sources"] = [_source_from_payload(ref) for ref in data.get("sources", [])]
    data["claims"] = [_claim_from_payload(claim) for claim in data.get("claims", [])]
    return ResearchBrief(**data)


def _material_card_from_payload(payload: dict[str, Any]) -> MaterialCard:
    return MaterialCard(**payload)


def _materials_from_payload(payload: dict[str, Any]) -> MaterialBoard:
    data = dict(payload)
    data["cards"] = [_material_card_from_payload(card) for card in data.get("cards", [])]
    return MaterialBoard(**data)


def _section_plan_from_payload(payload: dict[str, Any]) -> ArticleSectionPlan:
    return ArticleSectionPlan(**payload)


def _blueprint_from_payload(payload: dict[str, Any]) -> ArticleBlueprint:
    data = dict(payload)
    data["sections"] = [_section_plan_from_payload(section) for section in data.get("sections", [])]
    return ArticleBlueprint(**data)


def _article_from_payload(payload: dict[str, Any]) -> ArticlePackage:
    data = dict(payload)
    data["citations"] = [_source_from_payload(ref) for ref in data.get("citations", [])]
    return ArticlePackage(**data)


def _editorial_from_payload(payload: dict[str, Any]) -> EditorialReport:
    return EditorialReport(**payload)


def _policy_from_payload(payload: dict[str, Any]) -> PolicyReport:
    findings = [PolicyFinding(code=f["code"], message=f["message"], severity=RiskLevel(f["severity"]), evidence=f.get("evidence")) for f in payload.get("findings", [])]
    return PolicyReport(overall_risk=RiskLevel(payload["overall_risk"]), findings=findings, approved_for_draft=bool(payload["approved_for_draft"]), policy_version=payload.get("policy_version", "content-policy-v1"))


def _quality_from_payload(payload: dict[str, Any]) -> QualityReport:
    metrics = [QualityMetric(name=m["name"], score=float(m["score"]), rationale=m["rationale"]) for m in payload.get("metrics", [])]
    return QualityReport(
        overall_score=float(payload["overall_score"]),
        metrics=metrics,
        recommendations=list(payload.get("recommendations", [])),
        evaluator_version=payload.get("evaluator_version", "quality-eval-v1"),
    )


def _distribution_from_payload(payload: dict[str, Any]) -> DistributionPlan:
    return DistributionPlan(**payload)
