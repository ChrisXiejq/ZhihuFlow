from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DirectorConfig:
    seeds: list[str]
    audience: str = "关注 AI、LLM、Agent、求职和生产力工具的知乎读者"
    commercial_goal: str = "提升知乎账号专业信任与后续咨询/课程/工具转化"
    max_sources: int = 10
    parallel_research: bool = True
    research_workers: int = 4
    target_min_chars: int = 1500
    target_max_chars: int = 2500

