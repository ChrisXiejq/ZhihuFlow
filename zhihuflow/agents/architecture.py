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
        strategy = _strategy_for(trend.topic)
        sections = [
            ArticleSectionPlan(
                heading=strategy["why_heading"],
                purpose=strategy["why_purpose"],
                material_card_ids=evidence_cards[:3],
            ),
            ArticleSectionPlan(
                heading=strategy["problem_heading"],
                purpose=strategy["problem_purpose"],
                material_card_ids=evidence_cards[:2] + implementation_cards[:2],
                required_elements=["analogy"],
            ),
            ArticleSectionPlan(
                heading=strategy["architecture_heading"],
                purpose=strategy["architecture_purpose"],
                material_card_ids=implementation_cards[:4],
                required_elements=["mechanism"],
            ),
            ArticleSectionPlan(
                heading=strategy["code_heading"],
                purpose=strategy["code_purpose"],
                material_card_ids=implementation_cards[:2],
                required_elements=["methodology"],
            ),
            ArticleSectionPlan(
                heading=strategy["table_heading"],
                purpose=strategy["table_purpose"],
                material_card_ids=materials.cards[:4] and [card.card_id for card in materials.cards[:4]],
                required_elements=["table"],
            ),
            ArticleSectionPlan(
                heading=strategy["risk_heading"],
                purpose=strategy["risk_purpose"],
                material_card_ids=risk_cards[:3],
            ),
        ]
        return ArticleBlueprint(
            topic=trend.topic,
            title_candidates=[
                f"{title_topic}：{strategy['title_suffix_1']}",
                f"{strategy['title_prefix_2']}：{title_topic}",
                f"我会怎样设计一个能长期工作的 {title_topic}",
            ],
            core_thesis=(
                strategy["core_thesis"].format(topic=trend.topic)
            ),
            opening_strategy=strategy["opening_strategy"],
            sections=sections,
            code_plans=[plan for plan in strategy["code_plans"].split("|") if plan],
            diagram_plan=strategy["diagram_plan"],
            table_plan=strategy["table_plan"],
            analogy=strategy["analogy"],
            cta=strategy["cta"],
            discussion_question=strategy["discussion_question"].format(topic=trend.topic),
        )


def _short_topic(topic: str) -> str:
    cleaned = topic.split("：")[0].replace("正在", "").strip()
    for suffix in ["工程", "系统", "架构", "Runtime"]:
        marker = f"{suffix} "
        if marker in cleaned and len(cleaned) > 28:
            return cleaned.split(marker)[0] + suffix
    return cleaned if len(cleaned) <= 32 else cleaned[:31].rstrip() + "…"


