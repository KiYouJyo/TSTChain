# TST Chain Roadmap

> Territorial Spatial Trust Chain / 国土空间可信链

原则：**先协议与领域模型，后分布式实现；先可信规划基础设施，后智能应用**。版本号代表技术成熟度，不代表行政系统生产准入或法定效力。

## v0.1 — Domain Foundation — 完成
SpatialObject、SpatialEvent、Evidence、`TST-C14N-JSON/0.1`、三语资源、Schema/versioning、测试向量与 conformance 已完成。TST canonicalization 只用于 TST 协议实例，不用于外部 GeoJSON。

## v0.2 — Trust & Authority — 完成
Actor / Authority、权限/管辖、Ed25519、Credential、`TST-AUTHZ/0.2`、AuthorizationDecision、AuditRecord 已完成。

## v0.3 — Planning Rule — 完成协议候选
PlanningRule、RuleSet、enum/canonical-decimal/spatial conditions、RuleEvaluation、SpatialEvaluation 外部 GIS 关系证据接口已建立。ReferenceCity S006/S007 的规则层映射已进入 conformance，但完整状态拒绝仍依赖 v0.5，真实 GIS 关系生成仍依赖 v0.6。

## ReferenceCity 验收基线
截至 v0.4，ReferenceCity S001–S010 能力覆盖为 **0 full / 8 partial / 2 unsupported**。`full` 特指能够在持久权威状态上端到端执行，因此在 v0.7 ledger 前不会人为宣称 full PASS。

## v0.4 — Provenance — 协议候选实现完成

- [x] `PlanArtifact` / `PlanVersion`；
- [x] 对象长期 ID 与版本状态分离；
- [x] Amendment / Supersede / Derive / Transmit 等 `ProvenanceEdge`；
- [x] 外部内容 digest + canonicalization profile；
- [x] 版本递增、previous-version 与 cycle integrity 检查；
- [x] `HistoricalVersionVerification`；
- [x] ReferenceCity S001/S002 plan/version mapping；
- [x] ReferenceCity S009 历史 Hash/图完整性映射；
- [x] Python 3.11–3.13 conformance + v0.1–v0.3 regression。

## v0.5 — Workflow — 下一阶段
目标：让 S003/S010 获得主判定能力，并把 S001/S002/S006/S008 的已有协议对象真正串成状态事务。

- [ ] WorkflowDefinition / states / transitions
- [ ] WorkflowInstance / current state / current version
- [ ] TransitionRequest / expected_version / request_id
- [ ] Authority permission precondition
- [ ] required document / signature preconditions
- [ ] RuleEvaluationResult gate
- [ ] optimistic concurrency / `VERSION_CONFLICT`
- [ ] idempotency / request-id reuse
- [ ] atomic state mutation + AuditRecord output contract
- [ ] ReferenceCity S001/S002/S003/S004/S006/S008/S010 mapping

## v0.6 — Interoperability
GIS / GeoJSON / GeoPackage、TIM/CSPON、BIM/IFC、遥感、文档 adapter；S007 获得真实外部空间评价输入。

## v0.7 — Distributed Ledger Prototype
Append-only ledger、Merkle commitment、Authority validator set、finality、snapshot/checkpoint/state sync、atomic transition + audit persistence，并真正运行 ReferenceCity S001–S010 evaluator。

## v0.8 — Hierarchical & Jurisdictional Scaling
County/Domain → City → Province → National/Federation Root：partition、cross-domain proof、hierarchical checkpoint、selective replication、data-residency hooks。

## v0.9 — Knowledge Graph & Planning AI Foundation
Spatial knowledge graph、Object–Rule–Event–Authority graph、provenance query、AI/RAG evidence package、可验证引用与规划问答。

## v1.0
稳定核心 Schema、五大模型、签名/Hash/版本、可插拔账本、GIS/TIM/CSPON/BIM 适配、分层分域原型、完整测试与安全模型。
