from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from redflow.app.config import DirectorConfig
from redflow.app.director import ContentDirector
from redflow.core.schemas import to_jsonable
from redflow.ops.delivery import DeliveryResult, EmailDelivery


@dataclass
class ScheduledRunResult:
    trace_id: str
    article_path: str
    summary_path: str
    delivery: DeliveryResult


class DailyScheduler:
    def __init__(
        self,
        director: ContentDirector,
        delivery: EmailDelivery,
        output_dir: str = ".redflow/scheduled",
    ) -> None:
        self.director = director
        self.delivery = delivery
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_once(self, config: DirectorConfig, *, dry_run_email: bool = False) -> ScheduledRunResult:
        result = self.director.run(config)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        article_path = self.output_dir / f"{stamp}_{result.trace_id}.md"
        summary_path = self.output_dir / f"{stamp}_{result.trace_id}.json"
        article_path.write_text(result.article.body_markdown, encoding="utf-8")
        summary_path.write_text(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2), encoding="utf-8")
        delivery = self.delivery.send_files(
            f"RedFlow 知乎草稿：{result.article.titles[0]}",
            article_path,
            summary_path,
            dry_run=dry_run_email,
        )
        return ScheduledRunResult(
            trace_id=result.trace_id,
            article_path=str(article_path),
            summary_path=str(summary_path),
            delivery=delivery,
        )

    def run_forever(self, config: DirectorConfig, daily_at: str, *, dry_run_email: bool = False, poll_seconds: int = 30) -> None:
        while True:
            now = datetime.now()
            next_run = next_daily_time(now, daily_at)
            while datetime.now() < next_run:
                time.sleep(poll_seconds)
            self.run_once(config, dry_run_email=dry_run_email)
            time.sleep(max(1, poll_seconds))


def next_daily_time(now: datetime, daily_at: str) -> datetime:
    hour, minute = parse_hhmm(daily_at)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("time must be HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("time must be HH:MM")
    return hour, minute

