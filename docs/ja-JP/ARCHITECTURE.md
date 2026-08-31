# TST Chain アーキテクチャ概要

## 位置づけ

TST Chain は、国土空間計画における信頼・証拠・イベント・来歴を扱う基盤レイヤーです。GIS 描画、リモートセンシング解析、BIM モデリング、行政承認そのものを代替しません。

## 5つの中核ドメインモデル

### SpatialObject
安定した国土空間オブジェクトを表します。

```text
object_id
object_type
jurisdiction
parent_object_id?
external_refs[]
schema_version
```

### SpatialEvent
空間オブジェクトのライフサイクルにおける検証可能な状態変化を表します。

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

Spatial Event は主要な業務原語です。利用者向け画面では金融的な transaction 用語より、承認・変更・確認・監視など計画実務の意味を優先します。

### PlanningRule
機械可読・版管理可能・追跡可能な計画制約を表します。

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

計算処理は GIS、BIM、外部ルールエンジン等が担い、TST Chain はルール版、入力要約、出力要約、証拠、署名を記録します。

### Authority
現実のガバナンス体系に基づく組織、人、役割、管轄、資格情報を表します。チェーン上の設定だけで法的・行政的権限が創設されたものとして扱ってはなりません。

### Provenance
計画成果、ルール、指標、空間状態がどこから生まれ、どのように変更・伝達されたかを表します。

推奨関係：

- `DERIVED_FROM`
- `SUPERSEDES`
- `AMENDS`
- `TRANSMITS_TO`
- `IMPLEMENTS`
- `VERIFIES`
- `MONITORS`
- `AFFECTS`

## 証拠優先のハイブリッド保存

```text
GIS / TIM / BIM / RS / Document / Database
                  │
                  ├─ 原データは外部に保持
                  └─ hash / metadata / reference
                              ↓
                           TST Chain
```

台帳側には、安定 ID、内容 Hash、時刻、版、署名、権限関係、状態変化、計画伝達・来歴関係などの軽量情報を保存します。

## 階層・管轄別スケーリング

```text
Local / County Domain
        ↓ signed checkpoint
City Trust Layer
        ↓ signed checkpoint
Province Trust Layer
        ↓ signed checkpoint
National / Federation Root
```

上位層が下位層の全データを複製する必要はありません。署名済みコミットメントと必要な証拠のみを検証します。

## 中核不変条件

1. 同一 canonical payload は常に同一 content hash を生成すること。
2. 翻訳表示文言は consensus-critical field に入れないこと。
3. 状態変更は必ず識別可能な Spatial Event として表現すること。
4. Event から Actor、Evidence、Schema version を追跡できること。
5. 計画ルールの変更は旧版上書きではなく、新版と来歴関係で表現すること。
6. 外部ファイル更新後も過去の証拠検証が可能であること。
7. 上位チェックポイントは下位詳細データの完全複製を要求しないこと。
8. ルールエンジンの出力を、権限主体による正式決定と混同しないこと。

## Planning AI との関係

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

TST Chain は、AI の結論がどの空間オブジェクト、ルール版、イベント、権限主体に基づくかを追跡可能にする信頼コンテキストを提供します。

## 実装順序

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
