# TST Chain v0.2：可信身份与权责协议

## 目标

v0.2 在 v0.1 的 `SpatialObject / SpatialEvent / Evidence` 基础上解决两个问题：

- **是谁产生、签署或确认了数据？**
- **该主体在当时、该区域、该对象和该操作上是否具备被系统认可的授权？**

## 核心对象

```text
Actor（主体）
  ├─ PublicKey（公钥）
  │    └─ DetachedSignature（分离式签名）
  ├─ Credential（凭证）
  └─ Authority（权责声明）
        ↓
AuthorizationRequest（授权请求）
        ↓ TST-AUTHZ/0.2
AuthorizationDecision（授权判定）
        ↓
AuditRecord（审计记录）
```

## 重要边界

`Authority` 只是在 TST Chain 中可验证的数字权责声明，**不会凭空产生现实行政权力**。生产系统必须把它映射到真实有效的机构设置、法定职权、委托关系或其他合法依据。

## 密码学配置

v0.2 统一采用：

- `TST-C14N-JSON/0.1`
- SHA-256
- Ed25519
- 无填充 Base64URL
- 强制签名域分离

签名输入为：

```text
UTF8("TSTCHAIN-SIGNATURE-V0.2") || 0x00 || canonical_payload
```

即使数学签名有效，如果密钥已经撤销、过期或尚未生效，也必须拒绝。

## 权责范围

Authority 明确记录：

- 被授权主体；
- 授权签发主体；
- 角色；
- 权限字符串；
- 管辖范围；
- 空间对象类型范围；
- 必需凭证；
- 生效与失效时间；
- 外部依据。

v0.2 对管辖范围采用**精确引用匹配**，不自行猜测行政区划代码层级关系。行政层级映射留给后续 TIM/GIS/互操作适配层。

## Credential

凭证记录签发方、持有人、凭证类型、声明内容及生命周期，并使用独立签名证明签发来源。

为保证跨语言确定性，v0.2 的 claims 暂只允许字符串、整数、布尔值和 null，不允许任意浮点数。

## ReferenceCity

ReferenceCity 完成后将作为更完整的国土空间集成测试数据源。在此之前，v0.2 使用体量很小的合成 Reference City fixture，因此不会阻塞协议开发。
