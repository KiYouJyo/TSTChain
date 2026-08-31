# 国土空間信頼チェーン / Territorial Spatial Trust Chain

**TST Chain** は、国土空間計画のライフサイクル全体を支える信頼デジタル基盤を目指すプロジェクトです。

[简体中文](../../README.md) · **日本語** · [English](../en-US/README.md)

TST Chain は GIS、TIM、CSPON、「一張図」に相当する計画監督基盤、BIM、既存の行政業務システムを置き換えるものではありません。それらの下位に、共通の **信頼・イベント・証拠・来歴レイヤー** を構築します。

## 中核ドメインモデル

- **Spatial Object / 空間オブジェクト** — 行政単位、計画単位、筆・区画、建築物、道路、生態空間、インフラ等。
- **Planning Rule / 計画ルール** — 用途、指標、制御境界、参入条件、計画要件およびその版。
- **Spatial Event / 空間イベント** — 調査、策定、変更、審査、承認、許可、建設、確認、モニタリング、評価、更新等。
- **Authority / 権限主体** — 組織、人、役割、管轄、資格情報、および現実制度に基づく権限。
- **Provenance / 計画来歴** — 計画、ルール、指標、空間状態がどこから生まれ、どのように変更・伝達されたかを検証可能にする関係。

## 設計原則

1. **計画優先・金融非優先。** 取引可能トークン、DeFi、投機市場は主たるロードマップに含めません。
2. **原データは原則オフチェーン、証拠と関係をチェーンに記録。** GIS、BIM、リモートセンシング、文書、センサーデータは既存システムに保持します。
3. **現実の権限を写像し、チェーンが権限を創出しない。**
4. **計画ルールを機械可読・版管理可能にする。** 計算は GIS/BIM/ルールエンジンが担い、TST Chain は使用したルール、入力、結果の整合性を証明します。
5. **管轄と階層に沿って拡張。** ローカル業務はローカルで処理し、上位層は全明細を複製せず署名済みチェックポイントを検証します。
6. **TIM/CSPON および既存計画基盤との互換性を優先。**
7. **プロトコルを安定させ、実装は交換可能にする。**

## 全体アーキテクチャ

```text
Spatial Identity
      ↓
Spatial Object Model
      ↓
Spatial Event Ledger
      ↓
Planning Rule Model
      ↓
Authority & Credential
      ↓
Plan Provenance / Transmission Graph
      ↓
Workflow & Verification
      ↓
GIS · TIM · CSPON · BIM · Remote Sensing · Planning AI
```

詳細は [ロードマップ](../../ROADMAP.md) と [アーキテクチャ概要](ARCHITECTURE.md) を参照してください。

## 三言語対応

正式に次の三言語をサポートします。

- `zh-CN` — 簡体字中国語
- `ja-JP` — 日本語
- `en-US` — 英語

プロトコルフィールド、Schema ID、列挙値、永続 key、canonical payload、コード上の識別子は安定した英語 machine key を使用します。表示文言は `locales/` で分離し、翻訳によって署名対象や Hash 入力が変化しないようにします。

## プロジェクト名

**English:** Territorial Spatial Trust Chain  
**中文:** 国土空间可信链  
**日本語:** 国土空間信頼チェーン  
**略称:** TST Chain
