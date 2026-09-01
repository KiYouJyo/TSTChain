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

## v0.5 — Workflow — 完成协议候选
WorkflowDefinition / Instance / TransitionRequest / TransitionResult、权限/文档/签名/规则前置条件、乐观并发、幂等和原子状态迁移已完成。

## v0.6 — Interoperability — GIS/GeoJSON slice 完成协议候选
建立“数据不上链，证据与关系上链”的外部空间输入层。ReferenceCity S007 已由真实生成 geometry 经 Shapely 计算产生空间证据并驱动 PlanningRule / Workflow。

已完成：ExternalSpatialAsset、GeoJSON/generated JSON geometry adapter、SpatialEvaluation reference evaluator、RFC8785-JCS 外部 canonicalization 边界。

后续互操作子项继续滚动进入 v0.8–v1.0：GeoPackage、TIM/CSPON、BIM/IFC、document/raster descriptor、REST/OpenAPI gateway。

## ReferenceCity v0.1 验收基线 — v0.7 达成
固定 ReferenceCity commit `f810758d151a36747dbc7ccf11998f12d40bef4e`。实现端只接收由 ReferenceCity `build_benchmark_input.py` 生成、明确 `ground_truth_included=false` 的隔离输入；TSTChain 生成 `observed/S001...S010` 后，再由 ReferenceCity 自己的 `compare_observed.py` 独立读取 Ground Truth 判分。

**当前结果：10 full / 0 partial / 0 unsupported；Python 3.11 / 3.12 / 3.13 均为 10/10，所有场景 mismatches=[]。**

这里的 `full` 仅指该固定合成基准的端到端一致性通过；`production_ready=false`，不代表政府生产准入、法定效力、安全等级认证或真实涉密数据部署能力。

## v0.7 — Distributed Ledger Prototype — 核心完成
- [x] append-only ledger + per-entry hash chain
- [x] workflow commit / rejection atomic audit persistence
- [x] evidence / provenance record
- [x] auditable `state_seed` for benchmark/bootstrap state
- [x] disposable state snapshot + full ledger replay recovery
- [x] Merkle checkpoint
- [x] Authority validator set
- [x] Ed25519 quorum-signed finality（reference profile 2/3）
- [x] ReferenceCity S001–S010 isolated-input ledger adapter
- [x] independent ReferenceCity evaluator 10/10 on Python 3.11–3.13
- [x] native token / gas / mining dependency: NONE

尚未把 v0.7 称为生产级分布式网络：多节点网络传输、成员变更、BFT fault model、远程状态同步和运维安全仍属于后续版本。

## v0.8 — Hierarchical & Jurisdictional Scaling — 当前阶段
目标：把单一 ReferenceCity 账本扩展成符合国土空间治理层级与数据驻留要求的分层分域可信网络。

- [ ] Domain / Jurisdiction descriptor
- [ ] County/Domain → City → Province → National/Federation Root hierarchy
- [ ] ledger partition / namespace isolation
- [ ] local authoritative state + upper-level commitment
- [ ] cross-domain proof envelope
- [ ] hierarchical checkpoint aggregation
- [ ] selective replication policy
- [ ] data-residency / disclosure hooks
- [ ] validator-set inheritance / delegation profile
- [ ] cross-jurisdiction verification reference implementation
- [ ] ReferenceCity multi-domain synthetic fixture and conformance

## v0.9 — Knowledge Graph & Planning AI Foundation
Spatial knowledge graph、Object–Rule–Event–Authority graph、provenance query、AI/RAG evidence package、可验证引用与规划问答。

## v1.0
稳定核心 Schema、五大模型、签名/Hash/版本、可插拔账本、GIS/TIM/CSPON/BIM 适配、分层分域原型、完整测试与安全模型。
