from __future__ import annotations

import re
from typing import Any, Optional

from zhihuflow.app.config import DirectorConfig
from zhihuflow.core.schemas import ArticleBlueprint, ArticlePackage, MaterialBoard, ResearchBrief, TrendCard, to_jsonable
from zhihuflow.models.providers import ModelProvider, default_model
from zhihuflow.runtime.skills import SkillRegistry
from zhihuflow.runtime.tools import ToolRegistry, build_default_tool_registry
from zhihuflow.storage.longterm import LongTermMemory
from zhihuflow.content.style import strip_model_meta


class ZhihuWriter:
    def __init__(
        self,
        model: Optional[ModelProvider] = None,
        skill_registry: Optional[SkillRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory: Optional[LongTermMemory] = None,
    ) -> None:
        self.model = model or default_model()
        self.skill_registry = skill_registry or SkillRegistry()
        self.tool_registry = tool_registry or build_default_tool_registry()
        self.memory = memory

    def write(
        self,
        trend: TrendCard,
        research: ResearchBrief,
        trace_id: str,
        config: DirectorConfig,
        blueprint: Optional[ArticleBlueprint] = None,
        materials: Optional[MaterialBoard] = None,
    ) -> ArticlePackage:
        titles = (blueprint.title_candidates[:3] if blueprint else []) or [
            f"{trend.topic}：为什么它会是下一轮 AI 产品的分水岭？",
            f"别再只盯模型了，{_short_topic(trend.topic)} 真正拼的是工程系统",
            f"我为什么认为 {_short_topic(trend.topic)} 不能只靠 Prompt 解决",
        ]
        source_lines = "\n".join(f"- [{ref.evidence_id}] {ref.title} ({ref.source}) {ref.url}" for ref in research.sources[:8])
        claim_lines = "\n".join(f"- {claim.claim} evidence={claim.evidence_ids} confidence={claim.confidence}" for claim in research.claims)
        skill_brief = "\n\n".join(skill.brief() for skill in self.skill_registry.load_many(["zhihu-writing", "human-writing", "deep-research"]))
        tool_contracts = json_dumps_compact(self.tool_registry.contracts())
        memory_brief = self.memory.briefing() if self.memory else ""
        technical_blog_requirements = _technical_blog_requirements(trend.topic, config)
        blueprint_brief = json_dumps_compact(to_jsonable(blueprint)) if blueprint else "未提供文章蓝图。"
        material_brief = _material_brief(materials) if materials else "未提供素材板。"
        prompt = (
            f"话题：{trend.topic}\n"
            f"目标读者：{research.audience}\n"
            f"商业目标：{config.commercial_goal}\n"
            f"目标字数：中文 {config.target_min_chars}-{config.target_max_chars} 字。\n"
            "Markdown 结构要求：必须有 1 个一级标题；必须有 4-7 个二级标题；二级标题要服务论证，不要机械对称。\n"
            "我的立场：这篇文章要像一个真正做过 Agent 工程的人在解释问题，不像模型生成的标准答案。\n"
            f"可用工具契约：{tool_contracts}\n"
            f"长期记忆：\n{memory_brief}\n"
            f"按需加载的 Skills：\n{skill_brief}\n"
            f"内部研究材料，仅用于校验事实，不要在正文展示 evidence_id、URL 或参考来源列表：\n{source_lines}\n"
            f"内部 Claims，仅用于帮助判断主线，不要逐条照抄到正文：\n{claim_lines}\n"
            f"\n顶级技术博客写作要求：\n{technical_blog_requirements}\n"
            f"\nArchitecture Agent 文章蓝图：\n{blueprint_brief}\n"
            f"\nMaterial Agent 素材板摘要：\n{material_brief}\n"
            "\n写作任务：生成一篇完整的知乎风格技术文章。\n"
            "硬性要求：\n"
            "1. 只输出 Markdown 文章正文，不输出原文分析、优化策略、自检说明。\n"
            "2. 正文字数必须在目标区间内，不能短稿。\n"
            "3. 不要套固定报告结构，不要机械编号，不要使用“首先/其次/最后/综上所述”。\n"
            "4. 开头 200 字内必须出现一个明确问题、研究判断或概念边界，不要泛泛介绍背景。\n"
            "5. 每个核心观点至少落到一个机制解释、研究脉络、工程细节、反例或限制条件。\n"
            "6. 不要主动讨论 GMV、求职包装、项目推销或 ZhihuFlow，除非选题本身就是这些内容。\n"
            "7. 不要输出“参考来源”章节，不要输出 evidence_id、URL、来源编号或括号里的证据标记；证据只保留在系统内部 trace。\n"
            "8. 不要输出 Mermaid、PlantUML 或任何图表代码块；普通 Markdown 无法稳定解析这类图。\n"
            "9. 代码块不是必需项。只有当主题必须展示 schema、算法、API 或关键工程接口时才加入，最多 1-2 个，并解释它解决什么问题；概念型文章不要硬塞代码。\n"
            "10. 可以使用 Markdown 表格做概念对比、方法框架或限制条件总结，但不要为了凑形式而堆元素。\n"
            "11. 必须提升学术性：写清概念定义、问题边界、机制链条、已有讨论脉络、适用条件和局限性。\n"
            "12. 如果提供了文章蓝图，必须优先遵守蓝图中的 core_thesis、sections、table_plan、analogy 和讨论问题；code_plans 只在必要时使用，diagram_plan 只作为结构理解，不直接输出图。"
        )
        generated = self.model.generate(
            system=(
                "你是一个有真实 Agent 工程经验、也熟悉相关研究脉络的中文技术作者。"
                "你的文章应该有概念边界、机制分析、限制条件和作者判断，不要像咨询报告或 AI 模板。"
                "只能基于内部研究材料形成判断，但不要把 evidence_id、URL 或参考来源列表写给读者。"
            ),
            prompt=prompt,
            temperature=0.72,
        )
        body = self._finalize_article(trend, research, generated, config, trace_id)
        return ArticlePackage(
            topic=trend.topic,
            titles=titles,
            opening_hook=f"如果只把 {trend.topic} 理解成一个新名词，大概率会错过它背后的工程机会。",
            outline=[section.heading for section in blueprint.sections] if blueprint else [
                "先给结论：这不是概念热，而是工程边界变化",
                "为什么现在发生：趋势证据与技术动因",
                "核心架构：搜索、记忆、工具契约、工作流与评测",
                "工程实现里最容易踩的坑",
                "风险和边界：别把 Agent 做成不可审计的黑箱",
            ],
            body_markdown=body,
            citations=research.sources[:8],
            commercial_angle="用高质量技术长文建立专业可信度，但正文表达保持技术讨论优先，不承诺收益。",
            cta=blueprint.cta if blueprint else "如果你正在做 AI Agent 项目，可以先从一条可回放的 event log 和一份可审计的 evidence table 开始，而不是先堆模型调用。",
            trace_id=trace_id,
        )

    def _finalize_article(self, trend: TrendCard, research: ResearchBrief, generated: str, config: DirectorConfig, trace_id: str) -> str:
        body = strip_model_meta(generated).strip()
        if not body.startswith("# "):
            body = f"# {trend.topic}\n\n{body}"
        if (
            _word_count_zh(body) < config.target_min_chars
            or not _has_required_markdown_structure(body)
            or not _has_academic_depth_elements(body)
        ):
            body = self._fallback_structured_article(trend, research, config, trace_id)
        body = _strip_public_references(body)
        return _trim_to_max_chars(body, config.target_max_chars)

    def _fallback_structured_article(self, trend: TrendCard, research: ResearchBrief, config: DirectorConfig, trace_id: str) -> str:
        profile = _topic_profile(trend.topic, trace_id)
        academic = _academic_frame(trend.topic)
        claim_text = _public_claim_paragraphs(trend, research)
        body = f"""# {profile['title_prefix']}：{profile['title_suffix']}

{profile['opening_scene']}

{profile['opening_judgment']}

## {profile['why_heading']}

{_public_why_now(research.why_now, trend.topic)}

{profile['why_body']}

## {profile['problem_heading']}

{profile['problem_body']}

{claim_text}

{profile['problem_close']}

## {profile['architecture_heading']}

{profile['architecture_body']}

{profile['architecture_tradeoff']}

## {academic['mechanism_heading']}

{academic['mechanism_body']}

{profile['analogy']}

## {academic['method_heading']}

{academic['method_body']}

| {academic['table_col_1']} | {academic['table_col_2']} | {academic['table_col_3']} |
| --- | --- | --- |
{academic['table_rows']}

## {academic['boundary_heading']}

{academic['boundary_body']}

## {profile['hard_part_heading']}

{profile['hard_part_body']}

{profile['hard_part_close']}

## {profile['risk_heading']}

{profile['risk_body']}

{profile['risk_close']}

## {profile['practice_heading']}

{profile['practice_step_1']}

{profile['practice_step_2']}

{profile['practice_step_3']}

## {profile['ending_heading']}

{profile['ending_body']}

{profile['ending_action']}

{profile['discussion_question']}
"""
        return _expand_to_min_chars(body, trend, research, config.target_min_chars)


def _citation_lines(research: ResearchBrief) -> str:
    return "\n".join(f"- `{ref.evidence_id}`：[{ref.title}]({ref.url})，来源：{ref.source}" for ref in research.sources[:8])


def _topic_profile(topic: str, diversity_key: str = "") -> dict[str, str]:
    lowered = topic.lower()
    if "dynamic workflow" in lowered or "自适应编排" in topic:
        return _with_profile_variant(_dynamic_workflow_profile(topic), topic, diversity_key)
    if "memory" in lowered or "记忆" in topic:
        return _with_profile_variant(_memory_profile(topic), topic, diversity_key)
    if "context" in lowered or "上下文" in topic:
        return _with_profile_variant(_context_profile(topic), topic, diversity_key)
    if "rag" in lowered or "检索" in topic:
        return _with_profile_variant(_rag_profile(topic), topic, diversity_key)
    return _with_profile_variant(_adaptive_topic_profile(topic), topic, diversity_key)


def _with_profile_variant(profile: dict[str, str], topic: str, diversity_key: str) -> dict[str, str]:
    variants = _profile_variants(topic)
    if not variants:
        return profile
    key = diversity_key or topic
    selected = variants[sum(ord(ch) for ch in key) % len(variants)]
    varied = dict(profile)
    varied.update(selected)
    return varied


def _profile_variants(topic: str) -> list[dict[str, str]]:
    lowered = topic.lower()
    if "dynamic workflow" in lowered or "自适应编排" in topic:
        return [
            {},
            {
                "title_suffix": "失败恢复能力，比流程图更重要",
                "opening_scene": "真正考验 Dynamic Workflow 的，不是正常路径能不能跑通，而是任务跑偏之后系统怎么收场。工具返回空结果、用户临时补充约束、模型判断置信度不足，这些情况一出现，固定流程就会开始变脆。",
                "opening_judgment": "所以我会从失败恢复看 Dynamic Workflow：它不是让 Agent 随便改路线，而是让系统在异常发生时有一组清楚的补救动作。",
                "why_heading": "为什么失败路径比成功路径更值得设计",
                "problem_heading": "动态编排首先要回答失败后怎么办",
                "architecture_heading": "我会把恢复路径放进 Runtime",
                "hard_part_heading": "真正难的是让恢复动作可解释",
            },
            {
                "title_suffix": "人工接管不是妥协，而是系统能力",
                "opening_scene": "很多 Agent 系统喜欢追求全自动，但真实业务里最危险的不是慢一点，而是系统在不确定时还继续装作确定。Dynamic Workflow 的价值，恰恰在于能识别哪些节点该停下来让人看一眼。",
                "opening_judgment": "从这个角度看，Dynamic Workflow 不是减少人工，而是把人工接管变成一种有边界、有记录、可复盘的运行时能力。",
                "why_heading": "为什么全自动不是唯一目标",
                "problem_heading": "动态编排要能识别接管时机",
                "architecture_heading": "我会把 Human Handoff 设计成一等公民",
                "hard_part_heading": "真正难的是定义停下来的条件",
            },
        ]
    if "memory" in lowered or "记忆" in topic:
        return [
            {},
            {
                "title_suffix": "真正难的是让旧信息不过期",
                "opening_scene": "Agent Memory 最隐蔽的问题不是记不住，而是记得太认真。用户一个月前的偏好、旧版本文档里的事实、临时任务里的约束，如果没有过期机制，都会在未来某次推理里重新出现。",
                "opening_judgment": "所以 Memory 的关键不是容量，而是时效。一个靠谱的记忆系统必须知道信息什么时候有效，什么时候应该降权，什么时候必须被删除。",
                "why_heading": "为什么记住太多反而会出错",
                "problem_heading": "Memory 需要管理时效，而不是堆历史",
                "architecture_heading": "我会给 Memory 加上生命周期",
                "hard_part_heading": "真正难的是判断一条记忆何时过期",
            },
            {
                "title_suffix": "用户纠错能力决定系统可信度",
                "opening_scene": "如果一个 Agent 记错了你的偏好，最糟糕的情况不是这次答错，而是它以后每次都带着这个错误继续工作。很多 memory demo 没有暴露这个问题，因为它们只展示写入和检索，不展示纠错。",
                "opening_judgment": "我认为 Agent Memory 必须把用户纠错放到核心路径里。没有可编辑、可追踪、可撤销的记忆，长期使用只会积累新的不信任。",
                "why_heading": "为什么 Memory 必须允许用户纠错",
                "problem_heading": "Memory 的产品边界是可改、可删、可解释",
                "architecture_heading": "我会把 Audit Log 放进记忆系统",
                "hard_part_heading": "真正难的是让纠错影响后续推理",
            },
        ]
    if "context" in lowered or "上下文" in topic:
        return [
            {},
            {
                "title_suffix": "不是窗口不够大，而是信息没有排队",
                "opening_scene": "上下文窗口越来越大以后，很多人会误以为 Context Engineering 不重要了。我的感受刚好相反：窗口越大，越容易把低价值材料也塞进来，最后模型读了很多，却没有读到关键约束。",
                "opening_judgment": "Context Engineering 的核心不是扩容，而是排序。谁先进上下文、谁被压缩、谁只留下摘要，这些选择会直接决定模型表现。",
                "why_heading": "为什么大窗口解决不了信息排序",
                "problem_heading": "Context Engineering 首先是优先级问题",
                "architecture_heading": "我会先做 Context Ranker",
                "hard_part_heading": "真正难的是判断什么信息最该被看见",
            },
        ]
    if "rag" in lowered or "检索" in topic:
        return [
            {},
            {
                "title_suffix": "答案写得流畅，不代表证据链成立",
                "opening_scene": "RAG 系统最容易骗过自己的地方，是最终答案看起来很顺。可一旦拆开检索链路，你可能会发现 query 没拆对、召回片段不完整、证据互相冲突，模型只是把这些问题包装成了一段流畅表达。",
                "opening_judgment": "Agentic RAG 的价值，是把这些隐藏问题显式暴露出来：先计划检索，再筛证据，再检查冲突，最后才生成答案。",
                "why_heading": "为什么答案流畅不等于 RAG 可靠",
                "problem_heading": "RAG 的核心问题变成证据链质量",
                "architecture_heading": "我会把 Evidence Checker 放到主链路",
                "hard_part_heading": "真正难的是发现证据之间的矛盾",
            },
        ]
    return [
        {},
        {
            "title_suffix": "真正难的是把概念变成可验证问题",
            "opening_scene": f"{topic} 这类新概念最容易经历同一个过程：刚出现时大家讨论愿景，热起来之后开始套用各种已有框架，最后才发现真正困难的是定义边界和评价方法。",
            "opening_judgment": f"所以我会先把 {topic} 当成一个待验证的问题，而不是一个已经成立的答案。只有说清它解决什么、不解决什么、如何评估，后面的工程实现才有意义。",
            "why_heading": f"为什么 {topic} 不能只看概念热度",
            "problem_heading": f"{topic} 的概念边界在哪里",
            "architecture_heading": f"我会怎么拆解 {topic} 的机制链条",
            "hard_part_heading": "真正难的是建立可评价的判断标准",
        },
    ]


def _adaptive_topic_profile(topic: str) -> dict[str, str]:
    short = _short_topic(topic)
    return {
        "title_prefix": topic,
        "title_suffix": "从概念热度到可验证框架",
        "opening_scene": f"{short} 最近很容易被写成一个新名词：听起来方向明确，实际展开时却常常变成旧概念的重新包装。真正值得讨论的，不是它是不是热门，而是它有没有提出新的问题边界。",
        "opening_judgment": f"我更愿意把 {short} 当成一个研究对象来处理：先定义它试图解决什么问题，再看它依赖哪些机制假设，最后讨论它如何被评估和落地。",
        "why_heading": f"为什么 {short} 值得重新认真看",
        "why_body": f"{short} 的价值不应只来自概念热度，而应来自它能否解释现有方法解释不了的问题。如果一个主题只能换一套说法，却不能改变分析框架、评价指标或工程边界，那它很难支撑一篇有深度的技术文章。",
        "problem_heading": f"{short} 的概念边界在哪里",
        "problem_body": f"讨论 {short} 时，我会先问三个问题：它的对象是什么，它改变了哪一个机制，它和相邻概念的差异在哪里。缺少这三层边界，文章很容易滑向泛泛而谈。",
        "problem_close": f"因此，{short} 不应该被直接写成万能答案。更合理的写法，是把它放在具体问题里，说明它在哪些条件下成立，在哪些场景下反而会失效。",
        "architecture_heading": f"我会怎么拆解 {short} 的机制链条",
        "architecture_body": "一个通用的分析方式，是把主题拆成输入、约束、过程、输出和反馈。输入决定它处理什么材料，约束决定它不能越过什么边界，过程决定它如何产生结果，输出决定它交付什么，反馈决定它能否持续改进。",
        "architecture_tradeoff": "这种拆法看起来比直接给结论慢，但它能避免文章被历史模板牵着走。主题换了，分析变量也会跟着变化；只有框架保留，具体论证必须围绕新主题重建。",
        "diagram": "",
        "analogy": f"可以把 {short} 看成一组研究假设，而不是一个现成工具。研究假设需要被定义、被验证、被反驳；如果只把它当成口号，就很难讨论深度。",
        "code_heading": "代码不是必要表达，先看问题是否需要形式化",
        "code_intro": "",
        "code_1": "",
        "code_2_intro": "",
        "code_2": "",
        "code_3_intro": "",
        "code_3": "",
        "table_col_1": "分析维度",
        "table_col_2": "要回答的问题",
        "table_col_3": "写作时的作用",
        "table_rows": "| 概念边界 | 它解决什么、不解决什么 | 防止文章泛化成万能叙事 |\n| 机制假设 | 它为什么可能有效 | 让论证从观点变成推理 |\n| 评价指标 | 怎样判断它真的更好 | 避免只靠案例感受 |\n| 失效模式 | 它在什么条件下会失败 | 提升文章的可信度 |\n| 工程约束 | 落地需要哪些前提 | 把概念放回真实系统 |",
        "hard_part_heading": "真正难的是建立可评价的判断标准",
        "hard_part_body": f"{short} 这类主题最怕只有方向感，没有评价标准。没有指标时，任何案例都能被解释成成功；没有失败样本时，任何限制都会被包装成未来优化空间。",
        "hard_part_close": "所以文章需要主动写出判断标准：什么结果算有效，什么结果只是看起来合理，什么失败说明这个方向本身需要重新定义。",
        "risk_heading": f"别把 {short} 写成万能答案",
        "risk_body": "新概念最容易被滥用在三个地方：把适用条件省略掉，把局部案例推广成普遍规律，把工程成本藏在愿景后面。这些写法会让文章看起来兴奋，但缺少可信度。",
        "risk_close": "更稳的表达，是承认它有边界：在某些场景里它能带来新的组织方式，在另一些场景里它可能只是增加复杂度。",
        "practice_heading": f"评价 {short}，要看三类证据",
        "practice_step_1": "第一类是定义证据：概念是否能和相邻概念区分开，而不是换一个名字描述旧问题。",
        "practice_step_2": "第二类是机制证据：它是否说明了为什么会更好，而不是只展示一个看起来不错的案例。",
        "practice_step_3": "第三类是失败证据：它是否暴露了不适用场景，以及这些失败能否反过来修正定义。",
        "ending_heading": f"最后，{short} 的价值取决于能否被验证",
        "ending_body": f"回到最开始的问题：{short} 值不值得写，不取决于它是不是热门，而取决于它能不能形成清晰的问题边界、机制解释和评价框架。",
        "ending_action": "如果要继续研究这个方向，我建议先列出定义、假设、指标和失败样本，再考虑具体实现或产品化。",
        "discussion_question": f"关于 {short}，你最想看清的是概念边界、机制解释、评价指标，还是真实失败案例？",
    }


def _dynamic_workflow_profile(topic: str) -> dict[str, str]:
    return {
        "title_prefix": topic,
        "title_suffix": "真正难的不是流程图，而是运行时决策",
        "opening_scene": "我以前看 Agent demo，最容易被一张漂亮的流程图骗过去：用户输入需求，Planner 拆任务，Executor 调工具，Verifier 做校验，看起来每条边都很清楚。可真实业务一跑起来，流程图很快就不够用了。用户会临时改目标，工具会返回半截数据，某一步会突然需要人工确认，原来画死的 DAG 开始变成一张随时改线的施工图。",
        "opening_judgment": "这就是 Dynamic Workflow 真正有价值的地方。它讨论的不是“多加几个节点”，而是 Agent 能不能在运行时根据状态、风险和上下文，决定下一步该继续、重试、跳过、降级还是交给人。",
        "why_heading": "为什么固定流程开始不够用了",
        "why_body": "固定 workflow 适合边界清楚的任务，比如每天拉数据、生成报表、跑一次审核。但 Agent 面对的是开放任务：输入不稳定，工具结果不稳定，用户意图也可能中途变化。如果系统只能沿着预设路径往前走，就会在第一个异常分叉处失去判断力。",
        "problem_heading": "Dynamic Workflow 到底动态在哪里",
        "problem_body": "我理解的 Dynamic Workflow 至少有三层动态。第一是路径动态：下一步不是写死的，而是由当前状态决定。第二是粒度动态：任务复杂时拆细，任务简单时合并。第三是控制权动态：低风险步骤自动跑，高风险步骤暂停给人。它不是取消流程，而是让流程具备运行时选择能力。",
        "problem_close": "所以 Dynamic Workflow 的关键不是“让模型自己想怎么跑”，而是把选择权放进一个可观测的 runtime：每次改路都要有理由，每个分支都要能被追踪，每次人工接管都要能回写系统。",
        "architecture_heading": "我会怎么设计 Dynamic Workflow Runtime",
        "architecture_body": "我会把它拆成四个核心模块：State Reader 读取当前任务状态，Policy Router 判断下一步路径，Step Runner 执行具体动作，Checkpoint Store 保存中间结果。这样一来，模型负责提出候选动作，runtime 负责决定动作是否允许执行。",
        "architecture_tradeoff": "这个设计比固定 DAG 复杂，但换来的是可恢复性。任务失败时，系统不用从头开始，也不用假装一切正常；它可以回到最近的 checkpoint，根据失败原因选择重试、换工具、缩小任务或者交给人。",
        "diagram": "flowchart LR\n  A[Goal + Context] --> B[State Reader]\n  B --> C[Policy Router]\n  C -->|continue| D[Step Runner]\n  C -->|retry| E[Retry Queue]\n  C -->|handoff| F[Human Review]\n  D --> G[Checkpoint Store]\n  G --> B",
        "analogy": "如果用日常生活类比，固定 workflow 像提前打印好的旅行攻略，Dynamic Workflow 更像一个靠谱的领队。天气变了、路堵了、队员体力不一样，领队不会死守原计划，但每次改路线都要说明原因，还要尽量让大家安全到达目的地。",
        "code_heading": "三段代码看懂动态编排的骨架",
        "code_intro": "第一段是状态对象。Dynamic Workflow 的入口不是一个空 prompt，而是一份可以被机器判断的状态快照。",
        "code_1": "from dataclasses import dataclass\n\n@dataclass\nclass WorkflowState:\n    goal: str\n    step: str\n    confidence: float\n    failures: int = 0\n    needs_human: bool = False",
        "code_2_intro": "第二段是路由器。它不执行任务，只决定下一步应该走哪条路径。",
        "code_2": "def route(state: WorkflowState) -> str:\n    if state.needs_human:\n        return \"handoff\"\n    if state.failures >= 2:\n        return \"degrade\"\n    if state.confidence < 0.65:\n        return \"verify\"\n    return \"continue\"",
        "code_3_intro": "第三段是 checkpoint。动态不等于随意，系统每次改路之前都要保存现场。",
        "code_3": "class CheckpointStore:\n    def __init__(self):\n        self.items = []\n\n    def save(self, trace_id: str, state: WorkflowState, decision: str) -> None:\n        self.items.append({\"trace_id\": trace_id, \"state\": state, \"decision\": decision})",
        "table_col_1": "能力",
        "table_col_2": "解决的问题",
        "table_col_3": "固定流程的短板",
        "table_rows": "| State Reader | 让系统知道当前跑到哪里 | 只能按预设步骤前进 |\n| Policy Router | 根据风险和置信度选路 | 异常分支难处理 |\n| Checkpoint | 支持恢复和复盘 | 失败后只能重跑 |\n| Human Handoff | 把高风险决策交给人 | Agent 容易越权 |\n| Degrade Path | 工具失败时降级完成 | 一步失败拖垮全链路 |",
        "hard_part_heading": "真正难的是约束动态，而不是放开动态",
        "hard_part_body": "Dynamic Workflow 最容易走偏的地方，是把所有决策都交给模型。这样看起来很智能，但调试会非常痛苦：为什么这次跳过了校验？为什么那次直接交付？为什么同样输入走了不同路径？如果系统回答不了这些问题，动态就会变成不可控。",
        "hard_part_close": "更稳的做法是让模型提出候选动作，让规则、状态和人工边界决定动作能不能执行。动态发生在受控空间里，而不是发生在黑箱里。",
        "risk_heading": "别把 Dynamic Workflow 做成随机游走",
        "risk_body": "动态编排不是每一步都重新发明流程。大部分生产系统仍然需要稳定主干，只是在关键节点保留分支：重试、降级、补充上下文、人工确认。主干稳定，分支可控，系统才有可维护性。",
        "risk_close": "一个简单判断是：如果某个分支不能解释触发条件、不能记录决策理由、不能回放当时状态，那它就不该进入生产链路。",
        "practice_heading": "评价 Dynamic Workflow，要看三类失效模式",
        "practice_step_1": "第一类是状态失效：系统不知道自己已经掌握了什么、缺少什么、哪一步曾经失败。状态失效会让动态路由变成重复尝试，因为每次决策都像从零开始。",
        "practice_step_2": "第二类是约束失效：系统知道可以做什么，却不知道什么不能做。高风险动作、低置信结论和不可逆操作如果没有边界，动态编排会放大模型的过度自信。",
        "practice_step_3": "第三类是反馈失效：系统完成任务后没有把失败原因、人工修改和质量评价写回运行时。没有反馈，所谓动态只发生在单次任务里，无法形成可改进的系统能力。",
        "ending_heading": "最后，Dynamic Workflow 是运行时能力，不是 prompt 技巧",
        "ending_body": "回到最开始的问题：Dynamic Workflow 的价值，不是让流程图更复杂，而是让 Agent 在不确定环境里保持可控。它应该知道什么时候继续，什么时候停下，什么时候换路，什么时候把控制权交给人。",
        "ending_action": "如果你正在做 Agent 系统，我建议先从状态、路由和 checkpoint 三件事开始。等这三件事跑稳，再考虑更复杂的多 Agent 协作。",
        "discussion_question": "你在做 Agent Workflow 时，最难处理的是动态路由、状态恢复、工具失败，还是人工接管边界？",
    }


def _workflow_profile(topic: str) -> dict[str, str]:
    profile = _dynamic_workflow_profile(topic)
    profile.update(
        {
            "title_suffix": "真正的分水岭不是模型，而是运行时",
            "opening_scene": "我见过不少团队把 Agent 项目做成一个很漂亮的 demo：输入一个任务，模型调用几次工具，最后吐出一段看起来完整的答案。演示时没问题，真正上线后问题才开始暴露。用户追问一句“这个结论来自哪里”，系统给不出证据；任务跑到一半失败，没人知道该从哪一步恢复。",
            "opening_judgment": "在我看来，真正的变化正在这里：Agent 不再只是“模型加工具”的演示套路，而是在逼我们回答一个更工程化的问题，能不能把规划、工具、状态、校验和人工接管组成一个可持续运行的系统。",
            "why_heading": "为什么这个话题现在值得认真看",
            "problem_heading": "单次 Prompt 为什么撑不住复杂任务",
            "architecture_heading": "Agent Workflow 应该怎么拆",
        }
    )
    return profile


def _memory_profile(topic: str) -> dict[str, str]:
    profile = _dynamic_workflow_profile(topic)
    profile.update(
        {
            "title_suffix": "别再把记忆理解成聊天记录",
            "opening_scene": "很多 Agent 项目一说 memory，第一反应就是把历史对话塞进向量库。这个做法能跑 demo，但很快会遇到问题：旧信息污染新判断，临时偏好被当成长期事实，用户纠正过的内容下次又被系统忘掉。",
            "opening_judgment": "我更愿意把 Agent Memory 看成一套信息治理系统：什么该写入，什么该更新，什么该遗忘，什么只能作为短期上下文。",
            "why_heading": "为什么简单保存历史不够",
            "why_body": "Agent 任务越长，记忆越容易从资产变成负担。未经筛选的历史会挤占上下文窗口，也会把过期判断带回新任务。真正可用的记忆，需要有类型、时效、置信度和来源边界。",
            "problem_heading": "Memory 的核心不是存，而是治理",
            "problem_body": "一个可用的 memory runtime 至少要处理四件事：写入前筛选，检索时排序，使用后更新，过期后遗忘。缺少任何一环，系统都会越来越像一个只会堆笔记的助手。",
            "problem_close": "因此 Memory 的核心问题不是“存不存”，而是“以什么证据写入、在什么条件下检索、何时更新、如何撤销”。如果这些规则缺失，长期记忆会从能力变成新的幻觉来源。",
            "architecture_heading": "我会怎么拆 Agent Memory",
            "architecture_body": "我会把 Memory 拆成 Working Memory、Episodic Memory、Semantic Memory 和 Preference Memory。短期状态放 Working，任务过程放 Episodic，稳定知识放 Semantic，用户偏好单独沉淀。",
            "architecture_tradeoff": "这种拆分的代价是治理成本更高，但它让不同类型的信息拥有不同生命周期。临时任务状态不应长期保存，用户偏好也不应和模型推断混在一起。",
            "diagram": "flowchart LR\n  A[New Event] --> B[Write Gate]\n  B --> C[Working Memory]\n  B --> D[Episodic Memory]\n  B --> E[Semantic Memory]\n  B --> F[Preference Memory]\n  C --> G[Retriever]\n  D --> G\n  E --> G\n  F --> G",
            "analogy": "Agent Memory 更像一个资料室，而不是一个大纸箱。资料室需要分类、借阅记录和过期清理；大纸箱只会越堆越乱。",
            "code_heading": "三段代码看懂 Memory 治理",
            "code_1": "from dataclasses import dataclass\n\n@dataclass\nclass MemoryItem:\n    text: str\n    kind: str\n    confidence: float\n    ttl_days: int",
            "code_2": "def should_write(item: MemoryItem) -> bool:\n    if item.confidence < 0.7:\n        return False\n    if item.kind not in {\"preference\", \"fact\", \"episode\"}:\n        return False\n    return True",
            "code_3": "def retrieve(items: list[MemoryItem], query: str) -> list[MemoryItem]:\n    fresh = [item for item in items if item.ttl_days > 0]\n    return sorted(fresh, key=lambda item: item.confidence, reverse=True)[:5]",
            "table_rows": "| Write Gate | 避免垃圾记忆写入 | 历史越存越乱 |\n| Retriever | 找到当前任务相关记忆 | 上下文被无关信息污染 |\n| Update Policy | 修正过期偏好和事实 | 系统反复犯旧错 |\n| Forgetting | 清理临时状态 | 记忆库持续膨胀 |\n| Audit Log | 解释记忆从哪来 | 用户无法纠错 |",
            "hard_part_heading": "真正难的是遗忘，而不是存储",
            "hard_part_body": "Memory 系统最难的部分，是判断一条信息什么时候不再应该影响推理。过期事实、临时偏好和错误推断如果长期保留，会让 Agent 看起来越来越“了解用户”，实际却越来越难纠正。",
            "hard_part_close": "所以遗忘不是删除能力，而是质量控制。一个系统越强调长期记忆，越需要明确降权、过期、撤销和人工纠错机制。",
            "risk_heading": "别让 Memory 污染推理",
            "risk_body": "记忆污染通常不是一次性爆发，而是逐步累积。模型把上次任务的约束带到新任务，把用户随口表达当成稳定偏好，把推断结果当成事实，这些都会让输出变得更自信也更难验证。",
            "risk_close": "一个简单判断是：如果用户无法看到某条记忆从何而来，也无法修改它，那么这条记忆就不应该以高权重参与长期推理。",
            "practice_heading": "如果今天开始做 Memory，我会先做这三件事",
            "practice_step_1": "第一步，先定义记忆类型和写入门禁。明确哪些信息属于短期状态，哪些属于用户偏好，哪些只是一次任务里的临时事实。",
            "practice_step_2": "第二步，给每条记忆加上证据、时间和置信度。不要让模型推断和用户明确表达拥有同等权重。",
            "practice_step_3": "第三步，设计纠错和遗忘入口。用户应该能删除、降权或改写记忆，系统也应该能让过期信息自然退出高权重检索。",
            "ending_heading": "最后，Memory 是运行时的一部分",
            "ending_body": "回到最开始的问题：Agent Memory 的价值，不是让系统保存更多历史，而是让系统在长期任务里形成可解释、可纠错、可更新的状态。",
            "ending_action": "如果你准备实现 Memory，建议先做小而严格的写入规则，再做检索和长期沉淀。记忆越强，越需要治理边界。",
            "discussion_question": "你做 Agent Memory 时，最头疼的是写入、检索、更新，还是遗忘？",
        }
    )
    return profile


def _context_profile(topic: str) -> dict[str, str]:
    profile = _dynamic_workflow_profile(topic)
    profile.update(
        {
            "title_suffix": "真正拼的是上下文预算管理",
            "opening_scene": "很多长任务 Agent 失败，不是因为模型不够聪明，而是因为上下文像会议纪要一样越堆越长。到最后，关键约束被淹没，临时信息和长期目标混在一起，模型看似读了很多，其实抓不住重点。",
            "opening_judgment": "Context Engineering 的核心，是把上下文当成稀缺资源来管理，而不是把所有材料一股脑塞给模型。",
            "why_heading": "为什么上下文窗口越大，问题反而越明显",
            "why_body": "窗口变大只解决容量问题，不解决组织问题。没有结构化的上下文，模型仍然会被噪声干扰；没有压缩策略，长任务会不断变慢；没有优先级，最重要的信息未必会被模型真正使用。",
            "problem_heading": "Context Engineering 管的不是 prompt，而是信息流",
            "problem_body": "Context Engineering 处理的是信息如何进入、停留和退出模型视野。它关心的不只是 prompt 写法，而是材料筛选、优先级排序、压缩损耗和上下文反馈。",
            "problem_close": "如果没有这层信息流治理，上下文窗口越大，系统越容易把无关历史、低置信材料和过期约束一起塞给模型。",
            "architecture_heading": "我会怎么设计上下文管线",
            "architecture_body": "我会把上下文管线拆成 Filter、Rank、Compress、Pack 和 Feedback。Filter 决定什么不能进来，Rank 决定什么优先出现，Compress 控制表达成本，Pack 负责最终组织，Feedback 记录哪些上下文真正有效。",
            "architecture_tradeoff": "这套管线会增加前处理成本，但能换来更稳定的长任务表现。尤其当任务跨多轮、多工具、多来源时，上下文组织比窗口大小更重要。",
            "diagram": "flowchart LR\n  A[Raw Inputs] --> B[Filter]\n  B --> C[Chunk + Rank]\n  C --> D[Compression]\n  D --> E[Context Pack]\n  E --> F[Model Call]\n  F --> G[Context Feedback]",
            "analogy": "上下文像行李箱。箱子变大当然有用，但如果不分类、不取舍、不把常用物放在外层，旅途中还是会手忙脚乱。",
            "code_heading": "三段代码看懂上下文预算",
            "code_1": "def estimate_tokens(text: str) -> int:\n    return max(1, len(text) // 2)",
            "code_2": "def pack_context(chunks: list[str], budget: int) -> list[str]:\n    selected = []\n    used = 0\n    for chunk in chunks:\n        cost = estimate_tokens(chunk)\n        if used + cost <= budget:\n            selected.append(chunk)\n            used += cost\n    return selected",
            "code_3": "def compress(note: str, limit: int = 300) -> str:\n    return note if len(note) <= limit else note[:limit] + \"...\"",
            "table_rows": "| Filter | 去掉无关输入 | 噪声挤占窗口 |\n| Rank | 决定材料优先级 | 关键事实被淹没 |\n| Compress | 控制上下文成本 | 长任务越来越慢 |\n| Context Pack | 组装模型输入 | prompt 结构混乱 |\n| Feedback | 记录哪些上下文有效 | 每次都从头试 |",
            "hard_part_heading": "真正难的是取舍，而不是扩窗口",
            "hard_part_body": "上下文工程最难的地方，是承认有些材料必须被丢弃或降权。很多系统为了避免遗漏，把所有东西都塞进去，结果让模型在关键约束和噪声之间失去判断。",
            "hard_part_close": "所以取舍不是信息损失，而是控制注意力。一个好的 context pack 应该让模型先看到目标、边界、证据和当前状态，而不是先看到历史堆积。",
            "risk_heading": "别把上下文工程做成材料堆叠",
            "risk_body": "材料堆叠会制造一种虚假的安全感：好像模型读了很多，就应该答得更准。但如果材料之间存在冲突，或者关键约束被压到后面，长上下文反而会增加错误概率。",
            "risk_close": "判断上下文质量的关键，不是 token 用了多少，而是关键约束是否被保留、证据是否有优先级、压缩是否保留了限定条件。",
            "practice_heading": "如果今天开始做 Context Engineering，我会先做这三件事",
            "practice_step_1": "第一步，记录每次模型调用的 context pack。没有可回放的上下文，就很难判断输出跑偏到底是材料问题还是模型问题。",
            "practice_step_2": "第二步，给材料排序规则。至少区分目标、硬约束、证据、历史记录和工具结果，不要把它们混在同一段 prompt 里。",
            "practice_step_3": "第三步，评估压缩损耗。摘要不能只保留结论，还要保留条件、例外和不确定性。",
            "ending_heading": "最后，上下文质量决定 Agent 上限",
            "ending_body": "Context Engineering 的价值，不是让 prompt 更长，而是让模型在关键时刻看到正确的信息。它本质上是在管理注意力预算。",
            "ending_action": "如果你正在做长任务 Agent，建议先建立上下文记录、排序和压缩评估，再追求更大的窗口。",
            "discussion_question": "你做长任务 Agent 时，最容易被污染的是目标、约束、历史记录，还是工具结果？",
        }
    )
    return profile


def _rag_profile(topic: str) -> dict[str, str]:
    profile = _dynamic_workflow_profile(topic)
    profile.update(
        {
            "title_suffix": "从检索增强走向可评测工作流",
            "opening_scene": "很多 RAG 项目一开始都很顺：切文档、建索引、召回片段、交给模型回答。但一到真实问题，用户问法变了，文档版本变了，召回片段互相矛盾，系统就开始给出看似流畅但经不起追问的答案。",
            "opening_judgment": "Agentic RAG 的重点不是多调一次检索，而是把检索、重排、验证和追问做成一条可评测的工作流。",
            "why_heading": "为什么普通 RAG 不够用了",
            "why_body": "普通 RAG 默认检索到的片段可以直接支撑回答，但真实场景往往更复杂：材料版本不同，片段之间互相矛盾，用户问题也可能需要多跳推理。",
            "problem_heading": "RAG 的瓶颈从召回率变成了判断力",
            "problem_body": "Agentic RAG 的核心问题，是系统能否判断证据是否足够、是否冲突、是否覆盖问题意图。召回更多材料只是第一步，真正难的是对材料做结构化判断。",
            "problem_close": "如果没有证据检查，RAG 很容易把搜索结果包装成确定答案。答案越流畅，越容易掩盖检索链路里的缺口。",
            "architecture_heading": "我会怎么拆 Agentic RAG",
            "architecture_body": "我会把链路拆成 Query Planner、Retriever、Reranker、Evidence Checker、Answer Composer 和 Verifier。每个环节单独评测，避免把所有错误都归因于最后的生成模型。",
            "architecture_tradeoff": "这会让链路变长，但能让错误定位更清楚。召回不足、排序失败、证据冲突和回答越界，是四类完全不同的问题。",
            "diagram": "flowchart LR\n  A[Question] --> B[Query Planner]\n  B --> C[Retriever]\n  C --> D[Reranker]\n  D --> E[Evidence Checker]\n  E --> F[Answer Composer]\n  F --> G[Verifier]",
            "analogy": "普通 RAG 像把资料摊在桌上，Agentic RAG 更像一个研究助理：先拆问题，再找材料，再判断材料是否互相支持，最后才写结论。",
            "code_heading": "三段代码看懂 RAG 工作流",
            "code_1": "def plan_queries(question: str) -> list[str]:\n    return [question, f\"background: {question}\", f\"risk: {question}\"]",
            "code_2": "def rerank(chunks: list[dict]) -> list[dict]:\n    return sorted(chunks, key=lambda item: item.get(\"score\", 0), reverse=True)",
            "code_3": "def has_conflict(chunks: list[dict]) -> bool:\n    labels = {item.get(\"stance\") for item in chunks}\n    return \"support\" in labels and \"oppose\" in labels",
            "table_rows": "| Query Planner | 把问题拆成检索意图 | 单 query 容易漏信息 |\n| Retriever | 召回候选材料 | 没有材料就只能猜 |\n| Reranker | 过滤低质量片段 | 噪声进入回答 |\n| Evidence Checker | 检查冲突和缺口 | 答案看似确定 |\n| Verifier | 评估回答是否可用 | 幻觉难发现 |",
            "hard_part_heading": "真正难的是证据冲突，而不是召回更多",
            "hard_part_body": "RAG 系统最危险的情况，不是没有材料，而是材料之间存在细微冲突。模型很擅长把冲突写成顺滑叙述，但这会让读者误以为结论已经被充分支持。",
            "hard_part_close": "因此 Evidence Checker 应该成为主链路的一部分。它不只是找证据，还要暴露证据之间的张力和缺口。",
            "risk_heading": "别让 RAG 变成带搜索的幻觉",
            "risk_body": "带搜索的幻觉比普通幻觉更难发现，因为它看起来有材料支撑。只要检索片段相关但不足，模型就可能越过证据边界，给出过度确定的结论。",
            "risk_close": "更稳的表达方式，是把证据强度写进生成策略：证据充分时给结论，证据冲突时给分歧，证据不足时明确降低判断强度。",
            "practice_heading": "如果今天开始做 Agentic RAG，我会先做这三件事",
            "practice_step_1": "第一步，给每个问题生成多个检索意图，而不是只用用户原句检索。复杂问题通常需要背景、机制和风险三个方向。",
            "practice_step_2": "第二步，单独评测 rerank。关键证据能不能排到前面，往往比召回数量更影响最终答案。",
            "practice_step_3": "第三步，加入冲突检测。只要材料之间存在口径差异，就不要让模型输出单一确定判断。",
            "ending_heading": "最后，RAG 要从答案系统变成研究系统",
            "ending_body": "Agentic RAG 的目标不是让模型更会引用材料，而是让系统更像一个研究流程：先拆问题，再找证据，再检查冲突，最后谨慎表达。",
            "ending_action": "如果你正在做 RAG，建议先把证据链评测跑通，再增加更复杂的 Agent 协作。",
            "discussion_question": "你做 RAG 时，最难的是召回、重排、冲突检测，还是回答校验？",
        }
    )
    return profile


def _academic_frame(topic: str) -> dict[str, str]:
    lowered = topic.lower()
    if "memory" in lowered or "记忆" in topic:
        return {
            "mechanism_heading": "从研究视角看，Memory 是状态更新问题",
            "mechanism_body": "更严谨地说，Agent Memory 不是一个外置数据库，而是一个持续更新的状态估计过程。系统每接收一次新事件，都要判断它是否改变了对用户、任务或环境的理解。这里面同时存在写入误差、检索误差和使用误差：写入阶段可能把噪声当事实，检索阶段可能把过期内容排到前面，使用阶段可能把局部偏好泛化成全局规则。",
            "method_heading": "一个更稳的分析框架",
            "method_body": "我会用“对象、证据、时效、可撤销性”四个维度来评估 Memory 设计。它比单纯讨论向量库更接近问题本身，因为长期记忆的风险往往不来自存储能力不足，而来自系统无法说明一条记忆为什么存在、什么时候失效、如何被纠正。",
            "table_col_1": "分析维度",
            "table_col_2": "核心问题",
            "table_col_3": "设计含义",
            "table_rows": "| 对象 | 这条记忆描述用户、任务还是环境 | 不同对象应有不同写入规则 |\n| 证据 | 它来自用户明确表达还是模型推断 | 推断型记忆需要更低权重 |\n| 时效 | 它是短期状态还是长期偏好 | 需要 TTL 和降权机制 |\n| 可撤销性 | 用户能否查看、修改、删除 | 纠错能力决定长期可信度 |",
            "boundary_heading": "边界条件：不是所有历史都该成为记忆",
            "boundary_body": "Memory 的适用前提，是任务会跨会话延续，并且历史信息能稳定提高后续决策质量。如果任务本身是一次性的，或者历史偏好高度依赖上下文，把它沉淀为长期记忆反而会增加污染风险。换句话说，Memory 的第一原则不是“多记”，而是“少量、高置信、可纠错地记”。",
        }
    if "context" in lowered or "上下文" in topic:
        return {
            "mechanism_heading": "从机制上看，Context 是信息选择问题",
            "mechanism_body": "Context Engineering 的核心机制，是在有限注意力预算内选择哪些信息进入模型视野。窗口变大并不会消除选择问题，只会推迟它出现。真正影响输出质量的，是目标、约束、证据、历史和工具结果之间的优先级关系。",
            "method_heading": "我会用信息流而不是 prompt 模板来分析",
            "method_body": "一个更学术的拆法，是把上下文看成信息流管线：输入先被过滤，再被排序，低优先级内容被压缩，最终组装成 context pack。每一步都会引入偏差，因此系统需要记录哪些信息被丢弃、哪些信息被压缩、哪些信息被模型实际使用。",
            "table_col_1": "阶段",
            "table_col_2": "主要偏差",
            "table_col_3": "控制方法",
            "table_rows": "| Filter | 过早删除关键约束 | 保留删除理由和可回溯样本 |\n| Rank | 高噪声材料排到前面 | 引入任务相关性和证据强度 |\n| Compress | 压缩后丢失限定条件 | 保留结论和适用边界 |\n| Pack | 结构混乱导致模型误读 | 按目标、约束、证据分区 |",
            "boundary_heading": "边界条件：上下文工程不是无限扩容",
            "boundary_body": "如果一个系统的问题来自知识缺失，扩上下文可能有效；但如果问题来自目标不清、证据矛盾或工具结果不可信，扩上下文只会把更多噪声带进模型。Context Engineering 的价值，正是在这些情况下做信息取舍，而不是把材料堆得更满。",
        }
    if "rag" in lowered or "检索" in topic:
        return {
            "mechanism_heading": "从研究链路看，RAG 是证据选择与一致性检验",
            "mechanism_body": "RAG 的难点已经不只是召回相关片段，而是判断哪些片段能共同支持一个结论。真实材料经常存在版本差异、口径差异和局部矛盾。如果系统只把召回内容交给模型综合，就会把证据冲突隐藏在流畅答案里。",
            "method_heading": "我会把 RAG 拆成可评测的五个环节",
            "method_body": "更可靠的 Agentic RAG，需要把 query planning、retrieval、reranking、evidence checking 和 answer composing 分开评估。这样才能知道错误来自问题拆解、召回不足、排序失败、证据冲突，还是最终表达越界。",
            "table_col_1": "环节",
            "table_col_2": "评测问题",
            "table_col_3": "失败表现",
            "table_rows": "| Query Planning | 是否覆盖问题意图 | 召回方向一开始就错 |\n| Retrieval | 是否找到足够候选证据 | 模型只能补猜 |\n| Reranking | 关键证据是否排在前面 | 噪声影响回答 |\n| Evidence Checking | 证据是否互相支持 | 答案掩盖冲突 |\n| Answer Composing | 表达是否超过证据范围 | 形成貌似确定的幻觉 |",
            "boundary_heading": "边界条件：RAG 不能替代判断",
            "boundary_body": "RAG 能降低无依据生成，但不能自动保证结论正确。只要检索语料本身有偏、证据冲突没有暴露、或者问题需要外部实验验证，RAG 都必须降低表达强度。它更适合作为研究辅助系统，而不是最终裁判。",
        }
    return {
        "mechanism_heading": f"从机制上看，{topic} 需要先被拆成可验证假设",
        "mechanism_body": f"讨论 {topic} 时，最重要的不是马上给出实现方案，而是把它背后的机制假设讲清楚：它处理什么对象，改变了哪类关系，依赖哪些前提，又会在哪些条件下失效。只有完成这一步，文章才不会变成把旧框架套到新名词上。",
        "method_heading": f"一个更适合分析 {topic} 的框架",
        "method_body": "我会从“概念边界、机制假设、评价指标、失效模式”四个变量切入。概念边界决定它和相邻概念的差异，机制假设解释为什么它可能有效，评价指标说明如何判断效果，失效模式则限制它的适用范围。",
        "table_col_1": "变量",
        "table_col_2": "研究问题",
        "table_col_3": "写作含义",
        "table_rows": "| 概念边界 | 它和相邻概念有什么差异 | 避免换名词讲旧问题 |\n| 机制假设 | 它为什么可能有效 | 让论证从观点变成推理 |\n| 评价指标 | 怎样判断它真的更好 | 避免只靠案例感受 |\n| 失效模式 | 它在什么条件下失败 | 提升判断可信度 |",
        "boundary_heading": f"边界条件：{topic} 不是天然成立的答案",
        "boundary_body": f"{topic} 的适用性需要被论证，而不是被默认接受。如果定义不清、指标缺失、失败样本不足，它就只能停留在概念层面。真正有价值的讨论，应该主动写出它的边界和反例。",
    }


def _public_claim_paragraphs(trend: TrendCard, research: ResearchBrief) -> str:
    if "workflow" in trend.topic.lower() or "编排" in trend.topic:
        return (
            "从工程角度看，这个变化至少包含三层含义。第一，Agent 不再只是一次模型调用，而是一组可被编排的步骤。第二，真正的难点会落到运行时：状态如何保存，工具失败如何恢复，上下文如何压缩，输出如何校验。第三，社区里的失败案例往往不是模型完全不会做，而是系统没有告诉模型该在什么时候停、什么时候重试、什么时候交给人。"
        )
    if research.claims:
        readable = "；".join(_remove_internal_markers(claim.claim) for claim in research.claims[:3])
        return f"把已有讨论合在一起看，主线其实很清楚：{readable}。这些判断不需要在正文里堆编号，更重要的是把它们翻译成读者能理解的工程问题。"
    return "目前公开讨论还比较分散，所以本文会把结论降级成工程判断：先看它解决什么问题，再看它会带来哪些新复杂度。"


def _strip_public_references(body: str) -> str:
    body = re.sub(r"```(?:mermaid|plantuml)\n[\s\S]*?```", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\n##\s*参考来源[\s\S]*$", "", body).rstrip()
    body = re.sub(r"（证据：[^）]+）", "", body)
    body = re.sub(r"\(证据：[^)]+\)", "", body)
    body = re.sub(r"`?ev_[A-Za-z0-9_]+`?", "", body)
    body = re.sub(r"https?://\S+", "", body)
    return body.strip() + "\n"


def _remove_internal_markers(text: str) -> str:
    text = re.sub(r"\s*（证据：[^）]+）", "", text)
    text = re.sub(r"\s*evidence=\[[^\]]*]", "", text)
    text = re.sub(r"`?ev_[A-Za-z0-9_]+`?", "", text)
    return text.strip(" ，。")


def _short_topic(topic: str) -> str:
    return topic.split("：")[0].replace("正在", "").strip()[:24]


def _word_count_zh(text: str) -> int:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", "", text)
    return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text))


