# Contributing to TST Chain

感谢参与 **Territorial Spatial Trust Chain / 国土空间可信链**。

## 基本原则

任何贡献都应优先维护以下项目边界：

- 国土空间规划领域优先；
- 协议与数据模型优先于具体链实现；
- 现实权责优先于链上自定义权力；
- 原始大数据链下保存，链上保存证据、关系、版本与状态变化；
- 本地化文本不得进入 canonical payload、签名载荷或共识关键字段；
- 不把可交易代币、DeFi、虚拟货币融资作为核心功能。

## 分支与提交

建议分支命名：

```text
feature/<topic>
fix/<topic>
docs/<topic>
chore/<topic>
research/<topic>
```

建议 Conventional Commit 风格：

```text
feat: add spatial event validation
fix: reject mismatched evidence hash
docs: clarify planning rule provenance
chore: update locale parity checks
```

## 变更分类

### 协议变更

涉及以下内容时必须明确标记为协议变更：

- Schema 字段新增、删除或语义改变；
- canonical serialization；
- Hash / signature payload；
- ID 格式；
- 枚举值；
- ledger state transition；
- checkpoint / proof 格式。

协议变更必须说明兼容性影响，并更新测试向量。

### 本地化变更

新增用户可见 key 时必须同步更新：

- `locales/zh-CN.json`
- `locales/ja-JP.json`
- `locales/en-US.json`

三份文件必须保持完全一致的 key 集合。

### 规划领域术语变更

核心术语应保持稳定。涉及中国特有制度概念时，中文定义优先保证制度准确性，日英译文用于解释和国际交流，不应反向改变中文业务语义。

## Pull Request 最低要求

PR 应说明：

1. 解决什么问题；
2. 是否改变协议或 Schema；
3. 是否影响三语资源；
4. 是否影响兼容性、安全性或权责模型；
5. 如何测试；
6. 若涉及规划业务，现实业务语义是什么。

## 测试原则

核心协议至少应覆盖：

- deterministic / canonical serialization；
- content hash stability；
- signature verification；
- schema validation；
- provenance integrity；
- locale key parity；
- invalid authority / invalid transition rejection。

## 文档语言

正式支持：

- 简体中文 `zh-CN`
- 日本語 `ja-JP`
- English `en-US`

代码、协议字段、机器 key 使用英文。核心设计文档优先保持三语结构同步。
