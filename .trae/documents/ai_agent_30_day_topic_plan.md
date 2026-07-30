# AI Agent 30 天双更选题规划

## 目标

未来一个月每天发布两篇围绕 AI Agent 的文章，形成稳定的内容系列：

- 上午偏学术与理论：概念边界、研究脉络、评测体系、理论限制。
- 晚上偏工程与实践：架构设计、实现方法、系统拆解、真实踩坑。
- 每周穿插 1-2 篇实践型文章，增强工程可信度。
- 每 7 天做一次主题串联，形成系列感和账号记忆点。

## 选题原则

1. 围绕最新 AI Agent 的学术和工程进展。
2. 兼顾讨论热度和实际价值，不追纯概念热词。
3. 不把所有主题写成 Agent Workflow 或 Runtime，必须围绕主题本身建立边界。
4. 每篇文章至少讲清一个机制问题、一个评价标准和一个限制条件。
5. Mermaid 和代码不是必需项；只有必要时才加入代码。

## 30 天选题日历

| 天 | 上午：学术 / 理论向 | 晚上：工程 / 实践向 |
|---|---|---|
| Day 1 | AI Agent 到底是什么：从 LLM、Chatbot 到 Agent 的概念边界 | 做 Agent 系统前，为什么要先设计状态机而不是先写 Prompt |
| Day 2 | Agentic Workflow：为什么单次 Prompt 工程正在失效 | 一个最小可用 Agent Runtime 应该包含哪些模块 |
| Day 3 | Multi Agent 的本质：多角色分工，还是协作治理问题 | 如何设计 Coordinator + Specialist + Critic 的多 Agent 架构 |
| Day 4 | Agent Memory 为什么不是“保存聊天记录” | 如何设计 Memory 的写入、检索、更新和遗忘机制 |
| Day 5 | Context Engineering：Prompt Engineering 之后的新基础设施 | 如何构建 Context Pack：目标、约束、证据、历史和工具结果 |
| Day 6 | Agentic RAG：RAG 为什么正在从检索系统变成研究系统 | Query Planning + Rerank + Evidence Check 的 RAG 链路 |
| Day 7 | Agent 评测为什么比模型评测更难 | 如何用 SWE-bench、WebArena、OSWorld、GAIA 理解 Agent 能力边界 |
| Day 8 | Tool Use 的理论问题：Agent 如何决定“该不该调用工具” | 设计 Tool Contract 时最容易踩的 5 个坑 |
| Day 9 | MCP 为什么重要：工具协议正在改变 Agent 工程形态 | 如何把 MCP 理解成 Agent 的“外设总线” |
| Day 10 | A2A / Agent 通信协议：多 Agent 协作需要怎样的语言 | 多 Agent 系统里的消息协议、共享状态和冲突仲裁 |
| Day 11 | Dynamic Workflow：Agent 为什么需要运行时决策能力 | continue / verify / retry / handoff 四类路由策略 |
| Day 12 | Agent 的失败模式：幻觉、循环、越权、遗忘、上下文污染 | 如何给 Agent 加 Policy Gate 和 Human Handoff |
| Day 13 | Long-Horizon Agent：长任务为什么特别难 | Checkpoint、Event Log、Replay 如何让 Agent 可恢复 |
| Day 14 | Agent Memory 评测：LoCoMo、LongMemEval、BEAM 到底测什么 | 如何为自己的 Agent 设计 Memory Eval |
| Day 15 | Graph Memory vs Vector Memory：Agent 记忆应该用图还是向量 | 什么时候用向量库，什么时候用知识图谱 |
| Day 16 | Tool-based Memory：为什么记忆应该成为工具，而不是预检索结果 | 把 retrieve / update / delete / navigate 设计成 Memory Tools |
| Day 17 | Multi Agent 的成本问题：更多 Agent 一定更好吗 | 如何判断一个任务是否值得拆成多个 Agent |
| Day 18 | Agent 安全：Prompt Injection 在工具调用时代为什么更危险 | 工具权限、沙箱执行和不可逆操作确认怎么做 |
| Day 19 | Agent 的可观测性：为什么 trace 比最终答案更重要 | Agent Trace 应该记录哪些事件 |
| Day 20 | LLM-as-Judge 可靠吗：Agent 质量评估的理论边界 | 如何设计一个内容 Agent 的质量评分体系 |
| Day 21 | Agentic Coding：AI 编程 Agent 的真实能力边界 | 从 SWE-bench 看代码 Agent 的定位、修复和验证链路 |
| Day 22 | Computer Use Agent：从浏览器 Agent 到 OSWorld 的能力迁移 | 桌面 Agent 为什么比网页 Agent 更难工程化 |
| Day 23 | Agent 与人协作：Human-in-the-loop 不是妥协，而是系统能力 | 如何设计 Review Studio，让人审核 Agent 的关键决策 |
| Day 24 | Self-Reflection 为什么经常失效：Agent 自我纠错的边界 | Evaluator-Optimizer 模式什么时候有效 |
| Day 25 | Planning Agent 的理论困境：计划越长，错误越会级联 | 如何做 bounded execution，避免 Agent 无限循环 |
| Day 26 | Agent 经济学：成本、延迟、准确率之间的 Pareto 权衡 | 如何给 Agent 系统做 cost-quality dashboard |
| Day 27 | Enterprise Agent：企业落地难在权限、数据和流程 | 企业 Agent 架构：RBAC、审计、工具网关、数据隔离 |
| Day 28 | Agent 与知识工作：它替代的是任务，还是工作流的一部分 | 搭一个研究 Agent：自动生成 evidence table 和文章蓝图 |
| Day 29 | Agent OS：未来 Agent 会不会变成一种操作系统层 | 从 Memory、Tool、Context、Workflow 看 Agent OS 的雏形 |
| Day 30 | 下一个阶段的 AI Agent：从 Demo 到可验证系统 | 月度总结：如何搭建一个真正能长期运行的内容 Agent 系统 |

