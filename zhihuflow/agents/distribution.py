from __future__ import annotations

import re

from zhihuflow.core.schemas import ArticlePackage, DistributionPlan, EditorialReport, PolicyReport, QualityReport, RiskLevel


class DistributionAgent:
    """Prepare human-reviewed distribution assets without auto-publishing."""

    def prepare(
        self,
        article: ArticlePackage,
        quality: QualityReport,
        policy: PolicyReport,
        editorial: EditorialReport,
    ) -> DistributionPlan:
        title = article.titles[0] if article.titles else article.topic
        summary = _summary(article.body_markdown)
        risk_line = "低风险" if policy.overall_risk == RiskLevel.LOW else f"{policy.overall_risk.value} 风险，发布前需要复核"
        checklist = [
            "人工确认所有技术结论都有参考来源支撑。",
            "人工确认没有承诺收益、保证 GMV、自动发布或刷量表达。",
            "人工确认代码块和图表能被目标读者理解。",
            "人工确认标题没有夸大或制造焦虑。",
            f"质量分：{quality.overall_score:.2f}；风控：{risk_line}；编辑通过：{'是' if editorial.passed else '否'}。",
        ]
        if editorial.revision_suggestions:
            checklist.append("发布前处理编辑建议：" + "；".join(editorial.revision_suggestions[:2]))

        return DistributionPlan(
            zhihu_titles=article.titles[:3] or [title],
            zhihu_summary=summary,
            xiaohongshu_post=_xiaohongshu_post(article.topic, summary),
            social_post=_social_post(article.topic, quality.overall_score),
            cover_prompt=(
                "dark futuristic editorial cover, AI agent workflow dashboard, evidence graph, "
                "cyan and gold accents, clean Chinese tech blog visual, no text"
            ),
            review_checklist=checklist,
        )


def _summary(markdown: str, limit: int = 180) -> str:
    text = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text = re.sub(r"^# .*$", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^#{2,6}\s+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[[^\]]*]\([^)]*\)", "", text)
    text = re.sub(r"\[[^\]]+]\([^)]*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _xiaohongshu_post(topic: str, summary: str) -> str:
    return (
        f"卡文的时候，我现在更愿意把问题拆给 Agent 团队。\n\n"
        f"这次围绕「{topic}」，ZhihuFlow 会先找热点、整理证据、设计文章结构，再写初稿和做风控。\n"
        f"重点不是让 AI 乱写，而是把内容生产变成可复盘的工程系统。\n\n"
        f"{summary[:90]}…"
    )


def _social_post(topic: str, score: float) -> str:
    return (
        f"更新了一版 ZhihuFlow：把「{topic}」的内容生产拆成素材、架构、写作、编辑、风控和分发 Agent。"
        f"这篇草稿质量分 {score:.2f}，下一步会继续把复盘数据写回长期记忆。"
    )
