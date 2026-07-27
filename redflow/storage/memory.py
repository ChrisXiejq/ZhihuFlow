from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from redflow.core.schemas import new_id, to_jsonable, utc_now


SCHEMA = """
create table if not exists event_log (
  id integer primary key autoincrement,
  trace_id text not null,
  event_type text not null,
  payload_json text not null,
  created_at text not null
);

create table if not exists artifacts (
  artifact_id text primary key,
  trace_id text not null,
  kind text not null,
  title text not null,
  payload_json text not null,
  created_at text not null
);

create table if not exists workflow_journal (
  trace_id text not null,
  step_name text not null,
  status text not null,
  payload_json text not null,
  created_at text not null,
  primary key (trace_id, step_name)
);

create table if not exists memory_claims (
  claim_id text primary key,
  trace_id text not null,
  kind text not null,
  subject text not null,
  payload_json text not null,
  confidence real not null,
  status text not null,
  created_at text not null
);

create table if not exists claim_edges (
  edge_id text primary key,
  trace_id text not null,
  source_id text not null,
  target_id text not null,
  relation text not null,
  weight real not null,
  created_at text not null
);
"""


@dataclass
class StoredArtifact:
    artifact_id: str
    trace_id: str
    kind: str
    title: str
    payload: dict[str, Any]


class MemoryStore:
    """SQLite-backed event log and lightweight memory substrate."""

    def __init__(self, db_path: Union[str, Path] = ".redflow/redflow.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def append_event(self, trace_id: str, event_type: str, payload: Any) -> None:
        self._conn.execute(
            "insert into event_log(trace_id, event_type, payload_json, created_at) values (?, ?, ?, ?)",
            (trace_id, event_type, json.dumps(to_jsonable(payload), ensure_ascii=False), utc_now()),
        )
        self._conn.commit()

    def events(self, trace_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "select event_type, payload_json, created_at from event_log where trace_id = ? order by id",
            (trace_id,),
        ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def put_artifact(self, trace_id: str, kind: str, title: str, payload: Any) -> str:
        artifact_id = new_id("art")
        self._conn.execute(
            """
            insert into artifacts(artifact_id, trace_id, kind, title, payload_json, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                trace_id,
                kind,
                title,
                json.dumps(to_jsonable(payload), ensure_ascii=False),
                utc_now(),
            ),
        )
        self._conn.commit()
        self.append_event(trace_id, "artifact.created", {"artifact_id": artifact_id, "kind": kind, "title": title})
        return artifact_id

    def artifacts(self, trace_id: str) -> list[StoredArtifact]:
        rows = self._conn.execute(
            "select artifact_id, trace_id, kind, title, payload_json from artifacts where trace_id = ? order by created_at",
            (trace_id,),
        ).fetchall()
        return [
            StoredArtifact(
                artifact_id=row["artifact_id"],
                trace_id=row["trace_id"],
                kind=row["kind"],
                title=row["title"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def journal_get(self, trace_id: str, step_name: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute(
            "select status, payload_json from workflow_journal where trace_id = ? and step_name = ?",
            (trace_id, step_name),
        ).fetchone()
        if row is None or row["status"] != "completed":
            return None
        return json.loads(row["payload_json"])

    def journal_put(self, trace_id: str, step_name: str, payload: Any) -> None:
        self._conn.execute(
            """
            insert into workflow_journal(trace_id, step_name, status, payload_json, created_at)
            values (?, ?, 'completed', ?, ?)
            on conflict(trace_id, step_name) do update set
              status = excluded.status,
              payload_json = excluded.payload_json,
              created_at = excluded.created_at
            """,
            (trace_id, step_name, json.dumps(to_jsonable(payload), ensure_ascii=False), utc_now()),
        )
        self._conn.commit()
        self.append_event(trace_id, "workflow.step.completed", {"step": step_name})

    def put_claims(self, trace_id: str, kind: str, subject: str, claims: Iterable[Any]) -> None:
        for claim in claims:
            payload = to_jsonable(claim)
            claim_id = payload.get("claim_id", new_id("claim"))
            confidence = float(payload.get("confidence", 0.0))
            status = str(payload.get("status", "unverified"))
            self._conn.execute(
                """
                insert or replace into memory_claims(
                  claim_id, trace_id, kind, subject, payload_json, confidence, status, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_id,
                    trace_id,
                    kind,
                    subject,
                    json.dumps(payload, ensure_ascii=False),
                    confidence,
                    status,
                    utc_now(),
                ),
            )
        self._conn.commit()

    def put_claim_graph(self, trace_id: str, claims: Iterable[Any]) -> None:
        for claim in claims:
            payload = to_jsonable(claim)
            claim_id = payload.get("claim_id", new_id("claim"))
            confidence = float(payload.get("confidence", 0.0))
            for evidence_id in payload.get("evidence_ids", []):
                self._conn.execute(
                    """
                    insert or replace into claim_edges(edge_id, trace_id, source_id, target_id, relation, weight, created_at)
                    values (?, ?, ?, ?, 'supports', ?, ?)
                    """,
                    (
                        f"{trace_id}:{evidence_id}:{claim_id}",
                        trace_id,
                        evidence_id,
                        claim_id,
                        confidence,
                        utc_now(),
                    ),
                )
        self._conn.commit()
        self.append_event(trace_id, "claim_graph.updated", {"trace_id": trace_id})

    def claims(self, trace_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            select claim_id, kind, subject, payload_json, confidence, status, created_at
            from memory_claims where trace_id = ? order by created_at
            """,
            (trace_id,),
        ).fetchall()
        return [
            {
                "claim_id": row["claim_id"],
                "kind": row["kind"],
                "subject": row["subject"],
                "payload": json.loads(row["payload_json"]),
                "confidence": row["confidence"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def claim_edges(self, trace_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            select edge_id, source_id, target_id, relation, weight, created_at
            from claim_edges where trace_id = ? order by created_at
            """,
            (trace_id,),
        ).fetchall()
        return [
            {
                "edge_id": row["edge_id"],
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "relation": row["relation"],
                "weight": row["weight"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def context_briefing(self, trace_id: str, max_events: int = 12) -> str:
        rows = self._conn.execute(
            "select event_type, payload_json from event_log where trace_id = ? order by id desc limit ?",
            (trace_id, max_events),
        ).fetchall()
        chunks: list[str] = []
        for row in reversed(rows):
            payload = json.loads(row["payload_json"])
            compact = json.dumps(payload, ensure_ascii=False)
            if len(compact) > 280:
                compact = compact[:277] + "..."
            chunks.append(f"- {row['event_type']}: {compact}")
        return "\n".join(chunks)
