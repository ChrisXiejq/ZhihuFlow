---
description: Multi-Agent、SubAgent、Coordinator、Specialist、Critic、隔离上下文与 fan-in 汇总的写作框架。
tags: multi-agent subagent coordinator specialist critic orchestration fan-in
---

# SubAgent Orchestration Skill

## Goal

分析多 Agent 系统时，不要停留在“多个角色互相聊天”，而要解释职责边界、隔离上下文、共享状态、冲突仲裁和结果合并。

## Core Model

- Coordinator：定义目标、拆任务、分配上下文、控制流程和异常路径。
- Specialist：在明确输入/输出契约下完成局部任务。
- Critic：独立评估目标一致性、证据边界、风险和格式约束。
- Shared State：保存目标、硬约束、当前阶段、已有产物、未解决问题。

## Claude-Code-Inspired Patterns

- SubAgent 本质是一次 tool call 里启动另一个独立 Agent Loop。
- 父 Agent 不应该消费子 Agent 的完整过程，只消费结构化最终结论。
- 子 Agent 的工具视图和系统提示可以不同，权限也应该更窄。
- Fan-in 合并必须保留来源、置信度、冲突和未解决问题。

## Evaluation

- 多 Agent 是否降低了主上下文污染？
- 失败是否更容易定位到某个角色或阶段？
- Critic 的结论是否能驱动 revise/block，而不是只给泛泛建议？
- 增加 Agent 是否真的提升质量，还是只增加成本和延迟？

