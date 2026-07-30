---
description: Agent Harness 工程分析写作框架，适合 Claude Code、DeerFlow、OpenHands、Coding Agent、Agent Runtime 等主题。
tags: agent harness claude-code runtime workflow context tool permission memory
---

# Agent Harness Engineering Skill

## Goal

把 Agent 文章从“模型会调用工具”提升到 Harness 工程层：上下文、工具、权限、状态、回放、压缩、评测和人类控制权。

## Lens

- Agent Loop 往往只是 while 循环，真正复杂度在 loop 外围。
- 关注确定性基础设施，而不是把所有能力归因给模型。
- 用“系统如何长期稳定运行”替代“模型一次能生成什么”。

## Key Questions

- 上下文如何进入、保留、压缩和退出模型视野？
- Tool schema、权限、风险等级和执行结果如何被记录？
- 子 Agent 是否隔离上下文，只把最终结论合并回主线？
- 失败后能不能 replay，能不能定位是哪一步错了？
- 质量门禁、policy gate、人类接管放在哪些节点？

## Claude-Code-Inspired Patterns

- static-first dynamic-last：稳定系统指令和工具契约在前，动态材料放后面。
- attachment：运行时动态信息以附加上下文注入，而不是改系统提示词主干。
- progressive skill loading：先给 skill meta，再按需加载完整 skill body。
- microcompact：旧工具结果和低价值材料只保留摘要/指针，完整信息留在 artifact。
- subagent isolation：子 Agent 用独立上下文探索，父 Agent 只消费结论。
- permission gate：工具调用要先过风险与权限检查，尤其是写入、发布、外部操作。

## Writing Rules

- 不要写成“Claude Code 很厉害”的产品介绍。
- 要分析为什么这些机制有工程价值，以及它们解决了什么失效模式。
- 必须写出至少一个反例：如果没有该机制，系统会怎样失败。
- 对 ZhihuFlow 这类内容 Agent，要落到选题、研究、素材、写作、评估、投递链路。

