from __future__ import annotations

from zhihuflow.app.config import DirectorConfig
from zhihuflow.core.schemas import ResearchBrief, ResearchClaim, TrendCard
from zhihuflow.research.sources import ResearchScout, dedupe_refs


class ResearchAgent:
    def __init__(self, scout: ResearchScout) -> None:
        self.scout = scout

    def build_brief(self, trend: TrendCard, config: DirectorConfig) -> ResearchBrief:
        queries = [
            trend.topic,
            " ".join(trend.keywords[:4]) or trend.topic,
            f"{trend.topic} evaluation architecture",
        ]
        refs = []
        seen: set[str] = set()
        for query in queries:
            for ref in self.scout.search(query, limit=config.max_sources):
                if ref.url not in seen:
                    seen.add(ref.url)
                    refs.append(ref)
        refs = dedupe_refs(trend.sources + refs)[: config.max_sources]
        evidence_ids = [ref.evidence_id for ref in refs[:4]]
        claims = [
            ResearchClaim(
                claim=f"{trend.topic} 的核心问题应先拆成概念边界、机制假设、评价方法和工程约束，而不是直接套用既有 Agent Workflow 叙事。",
                evidence_ids=evidence_ids,
                confidence=0.78 if evidence_ids else 0.45,
                status="supported" if evidence_ids else "unverified",
            ),
            ResearchClaim(
                claim=f"{trend.topic} 的写作重点应围绕为什么成立、在什么条件下失效、如何评估，而不是只做新闻转述或概念介绍。",
                evidence_ids=evidence_ids[:2],
                confidence=0.68 if evidence_ids else 0.4,
                status="supported" if evidence_ids else "unverified",
            ),
        ]
        return ResearchBrief(
            topic=trend.topic,
            why_now=trend.summary,
            audience=config.audience,
            search_queries=queries,
            sources=refs,
            claims=claims,
            contradictions=[],
            missing_context=[] if len(refs) >= 3 else ["真实来源不足，建议补充人工资料或开启网络检索。"],
        )
