from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import unescape
from typing import Optional, Protocol

from redflow.core.schemas import SourceRef, TrendCard, utc_now


DEFAULT_SEEDS = [
    "LLM agent",
    "AI agent workflow",
    "context engineering",
    "RAG evaluation",
    "AI coding agent",
]


def _http_get(url: str, timeout: float = 8.0) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RedFlow/0.1 (+https://local.agent)",
            "Accept": "application/json,text/xml,text/html;q=0.8,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


class TrendSource(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[SourceRef]:
        ...


class ResearchSource(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[SourceRef]:
        ...


@dataclass
class HackerNewsSource:
    name: str = "hackernews"

    def search(self, query: str, limit: int = 10) -> list[SourceRef]:
        params = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": limit})
        payload = json.loads(_http_get(f"https://hn.algolia.com/api/v1/search_by_date?{params}"))
        refs: list[SourceRef] = []
        for hit in payload.get("hits", []):
            title = normalize_text(hit.get("title") or hit.get("story_title") or "")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if not title or not url:
                continue
            refs.append(
                SourceRef(
                    title=title,
                    url=url,
                    source=self.name,
                    published_at=hit.get("created_at"),
                    author=hit.get("author"),
                )
            )
        return refs


@dataclass
class ArxivSource:
    name: str = "arxiv"

    def search(self, query: str, limit: int = 10) -> list[SourceRef]:
        params = urllib.parse.urlencode(
            {
                "search_query": f'all:"{query}"',
                "start": 0,
                "max_results": limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        xml = _http_get(f"https://export.arxiv.org/api/query?{params}")
        root = ET.fromstring(xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        refs: list[SourceRef] = []
        for entry in root.findall("atom:entry", ns):
            title = normalize_text(entry.findtext("atom:title", default="", namespaces=ns))
            url = entry.findtext("atom:id", default="", namespaces=ns)
            published_at = entry.findtext("atom:published", default="", namespaces=ns) or None
            authors = [normalize_text(a.findtext("atom:name", default="", namespaces=ns)) for a in entry.findall("atom:author", ns)]
            if title and url:
                refs.append(SourceRef(title=title, url=url, source=self.name, published_at=published_at, author=", ".join(authors[:3])))
        time.sleep(0.35)
        return refs


@dataclass
class StaticSource:
    name: str
    refs: list[SourceRef]

    def search(self, query: str, limit: int = 10) -> list[SourceRef]:
        tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", query)}
        scored: list[tuple[int, SourceRef]] = []
        for ref in self.refs:
            haystack = f"{ref.title} {ref.source}".lower()
            score = sum(1 for token in tokens if token in haystack)
            scored.append((score, ref))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [ref for _, ref in scored[:limit]]


class TrendScout:
    def __init__(self, sources: Optional[list[TrendSource]] = None) -> None:
        self.sources = sources or [HackerNewsSource(), ArxivSource()]

    def discover(self, seeds: Optional[list[str]] = None, limit_per_seed: int = 6) -> list[TrendCard]:
        seeds = seeds or DEFAULT_SEEDS
        buckets: dict[str, list[SourceRef]] = {}
        for seed in seeds:
            for source in self.sources:
                try:
                    refs = source.search(seed, limit_per_seed)
                except Exception:
                    refs = []
                for ref in refs:
                    topic = infer_topic(ref.title, seed)
                    buckets.setdefault(topic, []).append(ref)
        if not buckets:
            return fallback_trends()
        cards = [make_trend_card(topic, refs) for topic, refs in buckets.items()]
        cards.sort(key=lambda c: (c.heat_score + c.technical_depth_score + c.zhihu_fit_score + c.gmv_fit_score - c.risk_score), reverse=True)
        return cards


class ResearchScout:
    def __init__(self, sources: Optional[list[ResearchSource]] = None) -> None:
        self.sources = sources or [ArxivSource(), HackerNewsSource()]

    def search(self, query: str, limit: int = 8) -> list[SourceRef]:
        refs: list[SourceRef] = []
        seen: set[str] = set()
        for source in self.sources:
            try:
                found = source.search(query, limit)
            except Exception:
                found = []
            for ref in found:
                key = ref.url.lower()
                if key not in seen:
                    seen.add(key)
                    refs.append(ref)
        return refs[:limit]


def infer_topic(title: str, seed: str) -> str:
    lowered = title.lower()
    if "context" in lowered and ("agent" in lowered or "llm" in lowered):
        return "Context Engineering 正在成为 Agent 系统的新基础设施"
    if "rag" in lowered and ("agent" in lowered or "evaluation" in lowered):
        return "Agentic RAG 从检索增强走向可评测工作流"
    if "coding" in lowered or "code agent" in lowered:
        return "AI Coding Agent 正在从工具调用进化到工程运行时"
    if "workflow" in lowered or "orchestration" in lowered:
        return "Agent Workflow 编排正在替代单次 Prompt 工程"
    if "memory" in lowered:
        return "Agent Memory 从向量库升级为可审计的组织记忆"
    return f"{seed} 的前沿趋势：{title[:52]}"


def make_trend_card(topic: str, refs: list[SourceRef]) -> TrendCard:
    unique_refs = dedupe_refs(refs)[:8]
    keywords = sorted({kw for ref in unique_refs for kw in extract_keywords(ref.title)})[:8]
    heat = min(1.0, math.log(len(refs) + 1, 8))
    technical_depth = 0.35 + 0.08 * sum(1 for ref in unique_refs if ref.source in {"arxiv", "hackernews"})
    zhihu_fit = 0.55 + (0.15 if any(k in topic.lower() for k in ["agent", "context", "rag", "coding"]) else 0.0)
    gmv_fit = 0.45 + (0.2 if any(k in topic.lower() for k in ["coding", "workflow", "memory"]) else 0.1)
    risk = 0.18 if "自动" in topic or "agent" in topic.lower() else 0.1
    return TrendCard(
        topic=topic,
        summary=f"该话题由 {len(unique_refs)} 条近期来源共同指向，适合做成兼具技术解释和落地判断的知乎长文。",
        keywords=keywords,
        sources=unique_refs,
        heat_score=round(min(heat, 1.0), 3),
        technical_depth_score=round(min(technical_depth, 1.0), 3),
        zhihu_fit_score=round(min(zhihu_fit, 1.0), 3),
        gmv_fit_score=round(min(gmv_fit, 1.0), 3),
        risk_score=round(risk, 3),
        captured_at=utc_now(),
    )


def dedupe_refs(refs: list[SourceRef]) -> list[SourceRef]:
    seen: set[str] = set()
    unique: list[SourceRef] = []
    for ref in refs:
        key = (ref.url or ref.title).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    return unique


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text)
    stop = {"the", "and", "for", "with", "from", "into", "using", "based", "towards"}
    return [w for w in words if w.lower() not in stop][:6]


def fallback_trends() -> list[TrendCard]:
    refs = [
        SourceRef(
            title="Agent systems need event logs, memory, and tool contracts",
            url="local://fallback/agent-runtime",
            source="redflow-fixture",
            published_at=utc_now(),
        ),
        SourceRef(
            title="Context engineering becomes a practical bottleneck for long-horizon agents",
            url="local://fallback/context-engineering",
            source="redflow-fixture",
            published_at=utc_now(),
        ),
    ]
    return [make_trend_card("Context Engineering 正在成为 Agent 系统的新基础设施", refs)]
