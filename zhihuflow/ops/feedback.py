from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional

from zhihuflow.storage.longterm import LongTermMemory
from zhihuflow.storage.memory import MemoryStore
from zhihuflow.core.schemas import FeedbackEvent


class FeedbackIngestor:
    """Persist Zhihu performance signals and convert them into memory facts."""

    def __init__(self, store: MemoryStore, long_term_memory: Optional[LongTermMemory] = None) -> None:
        self.store = store
        self.long_term_memory = long_term_memory

    def ingest(self, event: FeedbackEvent) -> dict[str, Any]:
        ctr_proxy = (event.likes + event.favorites + event.comments) / max(1, event.views)
        lead_rate = event.leads / max(1, event.views)
        revenue_yuan = event.revenue_cents / 100
        summary = {
            "feedback_id": event.feedback_id,
            "trace_id": event.trace_id,
            "article_id": event.article_id,
            "engagement_rate": round(ctr_proxy, 4),
            "lead_rate": round(lead_rate, 4),
            "revenue_yuan": round(revenue_yuan, 2),
        }
        self.store.append_event(event.trace_id, "feedback.ingested", {**asdict(event), **summary})
        self.store.put_artifact(event.trace_id, "zhihu_feedback", event.article_id, {**asdict(event), **summary})
        if self.long_term_memory:
            self._remember(event, summary)
        return summary

    def _remember(self, event: FeedbackEvent, summary: dict[str, Any]) -> None:
        data = self.long_term_memory.read()
        data.setdefault("timeline", []).append(
            {
                "trace_id": event.trace_id,
                "summary": (
                    f"Zhihu feedback for {event.article_id}: "
                    f"engagement={summary['engagement_rate']}, leads={event.leads}, revenue_yuan={summary['revenue_yuan']}."
                ),
                "created_at": event.captured_at,
            }
        )
        profile = data.setdefault("profile", {})
        profile["last_zhihu_feedback"] = summary
        self.long_term_memory._write(data)
