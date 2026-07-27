from __future__ import annotations

import json
import mimetypes
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import unquote, urlparse

from zhihuflow.app.config import DirectorConfig
from zhihuflow.app.director import ContentDirector
from zhihuflow.core.schemas import to_jsonable
from zhihuflow.models.providers import load_env_file
from zhihuflow.ops.delivery import EmailDelivery
from zhihuflow.ops.scheduler import DailyScheduler, parse_hhmm


DEFAULT_SEEDS = ["LLM agent", "context engineering", "AI coding agent", "Agentic RAG"]


@dataclass
class WebConsoleConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    settings_path: str = ".zhihuflow/web_settings.json"
    history_path: str = ".zhihuflow/web_history.json"
    output_dir: str = ".zhihuflow/web_runs"
    env_file: Optional[str] = None
    poll_seconds: int = 20


class WebConsoleState:
    def __init__(self, config: WebConsoleConfig, director_factory: Callable[[bool], ContentDirector]) -> None:
        self.config = config
        self.director_factory = director_factory
        self.settings_path = Path(config.settings_path)
        self.history_path = Path(config.history_path)
        self.output_dir = Path(config.output_dir)
        self.static_dir = Path(__file__).with_name("static")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._job_lock = threading.Lock()
        self._current_job: dict[str, Any] = {"status": "idle"}
        self._last_schedule_date: Optional[str] = None
        self._stop = threading.Event()
        if config.env_file:
            load_env_file(config.env_file)

    def load_settings(self) -> dict[str, Any]:
        default = {
            "schedule_enabled": False,
            "email_delivery_enabled": False,
            "offline": False,
            "daily_at": "09:00",
            "seeds": DEFAULT_SEEDS,
            "min_chars": 1500,
            "max_chars": 2500,
        }
        if not self.settings_path.exists():
            return default
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
        merged = {**default, **raw}
        try:
            return self._normalize_settings(merged)
        except (TypeError, ValueError):
            return default

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_settings()
        merged = {**current, **payload}
        normalized = self._normalize_settings(merged)
        self.settings_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        return normalized

    def status(self) -> dict[str, Any]:
        settings = self.load_settings()
        return {
            "app": "ZhihuFlow",
            "now": datetime.now().isoformat(timespec="seconds"),
            "settings": settings,
            "email_configured": EmailDelivery().configured(),
            "current_job": self._current_job,
            "history_count": len(self.history()),
        }

    def history(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if self.history_path.exists():
            try:
                records = json.loads(self.history_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                records = []
        records = [record for record in records if isinstance(record, dict)]
        records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return records

    def article_text(self, trace_id: str) -> str:
        for record in self.history():
            if record.get("trace_id") == trace_id:
                article_path = Path(str(record.get("article_path", ""))).resolve()
                if not self._is_inside(article_path, self.output_dir.resolve()):
                    raise FileNotFoundError("article path is outside output directory")
                return article_path.read_text(encoding="utf-8")
        raise FileNotFoundError(trace_id)

    def run_async(self, *, reason: str = "manual") -> dict[str, Any]:
        with self._job_lock:
            if self._current_job.get("status") == "running":
                return self._current_job
            job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._current_job = {"job_id": job_id, "status": "running", "reason": reason, "started_at": datetime.now().isoformat(timespec="seconds")}
            thread = threading.Thread(target=self._run_job, args=(job_id, reason), daemon=True)
            thread.start()
            return self._current_job

    def start_scheduler(self) -> None:
        thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _scheduler_loop(self) -> None:
        while not self._stop.is_set():
            settings = self.load_settings()
            if settings["schedule_enabled"]:
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                hour, minute = parse_hhmm(settings["daily_at"])
                if now.hour == hour and now.minute >= minute and self._last_schedule_date != today:
                    self._last_schedule_date = today
                    self.run_async(reason="schedule")
            self._stop.wait(self.config.poll_seconds)

    def _run_job(self, job_id: str, reason: str) -> None:
        director: Optional[ContentDirector] = None
        try:
            settings = self.load_settings()
            director = self.director_factory(bool(settings["offline"]))
            scheduler = DailyScheduler(director, EmailDelivery(), output_dir=str(self.output_dir))
            result = scheduler.run_once(
                DirectorConfig(
                    seeds=list(settings["seeds"]),
                    target_min_chars=int(settings["min_chars"]),
                    target_max_chars=int(settings["max_chars"]),
                ),
                dry_run_email=not bool(settings["email_delivery_enabled"]),
            )
            record = self._record_from_result(result, reason)
            self._append_history(record)
            self._current_job = {
                "job_id": job_id,
                "status": "completed",
                "reason": reason,
                "trace_id": result.trace_id,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
            }
        except Exception as exc:  # pragma: no cover - surfaced through UI.
            self._current_job = {
                "job_id": job_id,
                "status": "failed",
                "reason": reason,
                "error": str(exc),
                "finished_at": datetime.now().isoformat(timespec="seconds"),
            }
        finally:
            if director is not None:
                director.memory.close()

    def _record_from_result(self, result: Any, reason: str) -> dict[str, Any]:
        summary_path = Path(result.summary_path)
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        article = payload.get("article", {})
        quality = payload.get("quality", {})
        policy = payload.get("policy", {})
        return {
            "trace_id": result.trace_id,
            "title": (article.get("titles") or ["未命名文章"])[0],
            "topic": article.get("topic", ""),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "article_path": result.article_path,
            "summary_path": result.summary_path,
            "quality": quality.get("overall_score"),
            "risk": policy.get("overall_risk"),
            "delivered": result.delivery.delivered,
            "delivery_message": result.delivery.message,
        }

    def _append_history(self, record: dict[str, Any]) -> None:
        with self._lock:
            records = self.history()
            records.insert(0, record)
            self.history_path.write_text(json.dumps(records[:200], ensure_ascii=False, indent=2), encoding="utf-8")

    def _normalize_settings(self, raw: dict[str, Any]) -> dict[str, Any]:
        seeds_raw = raw.get("seeds", DEFAULT_SEEDS)
        if isinstance(seeds_raw, str):
            seeds = [item.strip() for item in seeds_raw.replace("\n", ",").split(",") if item.strip()]
        else:
            seeds = [str(item).strip() for item in seeds_raw if str(item).strip()]
        if not seeds:
            seeds = DEFAULT_SEEDS
        daily_at = str(raw.get("daily_at", "09:00"))
        parse_hhmm(daily_at)
        min_chars = max(800, int(raw.get("min_chars", 1500)))
        max_chars = max(min_chars, int(raw.get("max_chars", 2500)))
        return {
            "schedule_enabled": bool(raw.get("schedule_enabled", False)),
            "email_delivery_enabled": bool(raw.get("email_delivery_enabled", False)),
            "offline": bool(raw.get("offline", False)),
            "daily_at": daily_at,
            "seeds": seeds[:12],
            "min_chars": min_chars,
            "max_chars": max_chars,
        }

    @staticmethod
    def _is_inside(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False


class ZhihuFlowRequestHandler(BaseHTTPRequestHandler):
    state: WebConsoleState

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._send_json(self.state.status())
            return
        if parsed.path == "/api/settings":
            self._send_json(self.state.load_settings())
            return
        if parsed.path == "/api/history":
            self._send_json(self.state.history())
            return
        if parsed.path.startswith("/api/articles/"):
            trace_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                self._send_text(self.state.article_text(trace_id), "text/markdown; charset=utf-8")
            except FileNotFoundError:
                self._send_json({"error": "article not found"}, HTTPStatus.NOT_FOUND)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/settings":
            try:
                payload = self._read_json()
                self._send_json(self.state.save_settings(payload))
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/run":
            self._send_json(self.state.run_async(reason="manual"), HTTPStatus.ACCEPTED)
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _serve_static(self, route: str) -> None:
        if route in ("", "/"):
            target = self.state.static_dir / "index.html"
        else:
            relative = route.lstrip("/")
            target = (self.state.static_dir / relative).resolve()
            if not WebConsoleState._is_inside(target, self.state.static_dir.resolve()):
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
        if not target.exists() or not target.is_file():
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text: str, content_type: str) -> None:
        data = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_web_console(config: WebConsoleConfig, director_factory: Callable[[bool], ContentDirector]) -> None:
    state = WebConsoleState(config, director_factory)
    state.start_scheduler()

    class Handler(ZhihuFlowRequestHandler):
        pass

    Handler.state = state
    server = ThreadingHTTPServer((config.host, config.port), Handler)
    print(f"ZhihuFlow Web Console: http://{config.host}:{config.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop()
        server.server_close()
