# TST Chain v0.5 — Workflow

v0.5 定义规划生命周期的**原子状态事务协议**。它可以在内存参考实现中确定状态迁移、权限、文档、签名、规则门控、版本前置条件和幂等语义，但不声称提供持久化区块链账本。

## 前置条件顺序

1. Request ID / idempotency
2. Target exists or create semantics
3. `expected_version`
4. Authorization / permission
5. State transition
6. Required document
7. Required signature
8. Rule evaluation gate
9. Atomic state mutation + audit result

这一顺序是协议的一部分：例如 stale version 应返回 `VERSION_CONFLICT`，不继续尝试修改状态。

## 稳定错误

- `TST-WF-001` / `UNAUTHORIZED`
- `TST-WF-002` / `INVALID_STATE_TRANSITION`
- `TST-WF-003` / `MISSING_DOCUMENT`
- `TST-WF-004` / `MISSING_SIGNATURE`
- `TST-WF-005` / `RULE_CONFLICT`
- `TST-WF-006` / `VERSION_CONFLICT`
- `TST-WF-007` / `REQUEST_ID_REUSE`

成功为 `TST-WF-000` / `OK`。

## 与 v0.7 的边界

v0.5 reference engine 的 state/request cache 仅用于 conformance，不具备持久性、共识、finality、Merkle commitment 或多节点同步。只有 v0.7 才能让 ReferenceCity 场景成为真正的持久化端到端链回归。
