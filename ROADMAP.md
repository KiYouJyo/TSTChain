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
截至 v0.7 persistent-ledger benchmark，ReferenceCity S001–S010 已达到 **10 full / 0 partial / 0 unsupported**。十个场景均由同一持久权威账本执行并逐项匹配 pinned ReferenceCity expected output；账本随后通过重启 replay 恢复，并由 Authority validator quorum 对实际 ledger prefix 的 Merkle root 完成 finality。该基线已在 Python 3.11、3.12、3.13 三版本 CI 中通过。

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

## v0.7 — Distributed Ledger Prototype — 核心验收完成，节点化收口进行中
目标：把 v0.1–v0.6 的可信对象、规则、流程、证据与来源关系落实为可恢复、可终局确认、可同步的持久权威状态。

- [x] append-only SHA-256 predecessor hash chain；
- [x] accepted / rejected workflow outcome 原子持久化；
- [x] Evidence / Provenance 持久记录与后续摘要核验；
- [x] snapshot 仅作可丢弃缓存，权威状态由 ledger replay 恢复；
- [x] deterministic Merkle checkpoint；
- [x] Authority validator set + Ed25519 quorum finality；
- [x] checkpoint 对实际 ledger prefix 的 Merkle 反证；
- [x] `StateSyncBundle`：finalized ledger prefix + checkpoint + validator set；
- [x] state sync bundle hash、签名、Merkle、hash-chain 全链验证；
- [x] state sync fork rejection / rollback rejection；
- [x] ReferenceCity S001–S010 persistent benchmark：**10 full / 0 partial / 0 unsupported**；
- [x] Python 3.11–3.13 v0.1–v0.7 regression + full benchmark；
- [ ] NodeIdentity / 节点身份与 peer authentication；
- [ ] checkpoint chain / validator-set evolution；
- [ ] crash/fault recovery protocol 与中断写入恢复；
- [ ] incremental state sync / multi-node replication。

## v0.8 — Hierarchical & Jurisdictional Scaling
County/Domain → City → Province → National/Federation Root：partition、cross-domain proof、hierarchical checkpoint、selective replication、data-residency hooks。

## v0.9 — Knowledge Graph & Planning AI Foundation
Spatial knowledge graph、Object–Rule–Event–Authority graph、provenance query、AI/RAG evidence package、可验证引用与规划问答。

## v1.0
稳定核心 Schema、五大模型、签名/Hash/版本、可插拔账本、GIS/TIM/CSPON/BIM 适配、分层分域原型、完整测试与安全模型。
