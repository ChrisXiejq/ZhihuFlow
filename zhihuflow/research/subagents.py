from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from zhihuflow.core.schemas import ResearchBrief, ResearchClaim, SourceRef, TrendCard
from zhihuflow.research.sources import ResearchScout, dedupe_refs


@dataclass
class ResearchPerspective:
    name: str
    query_suffix: str
    claim_template: str


DEFAULT_RESEARCH_PERSPECTIVES = [
    ResearchPerspective(
        name="papers",
        query_suffix="paper benchmark architecture evaluation",
        claim_template="{topic} 的论文脉络重点在可评测、可复现和长任务可靠性。",
    ),
    ResearchPerspective(
        name="engineering",
        query_suffix="engineering system runtime memory tool calling",
        claim_template="{topic} 的工程难点通常不在单次调用，而在运行时、工具契约和状态恢复。",
    ),
    ResearchPerspective(
        name="community",
        query_suffix="developer discussion adoption pain points",
        claim_template="{topic} 的社区讨论能暴露真实使用门槛和反直觉失败案例。",
    ),
    ResearchPerspective(
        name="business",
        query_suffix="product monetization creator workflow",
        claim_template="{topic} 只有转化成可信内容资产和可交付服务时，才可能支撑 GMV。",
    ),
]


class ParallelResearchOrchestrator:
    """Run isolated research perspectives and merge them into one brief."""

    def __init__(self, scout: ResearchScout, max_workers: int = 4) -> None:
        self.scout = scout
        self.max_workers = max_workers

    def build_brief(
        self,
        trend: TrendCard,
        audience: str,
        max_sources: int,
        perspectives: list[ResearchPerspective] | None = None,
    ) -> ResearchBrief:
        perspectives = perspectives or DEFAULT_RESEARCH_PERSPECTIVES
        refs_by_perspective: dict[str, list[SourceRef]] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(perspectives))) as pool:
            futures = {
                pool.submit(self.scout.search, f"{trend.topic} {perspective.query_suffix}", max(2, max_sources // 2)): perspective
                for perspective in perspectives
            }
            for future in as_completed(futures):
                perspective = futures[future]
                try:
                    refs_by_perspective[perspective.name] = future.result()
                except Exception:
                    refs_by_perspective[perspective.name] = []

        merged_refs = dedupe_refs(trend.sources + [ref for refs in refs_by_perspective.values() for ref in refs])[:max_sources]
        evidence_ids = [ref.evidence_id for ref in merged_refs]
        claims = [
            ResearchClaim(
                claim=perspective.claim_template.format(topic=trend.topic),
                evidence_ids=evidence_ids[: max(1, min(3, len(evidence_ids)))],
                confidence=0.72 if evidence_ids else 0.38,
                status="supported" if evidence_ids else "unverified",
            )
            for perspective in perspectives
        ]
        missing = [name for name, refs in refs_by_perspective.items() if not refs]
        contradictions = []
        if len(merged_refs) < 3:
            contradictions.append("公开来源不足，当前结论应降级为选题假设。")
        return ResearchBrief(
            topic=trend.topic,
            why_now=trend.summary,
            audience=audience,
            search_queries=[f"{trend.topic} {perspective.query_suffix}" for perspective in perspectives],
            sources=merged_refs,
            claims=claims,
            contradictions=contradictions,
            missing_context=[f"{name} perspective returned no sources" for name in missing],
        )
