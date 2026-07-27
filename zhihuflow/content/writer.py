from __future__ import annotations

import re
from typing import Any, Optional

from zhihuflow.app.config import DirectorConfig
from zhihuflow.core.schemas import ArticlePackage, ResearchBrief, TrendCard
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

    def write(self, trend: TrendCard, research: ResearchBrief, trace_id: str, config: DirectorConfig) -> ArticlePackage:
        titles = [
            f"{trend.topic}：为什么它会是下一轮 AI 产品的分水岭？",
            f"别再只盯模型了，{_short_topic(trend.topic)} 真正拼的是工程系统",
            f"我为什么认为 {_short_topic(trend.topic)} 会影响 AI 求职和产品机会",
        ]
        source_lines = "\n".join(f"- [{ref.evidence_id}] {ref.title} ({ref.source}) {ref.url}" for ref in research.sources[:8])
        claim_lines = "\n".join(f"- {claim.claim} evidence={claim.evidence_ids} confidence={claim.confidence}" for claim in research.claims)
        skill_brief = "\n\n".join(skill.brief() for skill in self.skill_registry.load_many(["zhihu-writing", "human-writing", "deep-research"]))
        tool_contracts = json_dumps_compact(self.tool_registry.contracts())
        memory_brief = self.memory.briefing() if self.memory else ""
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
            f"证据：\n{source_lines}\n"
            f"Claims：\n{claim_lines}\n"
            "\n写作任务：生成一篇完整的知乎风格技术文章。\n"
            "硬性要求：\n"
            "1. 只输出 Markdown 文章正文，不输出原文分析、优化策略、自检说明。\n"
            "2. 正文字数必须在目标区间内，不能短稿。\n"
            "3. 不要套固定报告结构，不要机械编号，不要使用“首先/其次/最后/综上所述”。\n"
            "4. 开头 200 字内必须出现一个明确判断或具体场景，不要泛泛介绍背景。\n"
            "5. 每个核心观点至少落到一个具体场景、工程细节或反例。\n"
            "6. 商业转化只做克制 CTA，不承诺收益。\n"
            "7. 文末保留“参考来源”二级标题，列出 evidence_id、标题和链接。"
        )
        generated = self.model.generate(
            system=(
                "你是一个有真实 Agent 工程经验的中文技术作者。"
                "你的文章应该有判断、有现场感、有取舍，不要像咨询报告或 AI 模板。"
                "只能基于证据写作，商业表达必须克制。"
            ),
            prompt=prompt,
            temperature=0.72,
        )
        body = self._finalize_article(trend, research, generated, config)
        return ArticlePackage(
            topic=trend.topic,
            titles=titles,
            opening_hook=f"如果只把 {trend.topic} 理解成一个新名词，大概率会错过它背后的工程机会。",
            outline=[
                "先给结论：这不是概念热，而是工程边界变化",
                "为什么现在发生：趋势证据与技术动因",
                "核心架构：搜索、记忆、工具契约、工作流与评测",
                "普通创作者/求职者怎么抓住机会",
                "风险和边界：别把 Agent 做成不可审计的黑箱",
            ],
            body_markdown=body,
            citations=research.sources[:8],
            commercial_angle="用高质量技术长文建立专业可信度，再把读者导向可交付的咨询、课程、工具模板或项目展示。",
            cta="如果你正在做 AI Agent 项目，可以先从一条可回放的 event log 和一份可审计的 evidence table 开始，而不是先堆模型调用。",
            trace_id=trace_id,
        )

    def _finalize_article(self, trend: TrendCard, research: ResearchBrief, generated: str, config: DirectorConfig) -> str:
        body = strip_model_meta(generated).strip()
        if not body.startswith("# "):
            body = f"# {trend.topic}\n\n{body}"
        if _word_count_zh(body) < config.target_min_chars or not _has_required_markdown_structure(body):
            body = self._fallback_structured_article(trend, research, config)
        if "## 参考来源" not in body and "参考来源" not in body:
            body = f"{body.rstrip()}\n\n## 参考来源\n\n{_citation_lines(research)}\n"
        return _trim_to_max_chars(body, config.target_max_chars)

    def _fallback_structured_article(self, trend: TrendCard, research: ResearchBrief, config: DirectorConfig) -> str:
        claims = research.claims or []
        claim_text = "\n".join(f"- {claim.claim}（证据：{', '.join(claim.evidence_ids) or '待补充'}）" for claim in claims)
        if not claim_text:
            claim_text = "- 当前公开证据不足，本文把结论降级为工程判断。"
        scenes = [
            "我见过不少团队把 Agent 项目做成一个很漂亮的 demo：输入一个任务，模型调用几次工具，最后吐出一段看起来完整的答案。演示时没问题，真正上线后问题才开始暴露。用户追问一句“这个结论来自哪里”，系统给不出证据；任务跑到一半失败，没人知道该从哪一步恢复；文章生成出来像标准答案，但没有作者判断，也没有工程现场感。",
            f"这就是我认为 {trend.topic} 值得写的原因。它不是一个单独的新名词，而是在提醒我们：AI 产品的竞争点正在从“会不会调用模型”，转向“能不能把研究、证据、记忆、工具和人工审核组成一个可持续运行的系统”。",
        ]
        body = f"""# {trend.topic}：真正的分水岭不是模型，而是运行时

{scenes[0]}

{scenes[1]}

## 为什么这个话题现在值得认真看

{research.why_now}

如果把这个趋势只理解成“模型又变强了”，会漏掉更关键的变化。模型能力提升之后，瓶颈反而转移到了工程侧：选题从哪里来，证据怎么保存，claim 如何和来源绑定，生成失败后如何恢复，文章发出去之后反馈怎么回到系统里。这些东西不够性感，但它们决定一个 Agent 系统能不能长期稳定地产出内容。

对知乎创作者来说，这个变化尤其重要。热点新闻人人都能转述，真正能沉淀信任的是判断质量。判断质量来自三个东西：材料足够新，证据足够清楚，作者敢说清楚自己赞成什么、反对什么、担心什么。

## 我更关心的不是自动写作，而是证据链

一个商业可用的内容 Agent，第一层不应该是 Writer，而应该是 Research。系统需要先把来源保存下来，再从来源里抽 claim。这里有个很容易被忽视的区别：LLM 抽出来的是 claim，不是 truth。

{claim_text}

如果系统没有这层区分，文章会很快滑向“看起来很确定”的幻觉。更好的做法是把每个 claim 都挂到 evidence_id 上，同时保留 confidence 和 status。这样写作者可以知道哪些结论能强写，哪些只能弱表达，哪些需要人工补资料。

## 一个能长期工作的 ZhihuFlow 应该怎么跑

我会把链路拆成几个阶段。TrendScout 负责从公开来源里发现近期话题；ParallelResearchOrchestrator 把同一个选题拆成论文、工程、社区、商业四个视角并行研究；MemoryStore 记录 event log、workflow journal、artifact 和 claim graph；ZhihuWriter 再基于 Skill、证据、长期记忆生成文章；最后由 QualityEvaluator 和 PolicyGate 做质量与风险门禁。

这个结构比“搜一下然后让模型写”重得多，但它解决了真实使用里的问题。每天生成文章时，系统不会只给你一个 Markdown 文件，而是同时留下 trace、质量分、policy finding、证据图谱和后续反馈入口。你可以复盘为什么选这个题，为什么文章被判为证据不足，为什么某类标题转化更好。

## 对求职项目来说，复杂度要落在正确地方

如果只是做一个套壳写作工具，面试时很难讲出技术深度。真正值得展示的是 Harness：workflow replay、context offloading、tool contract、sandbox artifact、quality eval、feedback loop。这些模块能说明你不是只会调 API，而是在把 LLM 应用做成工程系统。

我不太建议一上来做复杂 UI。更务实的路线是先把 CLI、数据库、调度、邮件投递跑稳，再逐步做 Review Studio。面试官真正关心的是系统边界是否清晰、失败是否可恢复、质量是否可评估，而不是页面是否花哨。

## 内容转化不能靠承诺 GMV

提升 GMV 这件事不能包装成确定性结果。更可信的说法是：ZhihuFlow 提升的是选题研究效率、证据组织能力、内容一致性和复盘速度。最终转化仍然取决于账号定位、产品供给、读者信任和分发环境。

所以我会把 CTA 写得克制一点：如果读者正在做 Agent 项目，可以先从 event log、evidence table 和 claim graph 开始，而不是先堆模型调用。这种表达不会显得急着卖东西，但会让真正有需求的人知道你有可交付能力。

## 参考来源

{_citation_lines(research)}
"""
        return _expand_to_min_chars(body, trend, research, config.target_min_chars)


