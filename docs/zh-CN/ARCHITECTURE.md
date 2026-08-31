# TST Chain 架构概览

## 1. 定位

TST Chain 是国土空间规划数字体系中的可信关系与可信事件基础设施。它不承担 GIS 渲染、遥感计算、BIM 建模或行政审批本身，而负责对关键对象、规则、事件、权责和证据建立长期可验证关系。

## 2. 五个核心领域模型

### SpatialObject

稳定表示一个国土空间对象。

建议最小字段：

```text
object_id
object_type
jurisdiction
parent_object_id?
external_refs[]
schema_version
```

`external_refs` 用于关联 GIS、TIM、BIM、登记、遥感或其他业务系统中的真实数据。链上不保存大体量原始空间数据。

### SpatialEvent

表示空间对象生命周期中的一次可信状态变化。

```text
event_id
subject_object_id
event_type
previous_state_hash?
new_state_hash
actor_id
authority_id?
basis_refs[]
evidence_refs[]
timestamp
previous_event_hash?
signature
schema_version
```

Spatial Event 是 TST Chain 的核心业务原语，产品层应优先显示“审批、调整、核实、监测”等规划语义，而不是暴露金融区块链式 transaction 术语。

### PlanningRule

表示可机器读取、可版本化、可追溯的规划约束。

```text
rule_id
rule_type
scope
expression
unit?
source_plan_id
basis_refs[]
effective_from
effective_to?
status
schema_version
```

规则执行应由 GIS、BIM、规则引擎或其他计算组件完成；TST Chain 记录规则版本、输入摘要、输出摘要和签署结果。

### Authority

表示现实治理体系中的机构、人员、角色与职权。

```text
actor_id
authority_type
organization_ref
role
jurisdiction
valid_from
valid_to?
credential_refs[]
```

Authority 不能凭链上配置创造现实行政权力。生产部署必须把数字授权绑定到现实制度、证书或其他可验证凭据。

### Provenance

表示一个规划成果、规则、指标或空间状态从何而来、如何演变、如何向下传导。

核心关系建议包括：

- `DERIVED_FROM`
- `SUPERSEDES`
- `AMENDS`
- `TRANSMITS_TO`
- `IMPLEMENTS`
- `VERIFIES`
- `MONITORS`
- `AFFECTS`

## 3. 证据优先的混合存储

```text
GIS / TIM / BIM / RS / Document / Database
                  │
                  ├─ original data
                  │
                  └─ hash / metadata / reference
                              ↓
                           TST Chain
```

链上保存：

- 稳定 ID
- 内容 Hash
- 时间与版本
- 数字签名
- 权责关系
- 状态变化
- 规划传导与谱系关系

链下保存：

- GeoTIFF / SHP / GeoPackage / 3D tiles
- IFC / RVT / DWG / 3DM
- PDF / 图片 / 视频
- 大规模 IoT 与遥感时间序列
- 其他受业务系统管理的原始数据

## 4. 分层分域网络

TST Chain 不要求全国所有节点验证所有地方业务。

推荐研究架构：

```text
Local / County Domain
        │
        └── signed checkpoint
                 ↓
             City Layer
                 │
        └── signed checkpoint
                 ↓
           Province Layer
                 │
        └── signed checkpoint
                 ↓
        National/Federation Root
```

本地保存业务细节，上级保存必要摘要与验证关系，以降低全网复制成本并对应现实治理层级。

## 5. 关键不变量

任何实现都应维持以下不变量：

1. 相同 canonical payload 必须生成相同内容 Hash。
2. 三语显示文本不得进入共识关键字段。
3. 任何状态改变必须由一个可识别 Spatial Event 表达。
4. Event 必须能追溯 Actor、Evidence 和适用的 Schema version。
5. 规划规则变更不得静默覆盖旧规则，必须形成新版本与谱系关系。
6. 外部文件改变后，其旧证据仍必须保持可验证。
7. 上级检查点不得要求复制所有下级明细数据。
8. 智能合约或规则引擎输出不得伪装成行政决定。

## 6. 与规划智能化的关系

TST Chain 不负责替代 AI，而是给 AI 提供可验证上下文。

```text
Spatial Object
      +
Planning Rule
      +
Spatial Event
      +
Authority
      +
Provenance
      ↓
Trusted Spatial Knowledge Graph
      ↓
Planning AI / RAG / Decision Support
```

AI 输出可携带证据包，回答某一规划结论的对象来源、规则版本、审批事件与责任主体。

## 7. 实施顺序

内核开发优先顺序：

1. Canonical serialization
2. Content hash
3. SpatialObject
4. SpatialEvent
5. Evidence
6. Authority
7. PlanningRule
8. Provenance
9. Workflow
10. Distributed ledger
11. Hierarchical checkpoint
12. Interoperability adapters
13. Knowledge graph projection
