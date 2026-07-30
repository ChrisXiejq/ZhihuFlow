from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re


@dataclass
class Skill:
    name: str
    path: Path
    content: str
    description: str = ""
    tags: list[str] | None = None

    def brief(self, max_chars: int = 1200) -> str:
        text = self.content.strip()
        return text if len(text) <= max_chars else text[: max_chars - 3] + "..."

    def meta_line(self) -> str:
        tags = ", ".join(self.tags or [])
        suffix = f" tags={tags}" if tags else ""
        description = self.description or _first_heading_or_sentence(self.content)
        return f"- {self.name}: {description}{suffix}"


class SkillRegistry:
    """Progressive Markdown skill loader inspired by DeerFlow/Claude-style skills."""

    def __init__(self, roots: Optional[list[str]] = None) -> None:
        self.roots = [Path(root) for root in (roots or ["skills/builtin", "skills/custom"])]

    def list_names(self) -> list[str]:
        return [skill.name for skill in self.list_skills()]

    def list_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        for root in self.roots:
            if not root.exists():
                continue
            for path in sorted(root.glob("*/SKILL.md")):
                skills.append(_read_skill(path.parent.name, path))
        return skills

    def meta_brief(self, max_chars: int = 1800) -> str:
        lines = [skill.meta_line() for skill in self.list_skills()]
        text = "\n".join(lines)
        return text if len(text) <= max_chars else text[: max_chars - 3] + "..."

    def select_for_topic(self, topic: str, base: Optional[list[str]] = None, limit: int = 5) -> list[str]:
        selected: list[str] = []
        for name in base or ["zhihu-writing", "human-writing", "deep-research"]:
            if name in self.list_names() and name not in selected:
                selected.append(name)

        topic_tokens = _tokens(topic)
        scored: list[tuple[int, str]] = []
        for skill in self.list_skills():
            haystack = " ".join([skill.name, skill.description, " ".join(skill.tags or []), skill.content[:600]]).lower()
            score = sum(1 for token in topic_tokens if token and token in haystack)
            if score > 0 and skill.name not in selected:
                scored.append((score, skill.name))
        for _, name in sorted(scored, key=lambda item: (-item[0], item[1])):
            if len(selected) >= limit:
                break
            selected.append(name)
        return selected

    def load(self, name: str) -> Skill:
        for root in self.roots:
            path = root / name / "SKILL.md"
            if path.exists():
                return _read_skill(name, path)
        raise KeyError(f"skill not found: {name}")

    def load_many(self, names: list[str]) -> list[Skill]:
        return [self.load(name) for name in names]

    def attachment_for_topic(self, topic: str, selected: Optional[list[str]] = None) -> str:
        selected_names = selected or self.select_for_topic(topic)
        lines = [
            "<system-reminder>",
            "可用内容 Skills 采用渐进加载：先暴露 name/description，命中后才加载正文，避免固定模板污染所有主题。",
            "Skill Meta List:",
            self.meta_brief(),
            "",
            "本次已选择 Skills:",
            "\n".join(f"- {name}" for name in selected_names),
            "</system-reminder>",
        ]
        return "\n".join(lines)


def _read_skill(name: str, path: Path) -> Skill:
    content = path.read_text(encoding="utf-8")
    description = ""
    tags: list[str] = []
    frontmatter = re.match(r"^---\n([\s\S]*?)\n---\n", content)
    if frontmatter:
        for raw_line in frontmatter.group(1).splitlines():
            key, _, value = raw_line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip('"')
            if key == "description":
                description = value
            elif key == "tags":
                tags = [item.strip() for item in re.split(r"[, ]+", value) if item.strip()]
    if not description:
        description = _first_heading_or_sentence(content)
    return Skill(name=name, path=path, content=content, description=description, tags=tags)


def _first_heading_or_sentence(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip(" #")
        if stripped and not stripped.startswith("---") and ":" not in stripped[:20]:
            return stripped[:120]
    return "Markdown skill"


def _tokens(topic: str) -> list[str]:
    lowered = topic.lower()
    words = re.findall(r"[a-z][a-z0-9+-]{2,}", lowered)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", topic)
    normalized = {
        "multiagent": "multi-agent",
        "subagent": "sub-agent",
    }
    return [normalized.get(word, word) for word in words] + chinese
