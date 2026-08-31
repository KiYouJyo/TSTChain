# TST Chain Roadmap

> Territorial Spatial Trust Chain / 国土空间可信链

本路线图以“**先协议与领域模型，后分布式实现；先可信规划基础设施，后智能应用**”为原则。版本号代表技术成熟度，不代表行政系统生产准入或法定效力。

## v0.1 — Domain Foundation

目标：建立最小、稳定、可测试的国土空间可信领域模型。

- [x] `SpatialObject`：空间对象 ID、类型、层级/管辖域、外部数据与几何引用
- [x] `SpatialEvent`：事件 ID、主体、对象、前后状态、时间、依据、证据引用
- [x] `Evidence`：内容 Hash、时间戳、来源与外部 URI/对象存储引用
- [x] Canonical serialization：`TST-C14N-JSON/0.1` 确定性序列化与 SHA-256 内容寻址
- [x] 三语资源：`zh-CN` / `ja-JP` / `en-US`
- [x] 核心术语表与稳定机器 key
- [x] Schema versioning 与兼容策略
- [x] Schema 校验、测试向量、等价输入测试与示例数据

**验收标准**：同一 Spatial Event 在不同实现中可生成一致 canonical bytes 与一致 content hash；三语显示不改变协议字段。

**v0.1 状态**：协议候选实现完成。合并前由 `v0.1 Protocol Conformance` CI 在多 Python 版本环境复核 Schema、canonical bytes、SHA-256 测试向量和三语 key 一致性。

## v0.2 — Trust & Authority

目标：让“谁有权做什么、谁签署了什么”成为可验证对象。

- [ ] `Authority` / `Actor` 数据模型
- [ ] 机构、人员、角色与职权范围
- [ ] Digital Signature abstraction
- [ ] Credential / certificate abstraction
- [ ] Event authorization policy
- [ ] 签名验证、撤销与密钥轮换模型
- [ ] 审计日志与错误码规范

**原则**：链不创造现实行政权力，只映射和验证现实制度中的授权关系。

## v0.3 — Planning Rule

目标：建立机器可读、可版本化、可追溯的规划规则模型。

- [ ] `PlanningRule` 基础 Schema
- [ ] 适用空间范围与对象范围
- [ ] 数值指标、枚举条件、空间约束、引用依据
- [ ] RuleSet 与版本关系
- [ ] 生效、废止、替代与例外状态
- [ ] Rule evaluation result schema
- [ ] GIS/BIM 外部规则引擎接口

**原则**：链负责证明规则版本、输入和结果；不替代依法应由行政主体作出的裁量。

## v0.4 — Provenance

目标：形成规划版本链、调整链和上下级规划传导图。

- [ ] `PlanArtifact` / `PlanVersion`
- [ ] Amendment / Supersede / Derive 关系
- [ ] 国家—省—市—县—详细规划的传导边
- [ ] 指标分解与约束来源追溯
- [ ] 反向影响查询
- [ ] Provenance graph integrity validation

## v0.5 — Workflow

目标：表达国土空间规划全生命周期业务状态，而不是模拟金融交易。

- [ ] 编制
- [ ] 审查
- [ ] 审批
- [ ] 用途管制 / 许可
- [ ] 规划核实
- [ ] 监测
- [ ] 评估
- [ ] 调整 / 更新
- [ ] 可配置状态机与权限策略

## v0.6 — Interoperability

目标：建立“数据不上链，证据与关系上链”的标准适配层。

优先接口：

- [ ] GIS / GeoJSON / GeoPackage adapter
- [ ] TIM-compatible object mapping
- [ ] CSPON event/data adapter
- [ ] BIM / IFC reference adapter
- [ ] Remote sensing evidence adapter
- [ ] Document / PDF / archive evidence adapter
- [ ] REST / OpenAPI gateway

## v0.7 — Distributed Ledger Prototype

目标：从单机可验证日志升级为多节点可信账本原型。

- [ ] Append-only ledger
- [ ] Merkle commitment
- [ ] Authority-based validator set
- [ ] Finality model
- [ ] Node identity
- [ ] Snapshot / checkpoint
- [ ] State synchronization
- [ ] Fault and recovery tests

不引入可交易原生代币，不以挖矿或 Gas 作为业务前提。

## v0.8 — Hierarchical & Jurisdictional Scaling

目标：验证国土空间治理层级下的弹性扩展模型。

```text
County / Domain Ledger
        ↓ checkpoint
City Trust Layer
        ↓ checkpoint
Province Trust Layer
        ↓ checkpoint
National Root / Federation Root
```

- [ ] Jurisdiction partitioning
- [ ] Cross-domain event proof
- [ ] Hierarchical checkpoint
- [ ] Selective replication
- [ ] Data residency policy hooks
- [ ] 跨层级传导完整性验证

## v0.9 — Knowledge Graph & Planning AI Foundation

目标：把可信账本转化为可查询的国土空间知识基础。

- [ ] Spatial knowledge graph projection
- [ ] Object–Rule–Event–Authority graph
- [ ] Provenance-aware query
- [ ] AI/RAG evidence package
- [ ] 可验证引用与来源链
- [ ] 规划问答与规则解释原型

## v1.0 — Trusted Territorial Spatial Infrastructure

目标：形成稳定的国土空间可信基础协议与参考实现。

v1.0 至少应具备：

- 稳定的核心 Schema 与兼容策略；
- Spatial Object / Event / Rule / Authority / Provenance 五大核心模型；
- 多语言资源与术语规范；
- 可验证签名、Hash、时间与版本关系；
- 可插拔存储与分布式账本实现；
- GIS/TIM/CSPON/BIM 等适配接口；
- 分层分域检查点原型；
- 完整测试向量、示例数据、开发者文档与安全模型。

## 非主线路线

以下能力可以作为实验性扩展，但不得反客为主：

- NFT / unique tokenized object representation
- 通用资产凭证
- 公共参与式投票实验
- P2P 资源或能源结算实验

它们不得改变 TST Chain “国土空间规划可信数字基础设施”的核心定位。
