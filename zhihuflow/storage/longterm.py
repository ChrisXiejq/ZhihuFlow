from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zhihuflow.core.schemas import new_id, utc_now


@dataclass
class MemoryFact:
    text: str
    tags: list[str]
    confidence: float
    created_at: str = field(default_factory=utc_now)
    fact_id: str = field(default_factory=lambda: new_id("fact"))


class LongTermMemory:
    """Local memory.json with DeerFlow-like profile, timeline, and fact blocks."""

    def __init__(self, path: str = ".zhihuflow/memory.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"profile": {}, "timeline": [], "facts": []})

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def briefing(self, max_facts: int = 8) -> str:
        data = self.read()
        profile = data.get("profile", {})
        timeline = data.get("timeline", [])[-5:]
        facts = data.get("facts", [])[-max_facts:]
        chunks = ["Long-term memory:"]
        if profile:
            chunks.append(f"- profile: {json.dumps(profile, ensure_ascii=False)}")
        for item in timeline:
            chunks.append(f"- timeline: {item.get('summary', '')}")
        for fact in facts:
            chunks.append(f"- fact[{fact.get('confidence', 0)}]: {fact.get('text', '')}")
        return "\n".join(chunks)

    def remember_run(self, topic: str, trace_id: str, policy_risk: str, source_count: int) -> None:
        data = self.read()
        data.setdefault("timeline", []).append(
            {
                "trace_id": trace_id,
                "summary": f"Generated Zhihu draft for '{topic}' with {source_count} sources; policy risk={policy_risk}.",
                "created_at": utc_now(),
            }
        )
        self._upsert_fact(
            data,
            MemoryFact(
                text="User is building ZhihuFlow as both a real Zhihu GMV content system and a job-search portfolio project.",
                tags=["user_goal", "zhihuflow", "portfolio"],
                confidence=0.92,
            ),
        )
        self._write(data)

    def _upsert_fact(self, data: dict[str, Any], fact: MemoryFact) -> None:
        facts = data.setdefault("facts", [])
        for existing in facts:
            if existing.get("text") == fact.text:
                existing["confidence"] = max(float(existing.get("confidence", 0)), fact.confidence)
                existing["created_at"] = fact.created_at
                return
        facts.append(
            {
                "fact_id": fact.fact_id,
                "text": fact.text,
                "tags": fact.tags,
                "confidence": fact.confidence,
                "created_at": fact.created_at,
            }
        )

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
