# TST Chain Schema v0.1

本目录定义 TST Chain v0.1 的最小领域 Schema。当前阶段目标是先稳定 **SpatialObject / SpatialEvent / Evidence** 三类基础对象，再在后续版本扩展 Authority、PlanningRule、Provenance 与 Workflow。

## 设计原则

- JSON Schema 使用 Draft 2020-12。
- Schema 字段只使用稳定英文 machine key。
- 不允许用户可见翻译字符串影响 canonical payload。
- ID 格式当前保持实现中立，不提前绑定 UUID、DID、URI 或某一种链地址。
- 时间使用 RFC 3339 `date-time`。
- 大体量空间数据不直接嵌入 Schema；通过 `external_refs` / `evidence_refs` 关联。
- Hash 字段当前使用算法名 + digest 的组合，避免过早绑定单一算法。
- v0.1 Schema 仍属于实验性协议，字段语义可在 v1.0 前演进，但任何不兼容变更都应有显式记录。

## 文件

- `spatial-object.schema.json` — 国土空间对象最小身份与外部引用
- `spatial-event.schema.json` — 空间对象生命周期事件
- `evidence.schema.json` — 外部证据的内容摘要与来源引用

## 后续

计划增加：

```text
authority.schema.json
planning-rule.schema.json
provenance-edge.schema.json
workflow-transition.schema.json
checkpoint.schema.json
```

同时建立 canonical serialization 规范和跨语言测试向量，确保不同实现对同一事件得到一致的签名载荷与内容 Hash。
