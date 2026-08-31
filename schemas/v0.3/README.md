# TST Chain v0.3 — Planning Rule

v0.3 建立机器可读、可版本化、可验证的规划规则协议层。

## Schema

- `planning-rule.schema.json` — PlanningRule 与条件；
- `rule-set.schema.json` — RuleSet / version / 生命周期；
- `rule-evaluation-request.schema.json` — 规则评价输入事实与外部内容 digest；
- `rule-evaluation-result.schema.json` — pass/fail/indeterminate 与稳定 violation code；
- `spatial-evaluation.schema.json` — 外部 GIS 引擎产生的空间关系证据接口。

## 数值

为延续 `TST-C14N-JSON/0.1` 的跨语言确定性，v0.3 协议对象中的规划数值采用 canonical decimal string，例如 `"2.0"`、`"45"`，不使用 binary JSON float。单位必须单独声明。

## 空间计算边界

链核心不重新实现 GIS topology。`SpatialEvaluation` 记录外部 evaluator 对指定 subject/constraint geometry digest 得出的关系，并把 evaluator、时间、输入 digest 和 relation 作为可验证证据。PlanningRule 可以使用该关系，但不能伪装成链本身计算了几何。

## Canonicalization

v0.3 TST 协议对象继续使用 `TST-C14N-JSON/0.1`；本版本 Schema 中数组均按协议定义为无序集合。GeoJSON、ReferenceCity 等外部 JSON 仍使用来源系统定义的 canonicalization，不得套用 TST profile。
