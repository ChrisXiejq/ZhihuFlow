from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class SourceRef:
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    author: Optional[str] = None
    evidence_id: str = field(default_factory=lambda: new_id("ev"))


@dataclass
class TrendCard:
    topic: str
    summary: str
    keywords: list[str]
    sources: list[SourceRef]
    heat_score: float
    technical_depth_score: float
    zhihu_fit_score: float
    gmv_fit_score: float
    risk_score: float
    captured_at: str = field(default_factory=utc_now)
    trend_id: str = field(default_factory=lambda: new_id("trend"))


@dataclass
class ResearchClaim:
    claim: str
    evidence_ids: list[str]
    confidence: float
    status: str = "unverified"
    claim_id: str = field(default_factory=lambda: new_id("claim"))


@dataclass
class ResearchBrief:
    topic: str
    why_now: str
    audience: str
    search_queries: list[str]
    sources: list[SourceRef]
    claims: list[ResearchClaim]
    contradictions: list[str]
    missing_context: list[str]
    brief_id: str = field(default_factory=lambda: new_id("brief"))


@dataclass
class MaterialCard:
    title: str
    summary: str
    material_type: str
    evidence_ids: list[str]
    use_case: str
    confidence: float
    risk_note: str = ""
    card_id: str = field(default_factory=lambda: new_id("mat"))


@dataclass
class MaterialBoard:
    topic: str
    cards: list[MaterialCard]
    clusters: dict[str, list[str]]
    gaps: list[str]
    board_id: str = field(default_factory=lambda: new_id("board"))


@dataclass
class ArticleSectionPlan:
    heading: str
    purpose: str
    material_card_ids: list[str]
    required_elements: list[str] = field(default_factory=list)
    section_id: str = field(default_factory=lambda: new_id("section"))


@dataclass
class ArticleBlueprint:
    topic: str
    title_candidates: list[str]
    core_thesis: str
    opening_strategy: str
    sections: list[ArticleSectionPlan]
    code_plans: list[str]
    diagram_plan: str
    table_plan: str
    analogy: str
    cta: str
    discussion_question: str
    blueprint_id: str = field(default_factory=lambda: new_id("blueprint"))


@dataclass
class ArticlePackage:
    topic: str
    titles: list[str]
    opening_hook: str
    outline: list[str]
    body_markdown: str
    citations: list[SourceRef]
    commercial_angle: str
    cta: str
    trace_id: str
    package_id: str = field(default_factory=lambda: new_id("pkg"))


@dataclass
class EditorialReport:
    passed: bool
    ai_flavor_hits: list[str]
    structure_notes: list[str]
    missing_elements: list[str]
    revision_suggestions: list[str]
    editor_version: str = "editor-agent-v1"
    report_id: str = field(default_factory=lambda: new_id("edit"))


@dataclass
class PolicyFinding:
    code: str
    message: str
    severity: RiskLevel
    evidence: Optional[str] = None


@dataclass
class PolicyReport:
    overall_risk: RiskLevel
    findings: list[PolicyFinding]
    approved_for_draft: bool
    policy_version: str = "content-policy-v1"


@dataclass
class QualityMetric:
    name: str
    score: float
    rationale: str


@dataclass
class QualityReport:
    overall_score: float
    metrics: list[QualityMetric]
    recommendations: list[str]
    evaluator_version: str = "quality-eval-v1"


@dataclass
class DistributionPlan:
    zhihu_titles: list[str]
    zhihu_summary: str
    xiaohongshu_post: str
    social_post: str
    cover_prompt: str
    review_checklist: list[str]
    plan_id: str = field(default_factory=lambda: new_id("dist"))


@dataclass
class FeedbackEvent:
    trace_id: str
    article_id: str
    views: int = 0
    likes: int = 0
    favorites: int = 0
    comments: int = 0
    follows: int = 0
    leads: int = 0
    revenue_cents: int = 0
    notes: str = ""
    captured_at: str = field(default_factory=utc_now)
    feedback_id: str = field(default_factory=lambda: new_id("fb"))


@dataclass
class SandboxArtifact:
    artifact_id: str
    relative_path: str
    bytes_written: int
    created_at: str = field(default_factory=utc_now)


@dataclass
class AgentRunResult:
    trace_id: str
    trend: TrendCard
    research: ResearchBrief
    materials: MaterialBoard
    blueprint: ArticleBlueprint
    article: ArticlePackage
    editorial: EditorialReport
    quality: QualityReport
    policy: PolicyReport
    distribution: DistributionPlan
    artifacts: dict[str, str]
