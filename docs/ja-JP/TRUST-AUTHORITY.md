# TST Chain v0.2：信頼主体・権限プロトコル

## 目的

v0.2 は v0.1 の空間オブジェクト、空間イベント、証拠モデルの上に、次の検証可能性を追加します。

- 誰がデータやイベントを作成・署名・確認したか。
- その主体が、その時点・管轄・対象・操作についてシステム上の権限を持っていたか。

## コアモデル

```text
Actor
  ├─ PublicKey
  │    └─ DetachedSignature
  ├─ Credential
  └─ Authority
        ↓
AuthorizationRequest
        ↓ TST-AUTHZ/0.2
AuthorizationDecision
        ↓
AuditRecord
```

## 重要な境界

`Authority` は TST Chain 上の検証可能な権限表明であり、現実の行政権限を新たに作り出すものではありません。実運用では、法令、組織規程、委任その他の有効な根拠との対応付けが必要です。

## 暗号プロファイル

v0.2 は以下を固定します。

- `TST-C14N-JSON/0.1`
- SHA-256
- Ed25519
- パディングなし Base64URL
- 署名ドメイン分離

署名対象は次のバイト列です。

```text
UTF8("TSTCHAIN-SIGNATURE-V0.2") || 0x00 || canonical_payload
```

暗号学的署名が正しくても、鍵が失効・期限切れ・有効期間外なら検証は失敗します。

## ReferenceCity

ReferenceCity リポジトリが完成した後、統合試験データとして接続します。それまでは、小規模な合成 fixture を使用し、プロトコル開発を停止させません。