def _citation_lines(research: ResearchBrief) -> str:
    return "\n".join(f"- `{ref.evidence_id}`：[{ref.title}]({ref.url})，来源：{ref.source}" for ref in research.sources[:8])


def _short_topic(topic: str) -> str:
    return topic.split("：")[0].replace("正在", "").strip()[:24]


def _word_count_zh(text: str) -> int:
    text = re.sub(r"`[^`]+`", "", text)
    return len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text))


def _has_required_markdown_structure(text: str) -> bool:
    return bool(re.search(r"^# ", text, flags=re.MULTILINE)) and len(re.findall(r"^## ", text, flags=re.MULTILINE)) >= 4


def _expand_to_min_chars(body: str, trend: TrendCard, research: ResearchBrief, min_chars: int) -> str:
    if _word_count_zh(body) >= min_chars:
        return body
    supplement = f"""

## 我会怎么把它放进真实运营流程

真正上线时，我会让系统每天固定时间启动一次任务，但不会自动发布。它应该先生成文章草稿、质量报告和证据表，然后通过邮件发给人审核。人确认后再决定是否发布到知乎。这个设计看起来保守，但对一个商业账号更合理：账号信用比单篇文章效率更重要。

下一步可以把知乎阅读、赞藏、评论、私信线索和收入反馈写回长期记忆。几周之后，系统就不只是“会写文章”，而是能回答一个更有价值的问题：哪些技术角度更容易建立信任，哪些标题带来收藏，哪些 CTA 带来真实咨询。
"""
    return body.replace("\n## 参考来源\n", supplement + "\n## 参考来源\n")


def _trim_to_max_chars(body: str, max_chars: int) -> str:
    if _word_count_zh(body) <= max_chars:
        return body
    marker = "\n## 参考来源\n"
    if marker not in body:
        return body
    main, refs = body.split(marker, 1)
    tokens = re.findall(r".", main, flags=re.DOTALL)
    trimmed = "".join(tokens[: max(1200, max_chars - 280)]).rstrip()
    return f"{trimmed}\n\n{marker}{refs}"


def json_dumps_compact(value: Any) -> str:
    text = __import__("json").dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= 1800 else text[:1797] + "..."