def _has_required_markdown_structure(text: str) -> bool:
    return bool(re.search(r"^# ", text, flags=re.MULTILINE)) and len(re.findall(r"^## ", text, flags=re.MULTILINE)) >= 4


def _has_academic_depth_elements(text: str) -> bool:
    has_table = bool(re.search(r"^\|.+\|\n\|[-: |]+\|", text, flags=re.MULTILINE))
    depth_markers = len(
        re.findall(
            r"概念|边界|机制|假设|限制|局限|适用|框架|评测|证据|变量|因果|研究|脉络|方法",
            text,
        )
    )
    return has_table and depth_markers >= 6


def _has_technical_blog_elements(text: str) -> bool:
    return _has_academic_depth_elements(text)


def _public_why_now(why_now: str, topic: str) -> str:
    banned = re.compile(r"该话题由\s*\d+\s*条近期来源共同指向|适合做成.*?知乎长文|近期来源共同指向")
    cleaned = banned.sub("", why_now).strip(" ，。")
    if cleaned:
        return cleaned if cleaned.endswith(("。", "！", "？")) else cleaned + "。"
    if "workflow" in topic.lower() or "编排" in topic:
        return "真正的变化不是 prompt 写法更复杂了，而是 Agent 应用开始进入需要状态、工具、记忆和评测共同协作的阶段。"
    if "memory" in topic.lower() or "记忆" in topic:
        return "真正的变化不是多存几轮对话，而是 Agent 需要知道哪些信息该保留、哪些该遗忘，以及每个判断来自哪里。"
    return "这个方向值得认真看，是因为它已经从概念讨论进入工程取舍：系统能否被追溯、被评估、被恢复，开始比单次生成效果更重要。"


