# ReferenceCity ベンチマーク統合

ReferenceCity は TST Chain の合成国土空間計画ベンチマーク環境です。決定論的な都市、計画制御、ガバナンス主体、ライフサイクル、異常シナリオ、機械可読 Ground Truth を提供します。

現在の統合基準は ReferenceCity protocol `0.1`、core dataset `0.1.0`、合成 CRS `RC-SYNTHETIC-1` です。

TST Chain v0.2 は ID、Evidence、Authority、Credential、Ed25519 署名、権限判定、AuditRecord を備えています。一方 S001–S010 は PlanningRule、計画バージョン provenance、Workflow、GIS 空間競合評価、永続 ledger も必要とします。そのため現段階の benchmark は、無理に全て PASS にするものではなく、Roadmap の不足を実行可能な受入条件へ変換するために利用します。

`RC:*` ID、S001–S010 名、expected 結果を TST Chain 実装にハードコードしてはいけません。詳細は `integrations/referencecity/v0.1/` を参照してください。
