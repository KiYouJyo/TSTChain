# ReferenceCity 基准集成

ReferenceCity 是 TST Chain 的合成国土空间规划基准环境。它提供确定性城市、规划控制、治理主体、生命周期、异常场景与机器可读 Ground Truth。

当前集成基线：ReferenceCity protocol `0.1`、core dataset `0.1.0`、CRS `RC-SYNTHETIC-1`。

## 为什么现在不是 10/10

TST Chain v0.2 已具备身份、Evidence、Authority、Credential、Ed25519 签名、授权判定和 AuditRecord，但 ReferenceCity 的十个场景同时测试 PlanningRule、PlanVersion/Provenance、Workflow、GIS 空间冲突以及持久化账本。因此当前 benchmark 的意义首先是**把路线图缺口变成可执行验收条件**。

不得为通过测试而在 TST Chain 内硬编码 `RC:*` ID、S001–S010 名称或 expected 结果。

详见 `integrations/referencecity/v0.1/`。