def _technical_blog_requirements(topic: str, config: DirectorConfig) -> str:
    return f"""角色：你是一位在 AI Agent、LLM 应用工程和内容自动化领域有十年以上经验的资深技术专家，也是一位写作成熟的技术博主。
任务：围绕“{topic}”写一篇深度与易读性兼备的技术博客，读者包括初学者和有经验的开发者。
风格：权威但亲切，像导师和读者对话；语言清晰简洁，必要术语必须解释；多用“我/我们”的经验判断；避免空泛口号，但整体要有研究型文章的严谨度。
结构：标题要清晰有吸引力；引言 1-2 个短段落，用痛点或问题开场，并说明读者读完能解决什么；正文采用“提出问题 -> 分析问题 -> 给出方案”的层次；段落要短。
学术深度：必须写清概念定义、问题边界、机制链条、适用假设、局限性和评价方法。不要只停留在“怎么做”，还要解释“为什么这样做、在什么条件下成立、失败时说明什么”。
表达元素：不要输出 Mermaid 或 PlantUML。代码不是必需项，只有在解释 schema、算法、API 或工程接口不可替代时才加入。可以使用 Markdown 表格做概念对比、方法框架或限制条件总结。
边界：整篇文章仍要控制在中文 {config.target_min_chars}-{config.target_max_chars} 字附近；所有表格、代码和类比都必须服务论证，不要为了堆元素而堆元素。"""


