# TST Chain Roadmap

> Territorial Spatial Trust Chain / 国土空间可信链

本路线图以“**先协议与领域模型，后分布式实现；先可信规划基础设施，后智能应用**”为原则。版本号代表技术成熟度，不代表行政系统生产准入或法定效力。

## v0.1 — Domain Foundation — 完成

已完成 SpatialObject、SpatialEvent、Evidence、`TST-C14N-JSON/0.1`、三语资源、Schema/versioning、测试向量与多 Python conformance。`TST-C14N-JSON/0.1` 仅适用于 TST 核心协议实例，不得作为通用 GeoJSON canonicalizer。

## v0.2 — Trust & Authority — 完成

已完成 Actor / Authority、机构与人员、角色/权限/管辖范围、Ed25519 detached signature、Credential、`TST-AUTHZ/0.2`、密钥撤销/轮换、AuthorizationDecision、AuditRecord、稳定错误码和回归 CI。

## ReferenceCity 驱动的验收基线

ReferenceCity protocol `0.1` / core `0.1.0` 现作为后续版本的跨阶段 benchmark。当前 v0.2 对 S001–S010 的能力覆盖为 **0 full / 3 partial / 7 unsupported**；这不是失败掩盖项，而是路线图优先级输入。详见 `integrations/referencecity/v0.1/capability-gap.json`。

### Canonicalization 边界

- TST 核心对象：`TST-C14N-JSON/0.1`；
- ReferenceCity 外部 JSON/GIS 资产：保留其 `RFC8785-JCS` canonical SHA-256；
- TST Evidence 记录外部 digest，不用 TST profile 重排 GeoJSON coordinates、scenario actions 等有序数组。

## v0.3 — Planning Rule — 下一阶段

目标：优先解除 ReferenceCity **S006 / S007** 的规则模型阻塞，同时为其他规划业务建立可版本化规则基础。

- [ ] `PlanningRule` 基础 Schema
- [ ] RuleSet / version / effective / superseded 状态
- [ ] target object type 与 jurisdiction/scope
- [ ] 数值指标、枚举条件和外部空间约束 reference
- [ ] `RuleEvaluationRequest` / `RuleEvaluationResult`
- [ ] `external_content_canonicalization` / evidence profile 元数据
- [ ] 明确链内规则证明与外部 GIS rule engine 的职责边界
- [ ] ReferenceCity S006 rule-conflict mapping fixture
- [ ] 为 S007 预留 external spatial evaluator result，不在链核心重写 GIS 几何引擎
- [ ] v0.3 conformance + v0.1/v0.2 regression

## v0.4 — Provenance

目标：解除 S001/S002/S009 的计划版本与历史证明阻塞。

- [ ] `PlanArtifact` / `PlanVersion`
- [ ] Amendment / Supersede / Derive 关系
- [ ] 上下级规划传导边
- [ ] 指标分解与约束来源追溯
- [ ] Provenance graph integrity validation

## v0.5 — Workflow

目标：解除 S001/S002/S003/S006/S008/S010 的状态机与原子前置条件阻塞。

- [ ] 编制、提交、审查、审批、生效、调整
- [ ] 可配置状态机与 Authority policy
- [ ] required document/signature preconditions
- [ ] optimistic concurrency / expected_version
- [ ] idempotency / request-id reuse
- [ ] 稳定 workflow error mapping

## v0.6 — Interoperability

目标：解除 S007 的 GIS 外部空间评价阻塞，并建立“数据不上链，证据与关系上链”的标准适配层。

- [ ] GIS / GeoJSON / GeoPackage adapter
- [ ] TIM / CSPON mapping
- [ ] BIM / IFC reference adapter
- [ ] Remote sensing / document evidence adapter
- [ ] REST / OpenAPI gateway

## v0.7 — Distributed Ledger Prototype

目标：把 stateless conformance 升级为持久化多节点可信账本，使 ReferenceCity S001–S010 真正成为端到端链回归。

- [ ] Append-only ledger
- [ ] Merkle commitment
- [ ] Authority-based validator set
- [ ] Finality / node identity
- [ ] Snapshot / checkpoint / state synchronization
- [ ] atomic state transition + audit persistence
- [ ] ReferenceCity adapter observed-result output
- [ ] ReferenceCity S001–S010 evaluator run

## v0.8 — Hierarchical & Jurisdictional Scaling

County / Domain Ledger → City Trust Layer → Province Trust Layer → National/Federation Root：分区、跨域 proof、层级 checkpoint、selective replication、data-residency hooks。

## v0.9 — Knowledge Graph & Planning AI Foundation

Spatial knowledge graph、Object–Rule–Event–Authority graph、provenance query、AI/RAG evidence package、可验证引用与规划问答。

## v1.0 — Trusted Territorial Spatial Infrastructure

稳定核心 Schema、Spatial Object / Event / Rule / Authority / Provenance、签名/Hash/版本、可插拔存储/账本、GIS/TIM/CSPON/BIM 适配、分层分域原型、完整测试与安全模型。

## 非主线路线

NFT / unique tokenized representation、通用资产凭证、公共参与式投票实验、P2P 资源/能源结算可以作为实验扩展，但不得改变国土空间可信基础设施主线。