## 每周节奏

### Week 1：建立基础认知

重点讲清 Agent 的基本边界、workflow、multi-agent、memory、context、RAG 和评测。

目标是让读者形成一个基础判断：Agent 不是“会调用工具的聊天机器人”，而是一套带状态、工具、记忆、评测和边界的运行系统。

### Week 2：进入系统工程

重点讨论 tool use、MCP、A2A、dynamic workflow、失败模式、长任务恢复和 memory eval。

目标是把内容从概念介绍推进到工程系统设计。

### Week 3：讨论能力边界

重点覆盖 memory architecture、tool-based memory、multi-agent 成本、安全、可观测性、LLM-as-Judge 和 coding agent。

目标是展示你对“Agent 为什么难落地”的理解，而不是只讲热门框架。

### Week 4：面向真实落地

重点讨论 computer use、human-in-the-loop、self-reflection、planning、成本、企业落地、知识工作和 Agent OS。

目标是把前面的技术点收束成一个长期可运行的 Agent 产品观。

## 单篇文章建议结构

每篇文章建议使用以下结构，但不要机械套模板：

1. 用一个具体问题开场。
2. 定义主题边界：它是什么，不是什么。
3. 解释机制链条：为什么这个主题现在重要。
4. 给出评价标准：怎么判断它真的有效。
5. 写出失败模式：在哪些条件下会失效。
6. 落到工程取舍：如果要实现，应先做什么。
7. 结尾提出一个讨论问题，引导评论。

## 内容质量要求

- 不要写成新闻摘要。
- 不要写成概念百科。
- 不要为了显得技术而强塞代码。
- 不要输出 Mermaid / PlantUML。
- 不要暴露 evidence_id、URL 或参考来源列表。
- 每篇文章都要有作者判断，而不只是“这个方向很重要”。
- 学术深度优先看概念边界、机制假设、评价方法、局限条件。
- 工程深度优先看系统边界、状态管理、工具契约、失败恢复、可观测性。

## 实践型文章候选补充

如果某天需要更强实践感，可以从下面替换：

- 我会如何从零设计一个内容 Agent。
- 如何给 Agent 系统设计 event log。
- 如何让 Agent 输出可回放、可复盘。
- 如何设计一个最小版 Memory Store。
- 如何设计 Agent 的工具权限模型。
- 如何用 Policy Gate 拦截高风险输出。
- 如何给 Agent 文章生成做质量评分。
- 如何让 Multi Agent 不变成互相聊天。
- 如何判断一个 Agent 系统是否过度设计。
- 如何把 AI Agent 项目写进简历。

## 执行建议

每天不要临时想题。建议提前 3 天生成草稿，发布当天只做人工审稿和标题微调。

推荐节奏：

- T-3：生成初稿。
- T-2：补充研究材料和反例。
- T-1：人工审稿，删 AI 味，调整标题。
- T：发布，并记录阅读、赞藏、评论和关注转化。

每周复盘一次：

- 哪类标题点击高。
- 哪类主题收藏高。
- 哪类文章评论多。
- 哪些主题过于抽象，需要补实践。
- 哪些实践文缺少理论高度，需要补研究脉络。

