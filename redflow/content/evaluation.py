from __future__ import annotations

import re

from redflow.core.schemas import ArticlePackage, QualityMetric, QualityReport, ResearchBrief
from redflow.content.style import detect_ai_flavor


class QualityEvaluator:
    """Deterministic quality checks used as a regression guard for content output."""

    def evaluate(self, article: ArticlePackage, research: ResearchBrief) -> QualityReport:
        body = article.body_markdown
        metrics = [
            self._evidence_metric(article, research),
            self._human_voice_metric(body),
            self._specificity_metric(body),
            self._commercial_metric(article),
            self._structure_metric(body),
        ]
        overall = round(sum(metric.score for metric in metrics) / len(metrics), 3)
        recommendations = [metric.rationale for metric in metrics if metric.score < 0.72]
        return QualityReport(overall_score=overall, metrics=metrics, recommendations=recommendations)

    def _evidence_metric(self, article: ArticlePackage, research: ResearchBrief) -> QualityMetric:
        citation_count = len(article.citations)
        supported_claims = sum(1 for claim in research.claims if claim.evidence_ids)
        score = min(1.0, citation_count / 6 * 0.55 + supported_claims / max(1, len(research.claims)) * 0.45)
        return QualityMetric("evidence", round(score, 3), f"引用 {citation_count} 个来源，{supported_claims}/{len(research.claims)} 个 claim 有证据。")

    def _human_voice_metric(self, body: str) -> QualityMetric:
        hits = detect_ai_flavor(body)
        first_person = len(re.findall(r"我认为|我更|我会|我不太|我见过", body))
        scene_markers = len(re.findall(r"项目|团队|代码|trace|日志|评审|上线|复盘|用户", body, flags=re.IGNORECASE))
        score = max(0.0, 1.0 - len(hits) * 0.12)
        score = min(1.0, score + min(0.18, first_person * 0.04) + min(0.18, scene_markers * 0.015))
        return QualityMetric("human_voice", round(score, 3), f"AI 模板命中 {len(hits)} 个，第一人称判断 {first_person} 处，场景词 {scene_markers} 处。")

    def _specificity_metric(self, body: str) -> QualityMetric:
        concrete = len(re.findall(r"event log|claim|trace|workflow|sandbox|memory|tool|schema|评测|证据|引用", body, flags=re.IGNORECASE))
        paragraphs = max(1, len([chunk for chunk in body.split("\n\n") if chunk.strip()]))
        score = min(1.0, concrete / max(5, paragraphs) * 0.9)
        return QualityMetric("specificity", round(score, 3), f"具体技术词 {concrete} 个，段落 {paragraphs} 个。")

    def _commercial_metric(self, article: ArticlePackage) -> QualityMetric:
        text = article.body_markdown + article.commercial_angle + article.cta
        risky = len(re.findall(r"保证|稳赚|必爆|躺赚|百分百|刷赞|刷评论", text))
        has_soft_cta = 1 if article.cta and "保证" not in article.cta else 0
        score = max(0.0, 0.85 + has_soft_cta * 0.15 - risky * 0.35)
        return QualityMetric("commercial_safety", round(min(1.0, score), 3), f"高风险商业词 {risky} 个，soft CTA={'yes' if has_soft_cta else 'no'}。")

    def _structure_metric(self, body: str) -> QualityMetric:
        heading_count = len(re.findall(r"^#{1,3} ", body, flags=re.MULTILINE))
        length = len(body)
        score = 0.55
        if 3 <= heading_count <= 9:
            score += 0.25
        if 1800 <= length <= 9000:
            score += 0.2
        return QualityMetric("structure", round(min(1.0, score), 3), f"标题 {heading_count} 个，正文 {length} 字符。")
