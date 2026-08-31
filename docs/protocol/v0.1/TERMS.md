# Stable Terms — v0.1

The following machine terms are reserved by TST Chain v0.1.

| Machine term | 中文 | 日本語 | English |
|---|---|---|---|
| `SpatialObject` | 空间对象 | 空間オブジェクト | Spatial Object |
| `SpatialEvent` | 空间事件 | 空間イベント | Spatial Event |
| `Evidence` | 证据 | エビデンス | Evidence |
| `object_id` | 空间对象标识 | 空間オブジェクトID | Object ID |
| `event_id` | 空间事件标识 | 空間イベントID | Event ID |
| `evidence_id` | 证据标识 | エビデンスID | Evidence ID |
| `jurisdiction` | 管辖域 | 管轄域 | Jurisdiction |
| `external_refs` | 外部数据引用 | 外部データ参照 | External references |
| `content_digest` | 内容摘要 | コンテンツダイジェスト | Content digest |
| `previous_state_hash` | 前状态摘要 | 前状態ハッシュ | Previous-state hash |
| `new_state_hash` | 新状态摘要 | 新状態ハッシュ | New-state hash |
| `previous_event_hash` | 前事件摘要 | 前イベントハッシュ | Previous-event hash |
| `basis_refs` | 依据引用 | 根拠参照 | Basis references |
| `evidence_refs` | 证据引用 | エビデンス参照 | Evidence references |
| `schema_version` | 模式版本 | スキーマバージョン | Schema version |

## Naming rules

- Protocol fields use `snake_case`.
- Protocol type names use `PascalCase`.
- Event and object type values use lowercase `snake_case`.
- TST-native identifiers use lowercase `tst:` prefixes.
- Display translations never replace machine keys in stored protocol data.

New translations may be added without changing hashes or schema compatibility.
