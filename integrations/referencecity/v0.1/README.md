# ReferenceCity × TST Chain Integration Profile 0.1

该目录把 `KiYouJyo/ReferenceCity` 的 benchmark contract 与 TST Chain 当前协议能力连接起来。

## 当前结论

TST Chain 当前完成 v0.1 Domain Foundation 和 v0.2 Trust & Authority，但尚未实现 v0.3 Planning Rule、v0.4 Provenance、v0.5 Workflow 与 v0.7 persistent ledger。因此 **S001–S010 目前不能被称为端到端链测试通过**。

`capability-gap.json` 把每个场景拆成当前已有基础、缺失能力和最早目标版本。它是后续路线优先级的机器可读输入，而不是为了让 benchmark 变绿而降低 Ground Truth。

## Canonicalization 边界

`TST-C14N-JSON/0.1` 是 TST 核心协议对象的 canonicalization profile，不是通用 JSON/GeoJSON canonicalizer。v0.1/v0.2 当前数组规范只适用于这些版本 Schema 中按协议视为集合的字段。

ReferenceCity 外部内容使用 RFC 8785 JCS 生成 canonical SHA-256。TST 在登记这些外部资产时必须把该 digest 当作 **source-defined external evidence digest** 保存，不得用 TST-C14N 重新排列 GeoJSON coordinates、scenario actions 等有序数组后再计算所谓“等价 Hash”。

## 测试隔离

ReferenceCity adapter 只消费 `referencecity-benchmark-input-v0.1` artifact / bundle。该 bundle 不包含 `expected/`。链运行结束后才由 ReferenceCity evaluator 将 observed result 与 Ground Truth 比较。
