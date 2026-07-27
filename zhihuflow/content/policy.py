from __future__ import annotations

import re
from typing import Optional

from zhihuflow.core.schemas import ArticlePackage, PolicyFinding, PolicyReport, RiskLevel
from zhihuflow.content.style import detect_ai_flavor
from zhihuflow.runtime.skills import SkillRegistry


class PolicyGate:
    def __init__(self, skill_registry: Optional[SkillRegistry] = None) -> None:
        self.skill_registry = skill_registry or SkillRegistry()

    banned_patterns = [
        (re.compile(r"保证|稳赚|必爆|躺赚|百分百"), "overclaim", "存在绝对化或收益保证表达"),
        (re.compile(r"无需人工审核|全自动发布"), "unsafe_automation", "发布链路不能移除人工审核"),
        (re.compile(r"爬取私密|绕过验证码|刷赞|刷评论"), "platform_abuse", "涉及平台规避或虚假互动"),
    ]

    def review(self, package: ArticlePackage) -> PolicyReport:
        findings: list[PolicyFinding] = []
        text = "\n".join([package.body_markdown, package.commercial_angle, package.cta])
        for pattern, code, message in self.banned_patterns:
            if pattern.search(text):
                findings.append(PolicyFinding(code=code, message=message, severity=RiskLevel.HIGH))
        if len(package.citations) < 2:
            findings.append(PolicyFinding(code="weak_evidence", message="引用来源不足，建议补充至少 2 个公开来源。", severity=RiskLevel.MEDIUM))
        if "参考来源" not in package.body_markdown:
            findings.append(PolicyFinding(code="missing_citations", message="正文缺少参考来源区。", severity=RiskLevel.MEDIUM))
        ai_flavor_hits = detect_ai_flavor(package.body_markdown)
        if len(ai_flavor_hits) >= 4:
            findings.append(
                PolicyFinding(
                    code="ai_flavor",
                    message=f"检测到明显 AI 模板表达：{', '.join(ai_flavor_hits[:6])}",
                    severity=RiskLevel.MEDIUM,
                )
            )
        if any(f.severity == RiskLevel.HIGH for f in findings):
            risk = RiskLevel.HIGH
        elif findings:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW
        return PolicyReport(overall_risk=risk, findings=findings, approved_for_draft=risk != RiskLevel.HIGH)

