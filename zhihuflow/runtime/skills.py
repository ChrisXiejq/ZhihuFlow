from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Skill:
    name: str
    path: Path
    content: str

    def brief(self, max_chars: int = 1200) -> str:
        text = self.content.strip()
        return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


class SkillRegistry:
    """Progressive Markdown skill loader inspired by DeerFlow/Claude-style skills."""

    def __init__(self, roots: Optional[list[str]] = None) -> None:
        self.roots = [Path(root) for root in (roots or ["skills/builtin", "skills/custom"])]

    def list_names(self) -> list[str]:
        names: list[str] = []
        for root in self.roots:
            if not root.exists():
                continue
            for path in sorted(root.glob("*/SKILL.md")):
                names.append(path.parent.name)
        return names

    def load(self, name: str) -> Skill:
        for root in self.roots:
            path = root / name / "SKILL.md"
            if path.exists():
                return Skill(name=name, path=path, content=path.read_text(encoding="utf-8"))
        raise KeyError(f"skill not found: {name}")

    def load_many(self, names: list[str]) -> list[Skill]:
        return [self.load(name) for name in names]