def _material_brief(materials: MaterialBoard) -> str:
    lines = []
    for card in materials.cards[:10]:
        evidence = ",".join(card.evidence_ids[:3]) or "no_evidence"
        lines.append(f"- [{card.material_type}] {card.title}: {card.summary} evidence={evidence} confidence={card.confidence:.2f}")
    if materials.gaps:
        lines.append("素材缺口：" + "；".join(materials.gaps[:4]))
    return "\n".join(lines)


def _expand_to_min_chars(body: str, trend: TrendCard, research: ResearchBrief, min_chars: int) -> str:
    if _word_count_zh(body) >= min_chars:
        return body
    supplement = _topic_supplement(trend.topic)
    if "\n## 参考来源\n" in body:
        return body.replace("\n## 参考来源\n", supplement + "\n## 参考来源\n")
    return body.rstrip() + supplement


def _topic_supplement(topic: str) -> str:
    lowered = topic.lower()
    if "memory" in lowered or "记忆" in topic:
        return """

## 记忆系统要留下纠错入口

Memory 最容易被忽视的一点，是用户必须能纠错。一个偏好被误写入，或者一个事实已经过期，系统不能只靠下一次模型“自己意识到”。更可靠的做法是给每条记忆保留来源、写入时间、置信度和最近使用记录，让人能删除、降权或者改写它。

这会让 Memory 从“黑箱历史”变成“可维护资产”。当 Agent 下次引用某条记忆时，它应该能解释为什么这条信息被选中，而不是把旧上下文悄悄塞进推理过程。
"""
    if "context" in lowered or "上下文" in topic:
        return """

## 上下文也需要复盘指标

Context Engineering 不能只看最后答案好不好，还要看上下文包本身是否健康。比如关键约束有没有进入 prompt，低价值材料占了多少 token，被压缩的信息是否还能保留判断依据。这些指标比“窗口够不够大”更接近真实问题。

我会把每次模型调用的 context pack 存成 artifact。这样一旦输出跑偏，就能回头看是材料排序错了、压缩过度了，还是历史记录污染了当前任务。
"""
    if "rag" in lowered or "检索" in topic:
        return """

## 评测要覆盖检索链路，而不是只评答案

Agentic RAG 的评测不能只问“最终回答像不像”。更关键的是拆开看：query plan 有没有覆盖问题意图，召回片段是否足够，重排有没有把关键证据放到前面，verifier 有没有发现冲突。只评答案，很容易把检索问题误判成写作问题。

我会准备一组带标准证据的测试问题，每次修改切分、索引、重排或验证策略后都跑一遍。RAG 系统真正的稳定性，是链路每一段都能被单独解释。
"""
    if "dynamic workflow" in lowered or "自适应编排" in topic:
        return """

## 动态路由要有回放能力

Dynamic Workflow 上线后，我最关心的不是它能分出多少路径，而是每次分支能不能回放。系统要记录当时的状态、触发条件、候选动作和最终决策。否则同一个任务今天走 verify，明天走 handoff，团队却不知道差异来自哪里。

回放能力会让动态编排变得可调试。你可以统计哪些分支最常触发，哪些工具失败后最适合降级，哪些场景应该更早进入人工审核。没有这层记录，动态只会变成难以复现的偶然行为。
"""
    return """

## 把概念讨论变成可检验问题

一个新主题如果只停留在“看起来很有前景”，很难形成真正有深度的文章。更好的写法，是把它拆成可以检验的问题：定义是否清楚，机制是否成立，评价指标是否可靠，失败样本是否能解释。

这样写出来的文章不会依赖固定模板。主题可以不断变化，但每篇文章都必须重新建立自己的概念边界、机制链条和判断标准。
"""


def _trim_to_max_chars(body: str, max_chars: int) -> str:
    if _word_count_zh(body) <= max_chars:
        return body
    marker = "\n## 参考来源\n"
    if marker not in body:
        tokens = re.findall(r".", body, flags=re.DOTALL)
        return "".join(tokens[: max(1200, max_chars - 80)]).rstrip()
    main, refs = body.split(marker, 1)
    tokens = re.findall(r".", main, flags=re.DOTALL)
    trimmed = "".join(tokens[: max(1200, max_chars - 280)]).rstrip()
    return f"{trimmed}\n\n{marker}{refs}"


def json_dumps_compact(value: Any) -> str:
    text = __import__("json").dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= 1800 else text[:1797] + "..."
