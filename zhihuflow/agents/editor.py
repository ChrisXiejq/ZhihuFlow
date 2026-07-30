from __future__ import annotations

import re

from zhihuflow.content.style import detect_ai_flavor
from zhihuflow.content.writer import _has_academic_depth_elements, _has_required_markdown_structure
from zhihuflow.core.schemas import ArticleBlueprint, ArticlePackage, EditorialReport


class EditorAgent:
    """Act like a chief editor: diagnose quality gaps without rewriting facts."""

    def review(self, article: ArticlePackage, blueprint: ArticleBlueprint) -> EditorialReport:
        body = article.body_markdown
        ai_hits = detect_ai_flavor(body)
        structure_notes: list[str] = []
        missing: list[str] = []
        suggestions: list[str] = []

        if not _has_required_markdown_structure(body):
            missing.append("markdown_structure")
            suggestions.append("补足 1 个一级标题和至少 4 个服务论证的二级标题。")
        if not _has_academic_depth_elements(body):
            missing.append("academic_depth")
            suggestions.append("补足概念边界、机制链条、适用条件、局限性和方法框架；代码和图表不是必需项。")
        if re.search(r"```(?:mermaid|plantuml)\n", body, flags=re.IGNORECASE):
            missing.append("unsupported_diagram")
            suggestions.append("删除 Mermaid/PlantUML 图表，改用文字或 Markdown 表格表达结构。")
        if "## 参考来源" in body or "ev_" in body:
            missing.append("public_internal_evidence")
            suggestions.append("删除正文里的参考来源区、evidence_id 和 URL，把证据留在内部 trace。")
        if blueprint.core_thesis[:18] not in body:
            structure_notes.append("正文没有明显承接文章蓝图中的核心论点。")
            suggestions.append("在开头或第二节明确写出核心 thesis，减少泛泛背景介绍。")
        if len(re.findall(r"^## ", body, flags=re.MULTILINE)) > 8:
            structure_notes.append("二级标题偏多，文章可能像报告目录。")
            suggestions.append("合并相邻章节，让结构围绕一条主线推进。")
        if ai_hits:
            suggestions.append("删除模板化连接词，把抽象判断改成具体场景或作者经验。")

        passed = not missing and len(ai_hits) <= 2
        if passed and not suggestions:
            suggestions.append("文章结构、学术深度和引用基础达标，可以进入风控与分发准备。")
        return EditorialReport(
            passed=passed,
            ai_flavor_hits=ai_hits,
            structure_notes=structure_notes,
            missing_elements=missing,
            revision_suggestions=suggestions,
        )
