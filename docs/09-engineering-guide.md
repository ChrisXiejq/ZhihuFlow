# 工程规范

## 1. 推荐目录

```text
RedFlow/
  apps/
    web/
    api/
    worker/
  packages/
    domain/
    contracts/
    ui/
  infra/
    compose/
    migrations/
  docs/
  evals/
  scripts/
  .github/workflows/
```

## 2. 分支与提交

- `main`：始终可部署。
- `feat/<scope>`、`fix/<scope>`、`docs/<scope>`：短生命周期分支。
- Commit 使用 Conventional Commits：`feat(agent): add creative brief schema`。
- PR 必须关联需求、测试和风险；涉及 Prompt/策略变更需附评测结果。

## 3. 测试金字塔

- 单元：领域规则、Schema、风险规则、权限。
- 集成：数据库、队列、对象存储、Publisher mock。
- 契约：API OpenAPI、事件 payload、模型 JSON Schema。
- E2E：创建内容 → 生成 → 审核 → 导出。
- Eval：Golden set、轨迹和安全红队。

## 4. CI 必需检查

```text
format/lint
typecheck
unit + integration tests
API contract validation
small eval suite
secret scan
dependency vulnerability scan
container build
```

主干合并后运行完整评测集、构建镜像、发布测试环境。任何生产发布须附数据库迁移回滚说明。

## 5. ADR 模板

```markdown
# ADR-XXX: 标题
状态：Proposed | Accepted | Superseded
背景：
决策：
替代方案：
后果：
日期：
```

## 6. Definition of Done

一项能力完成必须满足：需求验收标准实现；权限/错误路径覆盖；日志不含密钥/PII；有单元或集成测试；如涉及模型，有至少一个评测案例；前端有空态和失败态；文档更新。
