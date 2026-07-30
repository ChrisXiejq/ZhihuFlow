from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zhihuflow.core.schemas import (
    ArticleBlueprint,
    ContextPack,
    MaterialBoard,
    ResearchBrief,
    RuntimeAttachment,
    TrendCard,
    to_jsonable,
)
from zhihuflow.runtime.skills import SkillRegistry
from zhihuflow.runtime.tools import ToolRegistry


@dataclass
class ContextPacker:
    """Claude-Code-inspired dynamic context assembly for content runs.

    The model should see stable instructions first and dynamic evidence later.
    Large, replayable tool outputs are summarized into pointers instead of being
    copied wholesale into every writing prompt.
    """

    skill_registry: SkillRegistry
    tool_registry: ToolRegistry
    budget_chars: int = 9000
    skill_body_chars: int = 900
    material_chars: int = 2600

    def build(
        self,
        trend: TrendCard,
        research: ResearchBrief,
        materials: MaterialBoard,
        blueprint: ArticleBlueprint | None = None,
    ) -> ContextPack:
        selected_skills = self.skill_registry.select_for_topic(trend.topic)
        attachments = [
            RuntimeAttachment(
                name="skill_meta_list",
                content=self.skill_registry.attachment_for_topic(trend.topic, selected_skills),
                source="skill_registry",
                priority=10,
            ),
            RuntimeAttachment(
                name="selected_skill_bodies",
                content=self._skill_bodies(selected_skills),
                source="skill_registry",
                priority=20,
            ),
            RuntimeAttachment(
                name="tool_contract_summary",
                content=self._tool_contracts(),
                source="tool_registry",
                priority=40,
            ),
            RuntimeAttachment(
                name="research_claim_pack",
                content=self._research_pack(research),
                source="research_brief",
                priority=50,
            ),
            RuntimeAttachment(
                name="material_microcompact",
                content=self._material_pack(materials),
                source="material_board",
                priority=60,
            ),
        ]
        if blueprint:
            attachments.append(
                RuntimeAttachment(
                    name="article_blueprint_pack",
                    content=self._blueprint_pack(blueprint),
                    source="architecture_agent",
                    priority=30,
                )
            )
        estimated = sum(len(item.content) for item in attachments)
        offloaded_items: list[str] = []
        if estimated > self.budget_chars:
            attachments, offloaded_items = self._compact_attachments(attachments)
            estimated = sum(len(item.content) for item in attachments)
        return ContextPack(
            topic=trend.topic,
            attachments=sorted(attachments, key=lambda item: item.priority),
            selected_skills=selected_skills,
            offloaded_items=offloaded_items,
            budget_chars=self.budget_chars,
            estimated_chars=estimated,
        )

    def _skill_bodies(self, selected_skills: list[str]) -> str:
        chunks: list[str] = []
        for skill in self.skill_registry.load_many(selected_skills):
            chunks.append(f"## {skill.name}\n\n{skill.brief(self.skill_body_chars)}")
        return "\n\n".join(chunks)

    def _tool_contracts(self) -> str:
        lines = []
        for contract in self.tool_registry.contracts():
            lines.append(f"- {contract['name']} risk={contract['risk']}: {contract['description']}")
        return "\n".join(lines)

    def _research_pack(self, research: ResearchBrief) -> str:
        claim_lines = []
        for claim in research.claims[:8]:
            claim_lines.append(f"- {claim.claim} confidence={claim.confidence} status={claim.status}")
        contradiction_lines = [f"- {item}" for item in research.contradictions[:4]]
        missing_lines = [f"- {item}" for item in research.missing_context[:4]]
        return "\n".join(
            [
                f"topic: {research.topic}",
                f"why_now: {research.why_now}",
                "claims:",
                "\n".join(claim_lines),
                "contradictions:",
                "\n".join(contradiction_lines) or "- none",
                "missing_context:",
                "\n".join(missing_lines) or "- none",
            ]
        )

    def _material_pack(self, materials: MaterialBoard) -> str:
        lines = [f"topic: {materials.topic}", "cards:"]
        used = 0
        for card in materials.cards:
            item = f"- {card.title} [{card.material_type}] confidence={card.confidence}: {card.summary}"
            if used + len(item) > self.material_chars:
                break
            lines.append(item)
            used += len(item)
        if len(materials.cards) > len(lines) - 2:
            lines.append(f"- offloaded {len(materials.cards) - (len(lines) - 2)} lower-priority material cards; retrieve from material_board artifact if needed.")
        if materials.gaps:
            lines.append("gaps:")
            lines.extend(f"- {gap}" for gap in materials.gaps[:4])
        return "\n".join(lines)

    def _blueprint_pack(self, blueprint: ArticleBlueprint) -> str:
        sections = "\n".join(f"- {section.heading}: {section.purpose}" for section in blueprint.sections)
        return "\n".join(
            [
                f"core_thesis: {blueprint.core_thesis}",
                f"opening_strategy: {blueprint.opening_strategy}",
                "sections:",
                sections,
                f"table_plan: {blueprint.table_plan}",
                f"analogy: {blueprint.analogy}",
                f"discussion_question: {blueprint.discussion_question}",
            ]
        )

    def _compact_attachments(self, attachments: list[RuntimeAttachment]) -> tuple[list[RuntimeAttachment], list[str]]:
        compacted: list[RuntimeAttachment] = []
        offloaded: list[str] = []
        remaining = self.budget_chars
        for attachment in sorted(attachments, key=lambda item: item.priority):
            if len(attachment.content) <= remaining:
                compacted.append(attachment)
                remaining -= len(attachment.content)
                continue
            excerpt = attachment.content[: max(200, remaining // 2)].rstrip()
            compacted.append(
                RuntimeAttachment(
                    name=attachment.name,
                    content=excerpt + "\n[content compacted; full data remains in workflow artifact]",
                    source=attachment.source,
                    priority=attachment.priority,
                )
            )
            offloaded.append(attachment.name)
            remaining = max(0, remaining - len(compacted[-1].content))
        return compacted, offloaded


def context_pack_to_prompt(pack: ContextPack) -> str:
    sections = []
    for attachment in pack.attachments:
        sections.append(f"### {attachment.name} ({attachment.source})\n{attachment.content}")
    return "\n\n".join(sections)


def context_pack_summary(pack: ContextPack) -> dict[str, Any]:
    return {
        "pack_id": pack.pack_id,
        "selected_skills": pack.selected_skills,
        "attachments": [attachment.name for attachment in pack.attachments],
        "budget_chars": pack.budget_chars,
        "estimated_chars": pack.estimated_chars,
        "offloaded_items": pack.offloaded_items,
        "json": to_jsonable(pack),
    }
