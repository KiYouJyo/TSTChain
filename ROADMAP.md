# TST Chain Roadmap

> Territorial Spatial Trust Chain / 国土空间可信链

原则：**先协议与领域模型，后分布式实现；先可信规划基础设施，后智能应用**。版本号代表技术成熟度，不代表行政系统生产准入或法定效力。

## v0.1 — Domain Foundation — 完成
SpatialObject、SpatialEvent、Evidence、`TST-C14N-JSON/0.1`、三语资源、Schema/versioning、测试向量与多 Python conformance 已完成。TST canonicalization 只用于 TST 协议实例，不用于外部 GeoJSON。

## v0.2 — Trust & Authority — 完成
Actor / Authority、角色/权限/管辖、Ed25519 signature、Credential、`TST-AUTHZ/0.2`、密钥撤销/轮换、AuthorizationDecision、AuditRecord 与稳定错误码已完成。

## ReferenceCity 验收基线
ReferenceCity protocol `0.1` / core `0.1.0` 是跨阶段 benchmark。v0.2 基线为 **0 full / 3 partial / 7 unsupported**。外部 ReferenceCity JSON 使用 `RFC8785-JCS` digest；TST Evidence 记录其 source-defined digest，不重新用 TST profile 排列有序数组。

## v0.3 — Planning Rule — 协议候选实现完成

目标：建立机器可读、可版本化、可验证的规划规则模型，并解除 S006/S007 的**规则表达层**阻塞。

- [x] `PlanningRule` Schema；
- [x] RuleSet / version / active / superseded / revoked；
- [x] jurisdiction / object / target / spatial-constraint scope；
- [x] enum、canonical decimal、外部空间关系条件；
- [x] `RuleEvaluationRequest` / `RuleEvaluationResult`；
- [x] `SpatialEvaluation` 外部 GIS 证据接口；
- [x] external content canonicalization profile 元数据；
- [x] 明确链内 rule proof 与外部 GIS topology 的职责边界；
- [x] ReferenceCity S006 rule-conflict mapping；
- [x] ReferenceCity S007 external spatial relation mapping；
- [x] Python 3.11–3.13 conformance + v0.1/v0.2 regression。

**注意**：S006/S007 仍不是完整 benchmark PASS；其状态变更/拒绝需要 v0.5 Workflow，S007 的真实几何关系生成需要 v0.6 GIS adapter。

## v0.4 — Provenance — 下一阶段

目标：解除 S001/S002/S009 的计划版本与历史证明阻塞。

- [ ] `PlanArtifact` / `PlanVersion`
- [ ] Amendment / Supersede / Derive 关系
- [ ] 上下级规划传导边
- [ ] 指标分解与约束来源追溯
- [ ] Provenance graph integrity validation
- [ ] ReferenceCity plan/version mapping

## v0.5 — Workflow
目标：解除 S001/S002/S003/S006/S008/S010 的状态机与原子前置条件阻塞：编制、提交、审查、审批、生效、调整；Authority policy；required document/signature；expected_version；idempotency；稳定错误码。

## v0.6 — Interoperability
目标：建立 GIS / GeoJSON / GeoPackage、TIM/CSPON、BIM/IFC、遥感、文档 evidence adapter；让 S007 获得真实外部空间评价输入。

## v0.7 — Distributed Ledger Prototype
目标：Append-only ledger、Merkle commitment、Authority validator set、finality、snapshot/checkpoint/state sync、atomic transition + audit persistence，并真正运行 ReferenceCity S001–S010 evaluator。

## v0.8 — Hierarchical & Jurisdictional Scaling
County/Domain → City → Province → National/Federation Root：partition、cross-domain proof、hierarchical checkpoint、selective replication、data-residency hooks。

## v0.9 — Knowledge Graph & Planning AI Foundation
Spatial knowledge graph、Object–Rule–Event–Authority graph、provenance query、AI/RAG evidence package、可验证引用与规划问答。

## v1.0 — Trusted Territorial Spatial Infrastructure
稳定核心 Schema、五大模型、签名/Hash/版本、可插拔账本、GIS/TIM/CSPON/BIM 适配、分层分域原型、完整测试与安全模型。

## 非主线路线
NFT / unique tokenized representation、通用资产凭证、公共参与式投票、P2P 资源/能源结算可实验，但不得改变国土空间可信基础设施主线。
