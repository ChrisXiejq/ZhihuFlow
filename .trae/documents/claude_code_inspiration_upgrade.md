# Claude Code 设计借鉴与 ZhihuFlow 改造记录

## 背景

这次改造参考了两类材料：

- 内部文档中对 Claude Code Skills、SubAgent、attachment、prompt caching、Microcompact、cache_edits、context offloading 的解析。
- 公开 Claude Code 架构分析资料中关于 Agent Loop、QueryEngine、Tool System、Permission、Memory、SubAgent、Context Management 的设计拆解。

核心判断是：Claude Code 的优势不在于“模型会写代码”或“Agent Loop 很复杂”。Agent Loop 本身只是模型调用、工具执行、结果回填的循环。真正值得借鉴的是 loop 外围的 Harness 工程：上下文如何组织，工具如何治理，子 Agent 如何隔离，动态能力如何注入，旧结果如何压缩，失败如何回放。

## Claude Code 值得借鉴的设计点

### 1. Static First, Dynamic Last

Claude Code 很重视 Prompt Cache，因此会尽量让稳定内容排在前面，把动态内容放在后面，减少缓存前缀被频繁打碎。

对 ZhihuFlow 的启发：

- 稳定写作规则、工具契约、skill meta 属于可复用上下文。
- 每次运行变化的研究材料、素材卡片、文章蓝图属于动态上下文。
- 不应该把所有内容混成一个超长 prompt。

### 2. Attachment 动态上下文注入

Claude Code 会把 skill list、subagent list 等运行时信息作为 attachment 注入 messages，而不是长期写死进系统提示词。

对 ZhihuFlow 的启发：

- 主题相关写作策略不应该继续硬编码在 Python 分支里。
- 系统应该能根据 topic 动态选择 playbook，并以 attachment 形式注入。
- 新主题可以通过新增 Markdown skill 扩展，而不是改 writer 分支。

### 3. Progressive Skill Loading

Claude Code 的 Skill 机制本质是按需加载 prompt 模板：先让模型知道有哪些 skill，再在需要时加载 skill body。

对 ZhihuFlow 的启发：

- `SkillRegistry` 应支持 name / description / tags 的 meta brief。
- 运行时根据 topic 选择相关 skill。
- Writer 只加载相关 skill 的正文，避免所有 skill 混在一起污染主题。

### 4. SubAgent Isolation

Claude Code 的 SubAgent 本质是通过一次工具调用启动另一个独立 Agent Loop。父 Agent 不消费子 Agent 的完整过程，只消费最终结论。

对 ZhihuFlow 的启发：

- 研究、素材、蓝图、写作、编辑、分发应保持角色边界。
- 子 Agent 的探索过程不应该全部塞进 Writer 上下文。
- Writer 应消费结构化的 material board、blueprint 和 context pack，而不是研究全过程。

### 5. Microcompact / Context Offloading

Microcompact 的关键不是“压缩很多”，而是高频、低成本、规则驱动地清理低价值旧 tool_result。

对 ZhihuFlow 的启发：

- 旧来源全文、低优先级素材、工具日志不应每次都进入写作 prompt。
- Context Pack 只保留当前写作需要的信息。
- 完整材料保留在 workflow artifact，必要时再回放。

### 6. Harness Report

Claude Code 的优势可以被解释为一套 Harness，而不是一次模型输出。ZhihuFlow 也应该显式记录本次运行用了哪些工程机制。

对 ZhihuFlow 的启发：

- 每次运行产出 `harness_report`。
- 记录 selected skills、attachments、context budget、offloaded items、borrowed patterns。
- 面试时可以直接展示这不是简单 prompt demo，而是可复盘的 Agent 系统。

## 本次已落地能力

### 1. SkillRegistry 增强

文件：

- `zhihuflow/runtime/skills.py`

新增能力：

- 解析 skill description / tags。
- 输出 skill meta brief。
- 根据 topic 自动选择相关 skills。
- 生成 `<system-reminder>` 风格 attachment。

现在新增主题不需要改 Python 分支，可以通过新增：

```text
skills/builtin/<skill-name>/SKILL.md
skills/custom/<skill-name>/SKILL.md
```

来扩展主题策略。

### 2. ContextPacker

文件：

- `zhihuflow/runtime/context.py`

新增能力：

- 构造 `ContextPack`。
- 注入 `skill_meta_list`、`selected_skill_bodies`、`tool_contract_summary`、`research_claim_pack`、`material_microcompact`、`article_blueprint_pack`。
- 当上下文超预算时压缩 attachment，并保留 offloaded item 记录。

### 3. Director 新增 Context Pack 阶段

文件：

- `zhihuflow/app/director.py`

新增工作流步骤：

```text
assemble_context_pack
harness_report
```

新的主链路变为：

```text
discover_trends
choose_trend
research
build_material_board
design_article_blueprint
assemble_context_pack
write_article
edit_article
evaluate_quality
policy_check
prepare_distribution
harness_report
```

### 4. Writer 消费 Context Pack

文件：

- `zhihuflow/content/writer.py`

新增行为：

- Writer 不再只依赖硬编码 skill 列表。
- Writer 会使用 `context_pack.selected_skills`。
- Prompt 中加入 Claude-Code-inspired 动态上下文包。
- 主题策略可以通过 Markdown skill 影响生成，不需要每个主题都改 writer。

### 5. 新增内置 Playbook

新增文件：

- `skills/builtin/agent-harness-engineering/SKILL.md`
- `skills/builtin/context-offloading/SKILL.md`
- `skills/builtin/subagent-orchestration/SKILL.md`

覆盖主题：

- Claude Code 源码解析
- Agent Harness
- Context Offloading
- Microcompact
- Multi Agent / SubAgent
- Coordinator + Specialist + Critic

### 6. 修正旧写作 Skill

文件：

- `skills/builtin/zhihu-writing/SKILL.md`

修正点：

- 不再要求公开 evidence IDs。
- 不再要求输出 References。
- 不再要求 Mermaid / PlantUML。
- 代码块改为按需出现。

## 新增测试

文件：

- `tests/test_pipeline.py`

新增覆盖：

- `test_skill_registry_selects_topic_playbooks_without_code_branch`
- `test_context_packer_builds_attachments_and_microcompact_summary`
- pipeline 产物中必须包含 `context_pack` 和 `harness_report`

验证结果：

```bash
python3 -m unittest discover -s tests -v
# Ran 20 tests
# OK
```

## 面试表达

可以这样总结这次改造：

> 我参考 Claude Code 的 Harness 设计，把 ZhihuFlow 从“多 Agent 内容生成链路”进一步升级成“可扩展的内容 Agent Harness”。具体包括渐进式 Skill 加载、动态 attachment、Context Pack、Microcompact 风格素材压缩、Workflow Journal Replay 和 Harness Report。这样新主题不需要改代码分支，只需要新增 Markdown playbook；同时每次运行都能解释本次用了哪些上下文、哪些材料被压缩、哪些 skill 被选择。

## 后续可继续增强

- 真正实现 artifact pointer：超预算素材只保留 artifact id，按需再取。
- 给 Writer 增加 Critic retry：Critic block 后回到 Writer 做局部重写。
- 给 Context Pack 加评分：记录哪些 attachment 对最终文章质量最有帮助。
- 给 SkillRegistry 增加热加载：检测 `skills/custom` 新文件并写入运行事件。
- 给 Web Console 增加 Harness Report 展示页。

