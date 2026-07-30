from __future__ import annotations

import re


AI_FLAVOR_PATTERNS = [
    r"首先[，,]",
    r"其次[，,]",
    r"再次[，,]",
    r"最后[，,]",
    r"综上所述",
    r"值得注意的是",
    r"需要指出的是",
    r"让我们",
    r"赋能",
    r"形成闭环",
    r"多维度",
    r"持续优化",
    r"具有重要意义",
    r"该话题由\s*\d+\s*条近期来源共同指向",
    r"适合做成.*?知乎长文",
    r"近期来源共同指向",
    r"值得写的原因",
    r"对知乎创作者来说",
]


def detect_ai_flavor(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in AI_FLAVOR_PATTERNS:
        if re.search(pattern, text):
            hits.append(pattern)
    return hits


def strip_model_meta(text: str) -> str:
    lines = []
    skip_prefixes = ("原文分析", "优化策略", "优化说明", "自检", "以下是", "好的，")
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in skip_prefixes):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
