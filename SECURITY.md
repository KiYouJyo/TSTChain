# Security Policy

TST Chain 处理的核心问题包括证据完整性、数字签名、权责映射、规划规则版本和跨层级检查点，因此安全设计属于协议的一部分，而不是发布后的附加项。

## 当前状态

项目目前处于早期 Foundation 阶段，尚未形成经过生产安全审计的正式版本。当前代码、Schema、示例或原型均不应直接视为行政审批、法定规划成果或关键基础设施场景的生产级实现。

## 高优先级安全边界

后续实现必须重点防止：

- canonical serialization 不一致导致的 Hash 分叉；
- 签名载荷与显示内容不一致；
- 证据 Hash 与外部文件错配；
- 过期、撤销或越权 Credential 被继续接受；
- Authority / jurisdiction 校验缺失；
- Planning Rule 被静默覆盖而非形成新版本；
- Spatial Event 被重排、回滚或伪造；
- checkpoint 重放或跨域冒用；
- 多语言文本进入签名或共识关键字段；
- 外部 URI 指向内容变化但证据未更新；
- 规则引擎结果被错误表示为行政决定；
- 敏感业务数据因“上链”而被不必要公开。

## 数据最小化

默认采用“数据不上链，证据与关系上链”。不得因为可追溯需求而将个人信息、敏感业务材料、大体量空间原始数据或不应公开的行政数据直接写入公开不可变账本。

## 密码与密钥

在密码学实现尚未固定前：

- 不自行设计密码算法；
- 不把测试密钥用于真实业务；
- 私钥不得进入仓库、示例数据或日志；
- 签名、Hash、证书与密钥轮换策略必须保持可替换接口；
- 生产实现应根据部署环境适配适用的密码、电子认证与安全规范。

## 报告漏洞

在专用私密漏洞报告通道建立前，请不要在公开 Issue 中提交可直接利用的私钥泄露、签名绕过、权限提升或数据暴露细节。项目进入可执行代码阶段后，应优先启用 GitHub Private Vulnerability Reporting 或等价私密渠道。

## Security review gates

以下阶段进入下一阶段前应进行专门安全复核：

1. canonical serialization / content hash；
2. digital signature / credential；
3. authority policy；
4. distributed ledger / consensus；
5. hierarchical checkpoint；
6. external system adapters；
7. production deployment profile。
