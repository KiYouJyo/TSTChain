# TST Chain v0.4 — Provenance

v0.4 将“规划是什么”和“规划为什么变成现在这样”分开表达：`PlanArtifact` 是长期身份，`PlanVersion` 是可验证状态，`ProvenanceEdge` 表达调整、替代、派生、传导与实施关系。

核心原则：对象 ID 不随版本变化；版本号使用 canonical integer string；外部规划数据的 `content_digest` 保留来源 canonicalization profile（ReferenceCity 为 `RFC8785-JCS`）；图中边的数组顺序不参与语义，关系由 `from_ref` / `to_ref` 决定。

`HistoricalVersionVerification` 允许验证旧版本仍存在、内容 Hash 是否匹配、版本链是否完整，而不要求旧版本重新成为当前有效状态。
