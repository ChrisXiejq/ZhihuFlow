from __future__ import annotations

from zhihuflow.app.config import DirectorConfig
from zhihuflow.core.schemas import ArticleBlueprint, ArticleSectionPlan, MaterialBoard, ResearchBrief, TrendCard


class ArchitectureAgent:
    """Design the article before the writer starts drafting."""

    def design(
        self,
        trend: TrendCard,
        research: ResearchBrief,
        materials: MaterialBoard,
        config: DirectorConfig,
    ) -> ArticleBlueprint:
        evidence_cards = materials.clusters.get("evidence", [])
        implementation_cards = materials.clusters.get("implementation", [])
        risk_cards = materials.clusters.get("risk", [])
        title_topic = _short_topic(trend.topic)
        sections = [
            ArticleSectionPlan(
                heading="为什么这个话题现在值得认真看",
                purpose="用趋势证据和读者痛点建立阅读动机。",
                material_card_ids=evidence_cards[:3],
            ),
            ArticleSectionPlan(
                heading="真正的问题不是会不会写，而是能不能被追溯",
                purpose="把文章主线从自动写作转向可审计内容生产系统。",
                material_card_ids=evidence_cards[:2] + implementation_cards[:2],
                required_elements=["analogy"],
            ),
            ArticleSectionPlan(
                heading="一条 Multi-Agent 内容链路应该怎么设计",
                purpose="解释各 Agent 的职责、输入输出和协作关系。",
                material_card_ids=implementation_cards[:4],
                required_elements=["mermaid"],
            ),
            ArticleSectionPlan(
                heading="三段代码把工程骨架跑起来",
                purpose="用最少代码说明配置、运行和风控门禁。",
                material_card_ids=implementation_cards[:2],
                required_elements=["code"],
            ),
            ArticleSectionPlan(
                heading="模块取舍：哪些能力本期必须有，哪些可以晚点做",
                purpose="用表格总结技术取舍，体现工程判断。",
                material_card_ids=materials.cards[:4] and [card.card_id for card in materials.cards[:4]],
                required_elements=["table"],
            ),
            ArticleSectionPlan(
                heading="风险边界：不要把内容 Agent 做成黑箱发布器",
                purpose="说明证据不足、商业夸大和自动发布风险。",
                material_card_ids=risk_cards[:3],
            ),
        ]
        return ArticleBlueprint(
            topic=trend.topic,
            title_candidates=[
                f"{title_topic} 不是写作技巧，而是一套可复盘的内容操作系统",
                f"从自动写稿到 Multi-Agent 内容系统：{title_topic} 的真正分水岭",
                f"我会怎样设计一个能长期工作的 {title_topic} 内容 Agent",
            ],
            core_thesis=(
                f"{trend.topic} 的关键价值不在于更快生成一篇文章，而在于把选题、素材、证据、结构、编辑、风控和复盘拆成可审计的 Agent 链路。"
            ),
            opening_strategy="用创作者卡文和 AI 文缺少证据链的痛点开场，前 200 字内给出明确判断。",
            sections=sections,
            code_plans=[
                "DirectorConfig 配置主题、目标读者和字数边界。",
                "ContentDirector.run 触发一次带 trace_id 的可回放运行。",
                "PolicyGate 拦截夸大表达和自动发布风险。",
            ],
            diagram_plan="使用 Mermaid 展示 Trend -> Material -> Research -> Architecture -> Writing -> Editor -> Risk -> Distribution 的链路。",
            table_plan="用 Markdown 表格总结各 Agent 的职责、输入、输出和失败风险。",
            analogy="把多 Agent 内容系统比作一间厨房：采购、备菜、主厨、质检和出餐各司其职。",
            cta="建议读者先实现 event log、evidence table 和 policy check，再扩展复杂 Agent。",
            discussion_question=f"你在做 {trend.topic} 时，最难复盘的是选题、证据、结构还是发布后的反馈？",
        )


def _short_topic(topic: str) -> str:
    cleaned = topic.split("：")[0].replace("正在", "").strip()
    for suffix in ["工程", "系统", "架构", "Runtime"]:
        marker = f"{suffix} "
        if marker in cleaned and len(cleaned) > 28:
            return cleaned.split(marker)[0] + suffix
    return cleaned if len(cleaned) <= 32 else cleaned[:31].rstrip() + "…"
