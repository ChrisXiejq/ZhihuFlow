from __future__ import annotations

from zhihuflow.core.schemas import MaterialBoard, MaterialCard, ResearchBrief, TrendCard


class MaterialAgent:
    """Turn research output into writing-ready material cards."""

    def build_board(self, trend: TrendCard, research: ResearchBrief) -> MaterialBoard:
        cards: list[MaterialCard] = []
        clusters: dict[str, list[str]] = {
            "evidence": [],
            "implementation": [],
            "counterpoint": [],
            "risk": [],
        }
        for claim in research.claims:
            material_type = _claim_type(claim.claim)
            card = MaterialCard(
                title=_shorten(claim.claim, 34),
                summary=claim.claim,
                material_type=material_type,
                evidence_ids=list(claim.evidence_ids),
                use_case=_use_case_for(material_type),
                confidence=claim.confidence,
                risk_note="" if claim.status == "supported" else "该素材证据较弱，写作时需要降级表达。",
            )
            cards.append(card)
            clusters.setdefault(material_type, []).append(card.card_id)

        for ref in research.sources[:6]:
            card = MaterialCard(
                title=ref.title,
                summary=f"来自 {ref.source} 的可引用来源：{ref.title}",
                material_type="evidence",
                evidence_ids=[ref.evidence_id],
                use_case="用于支撑趋势背景、技术事实或参考来源列表。",
                confidence=0.72,
            )
            cards.append(card)
            clusters["evidence"].append(card.card_id)

        gaps = list(research.missing_context)
        if len(research.sources) < 3:
            gaps.append("公开来源不足，建议人工补充论文、官方文档或社区讨论。")
        if not cards:
            gaps.append("没有可用素材卡片，写作前应补充研究。")

        return MaterialBoard(topic=trend.topic, cards=cards, clusters=clusters, gaps=gaps)


def _claim_type(claim: str) -> str:
    if any(word in claim for word in ["风险", "不足", "失败", "门槛"]):
        return "risk"
    if any(word in claim for word in ["工程", "运行时", "工具", "状态", "架构"]):
        return "implementation"
    if any(word in claim for word in ["反例", "争议", "不确定"]):
        return "counterpoint"
    return "evidence"


def _use_case_for(material_type: str) -> str:
    mapping = {
        "evidence": "用于论证为什么这个选题现在值得写。",
        "implementation": "用于解释系统架构、代码示例或工程取舍。",
        "counterpoint": "用于补充不同立场，避免文章过度单边。",
        "risk": "用于风险边界和人工审核章节。",
    }
    return mapping.get(material_type, "用于支持正文论证。")


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
