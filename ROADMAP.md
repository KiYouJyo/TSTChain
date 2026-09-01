# TST Chain Roadmap

> Territorial Spatial Trust Chain / 国土空间可信链

原则：**先协议与领域模型，后分布式实现；先可信规划基础设施，后智能应用**。版本号代表技术成熟度，不代表行政系统生产准入或法定效力。

## v0.1 — Domain Foundation — 完成
SpatialObject、SpatialEvent、Evidence、`TST-C14N-JSON/0.1` 与 conformance 已完成；TST canonicalization 不用于外部 GeoJSON。

## v0.2 — Trust & Authority — 完成
Actor / Authority、权限、Ed25519、Credential、AuthorizationDecision、AuditRecord 已完成。

## v0.3 — Planning Rule — 完成协议候选
PlanningRule / RuleSet / RuleEvaluation / SpatialEvaluation 已完成，S006/S007 的规则表达层已建立。

## v0.4 — Provenance — 完成协议候选
PlanArtifact / PlanVersion / ProvenanceEdge / HistoricalVersionVerification 已完成，S001/S002/S009 的版本和历史模型已建立。

## ReferenceCity 验收基线
截至 v0.6 GIS slice，S001–S010 仍为 **0 full / 10 partial / 0 unsupported**。所有场景的主协议判定均已具备，S007 已由真实 ReferenceCity geometry 驱动外部 GIS evaluator；`full` 仍要求 v0.7 的持久权威状态，因此现在不人为宣称端到端链 PASS。

## v0.5 — Workflow — 协议候选实现完成
- [x] WorkflowDefinition / states / transitions；
- [x] WorkflowInstance / current state / current version；
- [x] TransitionRequest / `expected_version` / request ID；
- [x] v0.2 authorization/permission gate；
- [x] required document / signature preconditions；
- [x] v0.3 RuleEvaluationResult gate；
- [x] optimistic concurrency / `VERSION_CONFLICT`；
- [x] idempotent replay / `REQUEST_ID_REUSE`；
- [x] all-preconditions-before-mutation 原子语义；
- [x] ReferenceCity S001/S002/S003/S004/S006/S008/S010 protocol mappings；
- [x] Python 3.11–3.13 conformance + v0.1–v0.4 regression。

## v0.6 — Interoperability — GIS/GeoJSON slice 完成协议候选
目标：建立通用的“数据不上链，证据与关系上链”输入层。首个 slice 已将 S007 从预注入空间关系证据升级为真实 ReferenceCity geometry 计算。

- [x] ExternalSpatialAsset / canonicalization profile
- [x] GeoJSON / generated JSON geometry adapter
- [ ] GeoPackage adapter contract
- [x] `SpatialEvaluation` reference evaluator
- [x] ReferenceCity S007 geometry → Shapely → PlanningRule → Workflow integration test
- [x] RFC8785-JCS external ordered-JSON boundary regression
- [ ] TIM / CSPON mapping profile
- [ ] BIM / IFC reference profile
- [ ] document / raster evidence descriptor
- [ ] REST / OpenAPI gateway

**原则**：Shapely 只是参考适配器，不是协议依赖。生产系统可替换为 PostGIS、QGIS、ArcGIS 或其他 GIS 引擎，只要产生同一 v0.6 证据契约。

## v0.7 — Distributed Ledger Prototype
Append-only ledger、Merkle commitment、Authority validator set、finality、snapshot/checkpoint/state sync、atomic transition + audit persistence，并真正运行 ReferenceCity S001–S010 evaluator。

## v0.8 — Hierarchical & Jurisdictional Scaling
County/Domain → City → Province → National/Federation Root：partition、cross-domain proof、hierarchical checkpoint、selective replication、data-residency hooks。

## v0.9 — Knowledge Graph & Planning AI Foundation
Spatial knowledge graph、Object–Rule–Event–Authority graph、provenance query、AI/RAG evidence package、可验证引用与规划问答。

## v1.0
稳定核心 Schema、五大模型、签名/Hash/版本、可插拔账本、GIS/TIM/CSPON/BIM 适配、分层分域原型、完整测试与安全模型。