def _strategy_for(topic: str) -> dict[str, str]:
    lowered = topic.lower()
    if "dynamic workflow" in lowered or "自适应编排" in topic:
        return {
            "title_suffix_1": "真正难的不是流程图，而是运行时决策",
            "title_prefix_2": "从固定 DAG 到运行时路由",
            "core_thesis": "{topic} 的关键价值不在于多画几个节点，而在于让 Agent 能根据状态、风险和上下文，在运行时选择继续、重试、降级或人工接管。",
            "opening_strategy": "用固定流程图上线后遇到异常分支的场景开场，强调动态编排必须可解释。",
            "why_heading": "为什么固定流程开始不够用了",
            "why_purpose": "解释开放任务中用户意图、工具结果和风险等级都会变化。",
            "problem_heading": "Dynamic Workflow 到底动态在哪里",
            "problem_purpose": "拆解路径动态、粒度动态和控制权动态。",
            "architecture_heading": "我会怎么定义 Dynamic Workflow 的机制边界",
            "architecture_purpose": "说明状态读取、策略路由、执行器、检查点之间的因果关系和约束。",
            "code_heading": "一个更适合分析动态编排的方法框架",
            "code_purpose": "用状态、动作、约束和反馈解释动态编排，而不是强行堆代码。",
            "table_heading": "模块取舍：哪些动态能力值得先做",
            "table_purpose": "对比动态路由、checkpoint、人工接管和降级路径。",
            "risk_heading": "别把 Dynamic Workflow 做成随机游走",
            "risk_purpose": "说明动态必须受状态、规则和人工边界约束。",
            "code_plans": "仅当文章需要解释状态 schema 或路由接口时，才加入 1 个短代码块",
            "diagram_plan": "仅作为内部结构理解，不输出 Mermaid/PlantUML；正文用段落或 Markdown 表格说明状态、动作、约束、反馈。",
            "table_plan": "总结 State Reader、Policy Router、Checkpoint、Human Handoff、Degrade Path 的价值。",
            "analogy": "把 Dynamic Workflow 比作旅行领队，根据天气、路况和队员状态调整路线。",
            "cta": "建议读者先实现状态 schema、Policy Router 和 checkpoint，再谈复杂自适应。",
            "discussion_question": "你在做 {topic} 时，最难处理的是动态路由、状态恢复、工具失败，还是人工接管？",
        }
    if "memory" in lowered or "记忆" in topic:
        return {
            "title_suffix_1": "别再把记忆理解成聊天记录",
            "title_prefix_2": "从向量库到记忆治理",
            "core_thesis": "{topic} 的关键价值不在于多存历史，而在于把写入、检索、更新和遗忘变成一套可治理的运行时能力。",
            "opening_strategy": "用历史对话污染新任务的场景开场。",
            "why_heading": "为什么简单保存历史不够",
            "why_purpose": "解释记忆污染、过期事实和上下文挤占。",
            "problem_heading": "Memory 的核心不是存，而是治理",
            "problem_purpose": "拆解写入门禁、检索排序、更新和遗忘。",
            "architecture_heading": "我会怎么定义 Agent Memory 的概念边界",
            "architecture_purpose": "说明 Working、Episodic、Semantic、Preference Memory 的差异、证据强度和时效边界。",
            "code_heading": "一个更稳的 Memory 治理分析框架",
            "code_purpose": "从对象、证据、时效和可撤销性解释 Memory 治理，代码只在必要时出现。",
            "table_heading": "模块取舍：哪些记忆能力先做",
            "table_purpose": "总结 Write Gate、Retriever、Update Policy、Forgetting、Audit Log。",
            "risk_heading": "别让 Memory 污染推理",
            "risk_purpose": "说明记忆滥用会导致旧事实和临时偏好污染判断。",
            "code_plans": "仅当文章需要解释 MemoryItem schema 或写入门禁接口时，才加入 1 个短代码块",
            "diagram_plan": "仅作为内部结构理解，不输出 Mermaid/PlantUML；正文用概念边界和表格说明记忆流。",
            "table_plan": "总结写入、检索、更新、遗忘、审计能力。",
            "analogy": "把 Memory 比作资料室，而不是一个越堆越乱的大纸箱。",
            "cta": "建议读者先做写入门禁和遗忘策略，再扩展复杂长期记忆。",
            "discussion_question": "你在做 {topic} 时，最难的是写入、检索、更新，还是遗忘？",
        }
    if "context" in lowered or "上下文" in topic:
        return {
            "title_suffix_1": "真正拼的是上下文预算管理",
            "title_prefix_2": "从堆 Prompt 到管理信息流",
            "core_thesis": "{topic} 的关键价值不在于塞更多材料，而在于过滤、排序、压缩和反馈，让模型在有限上下文里看到真正重要的信息。",
            "opening_strategy": "用长任务上下文越堆越乱的场景开场。",
            "why_heading": "为什么上下文窗口越大，问题反而越明显",
            "why_purpose": "解释容量变大不等于组织变好。",
            "problem_heading": "Context Engineering 管的不是 prompt，而是信息流",
            "problem_purpose": "拆解过滤、排序、压缩和上下文反馈。",
            "architecture_heading": "我会怎么定义上下文管线的机制",
            "architecture_purpose": "说明 Filter、Rank、Compression、Context Pack、Feedback 的信息选择机制。",
            "code_heading": "一个更适合分析上下文的信息流框架",
            "code_purpose": "从过滤、排序、压缩和组装解释上下文预算，代码只在必要时出现。",
            "table_heading": "模块取舍：哪些上下文能力先做",
            "table_purpose": "总结过滤、排序、压缩、组装和反馈。",
            "risk_heading": "别把上下文工程做成材料堆叠",
            "risk_purpose": "说明无取舍上下文会污染模型判断。",
            "code_plans": "仅当文章需要解释 token budget 或 context pack 接口时，才加入 1 个短代码块",
            "diagram_plan": "仅作为内部结构理解，不输出 Mermaid/PlantUML；正文用信息流表格说明上下文管线。",
            "table_plan": "总结 Filter、Rank、Compress、Context Pack、Feedback。",
            "analogy": "把上下文比作行李箱，空间变大不等于不用分类。",
            "cta": "建议读者先做上下文预算和排序策略，再追求更大的窗口。",
            "discussion_question": "你在做 {topic} 时，最容易被污染的是目标、约束、历史记录，还是工具结果？",
        }
    return _adaptive_strategy(topic)


def _adaptive_strategy(topic: str) -> dict[str, str]:
    short = _short_topic(topic)
    return {
        "title_suffix_1": "先定义问题边界，再讨论工程价值",
        "title_prefix_2": "从概念热度到可验证框架",
        "core_thesis": "{topic} 的关键价值不在于套用某个既有 Agent 模板，而在于说清它解决什么问题、依赖哪些假设、如何被评估，以及在哪些边界内才成立。",
        "opening_strategy": f"用“{short} 很热，但很多讨论没有定义清楚问题边界”的场景开场。",
        "why_heading": f"为什么 {short} 值得重新认真看",
        "why_purpose": "解释这个主题从概念讨论进入方法、评测和工程取舍阶段。",
        "problem_heading": f"{short} 的概念边界在哪里",
        "problem_purpose": "拆解它到底解决什么问题、不解决什么问题，以及常见误解。",
        "architecture_heading": f"我会怎么分析 {short} 的机制链条",
        "architecture_purpose": "说明输入、约束、过程、输出、反馈之间的关系。",
        "code_heading": f"一个适合分析 {short} 的方法框架",
        "code_purpose": "从概念定义、机制假设、评价指标和失效模式解释主题，代码只在必要时出现。",
        "table_heading": f"如何评价 {short} 是否真的有效",
        "table_purpose": "总结概念边界、机制假设、评价指标、失效模式和适用条件。",
        "risk_heading": f"别把 {short} 写成万能答案",
        "risk_purpose": "说明概念滥用、指标缺失和边界不清会造成误导。",
        "code_plans": "仅当文章需要解释 schema、算法或接口时，才加入 1 个短代码块",
        "diagram_plan": "仅作为内部结构理解，不输出 Mermaid/PlantUML；正文用段落或 Markdown 表格说明分析框架。",
        "table_plan": "总结概念边界、机制假设、评价指标、失效模式和适用条件。",
        "analogy": f"把 {short} 比作一套研究假设，而不是一个现成答案；先证明假设成立，再谈规模化应用。",
        "cta": "建议读者先写清定义、评价指标和失败样本，再进入实现方案。",
        "discussion_question": "你在做 {topic} 时，最难的是定义边界、找到评价指标、处理失败样本，还是落到真实场景？",
    }
