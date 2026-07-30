---
description: 上下文预算、Context Offloading、Microcompact、缓存友好 Prompt 组织的分析框架。
tags: context offloading microcompact cache prompt-budget compaction claude-code
---

# Context Offloading Skill

## Goal

解释长任务 Agent 为什么不能把所有历史、工具结果和材料都塞进上下文，以及如何用预算、摘要、指针和 artifact 管理信息流。

## Core Ideas

- 上下文窗口是稀缺资源，窗口变大不等于组织变好。
- 可重取、低价值、已经被模型消化的 tool result 应该被压缩或替换成指针。
- 本地 artifact 保存完整数据，模型上下文只保留当前决策需要的信息。
- 压缩不能只保留结论，还要保留条件、限制和不确定性。

## Article Angles

- Microcompact 的价值不是“压得多”，而是高频、低成本、规则驱动。
- cache-friendly prompt 组织要求稳定内容在前，动态内容在后。
- 对内容 Agent 来说，旧来源全文、搜索日志、低优先级素材不应每次都进入写作 prompt。
- 好的 context pack 应该包含目标、硬约束、核心 claims、冲突、缺口和当前阶段。

## Failure Modes

- 历史材料过多导致主题漂移。
- 旧工具结果污染新任务。
- 摘要丢失限定条件，导致过度确定表达。
- 所有材料平铺进 prompt，模型看似读很多，实际抓不住主线。

