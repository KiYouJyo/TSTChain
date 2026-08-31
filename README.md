# 国土空间可信链 / Territorial Spatial Trust Chain

**TST Chain** 是面向国土空间规划全生命周期的分布式可信数字基础设施。项目目标不是以区块链替代 GIS、TIM、CSPON、“一张图”或既有规划业务系统，而是在其之下建立统一的 **可信关系层、可信事件层与规划谱系层**。

[简体中文](README.md) · [日本語](docs/ja-JP/README.md) · [English](docs/en-US/README.md)

> **Spatial data describes the world. Planning rules constrain the world. AI interprets the world. TST Chain proves why the information can be trusted.**

## 系统目标

TST Chain 围绕国土空间治理中的四类核心对象建立长期、可验证、可追溯的数字关系：

- **Spatial Object / 空间对象**：行政单元、规划单元、地块、建筑、道路、生态空间、基础设施等。
- **Planning Rule / 规划规则**：用途、指标、控制线、准入条件、规划要求及其版本。
- **Spatial Event / 空间事件**：调查、编制、调整、审批、许可、建设、核实、监测、评估、更新等事件。
- **Authority / 权责主体**：规划编制、审批、管理、监督及相关机构与人员。

在此基础上形成 **Provenance / 规划谱系**，实现“现状—规划—审批—实施—监测—评估—调整”全过程的可验证关联，为规划传导、用途管制、智能审查、实施监督、CSPON、规划知识图谱与规划 AI 提供可信数字基础。

## 技术原则

1. **规划优先，非金融优先**：主线不以代币、DeFi、交易市场为目标。
2. **数据不上链，证据与关系上链**：GIS、BIM、遥感、文档等大体量数据保存在既有平台；链上保存对象标识、Hash、版本、签名、关系与状态变化。
3. **现实权责映射**：链不创造行政权力，仅验证现实制度中已经存在的权责与数字行为。
4. **规则可机器读取**：规划指标、控制线和用途规则逐步标准化为可计算的 Planning Rule。
5. **分层分域扩展**：面向国家—省—市—县等治理层级设计可扩展的验证与检查点体系。
6. **TIM/CSPON 兼容优先**：优先适配正在形成的国土空间信息模型、监测网络和“一张图”体系，不重复建设 GIS 数据底座。
7. **协议稳定、实现可替换**：核心价值是可验证的国土空间协议与数据模型，而不是绑定某一种区块链实现。

## 总体技术路线

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

## 核心模块

| 模块 | 职责 |
| --- | --- |
| `SpatialObject` | 国土空间对象统一身份、类型、层级与外部数据引用 |
| `SpatialEvent` | 空间对象全生命周期事件与状态变化 |
| `PlanningRule` | 机器可读的规划规则、依据、适用范围和版本 |
| `Authority` | 机构、人员、职权、凭证与签名 |
| `Provenance` | 规划版本、调整历史、上下级传导和依据追溯 |
| `Evidence` | 文件 Hash、时间戳、签名和外部证据引用 |
| `Workflow` | 编制、审查、审批、许可、核实、监测等业务状态机 |
| `Interop` | GIS、TIM、CSPON、BIM/IFC、遥感及现有业务平台适配 |

## 当前阶段

当前仓库处于 **Foundation / 仓库与协议基础阶段**。近期重点是：

- 建立三语文档与术语体系；
- 固化核心领域模型与命名规范；
- 定义 v0.1 协议边界；
- 建立最小可验证的 Spatial Object + Spatial Event 原型；
- 为后续 Authority、Planning Rule、Provenance 与分层网络实现留出稳定接口。

详见 [开发路线图](ROADMAP.md) 与 [架构说明](docs/zh-CN/ARCHITECTURE.md)。

## 三语支持

仓库正式支持：

- `zh-CN`：简体中文
- `ja-JP`：日本語
- `en-US`：English

协议字段、代码符号和持久化 key 统一使用英文；用户可见文本通过 `locales/` 管理。术语翻译必须遵循 [本地化规范](docs/zh-CN/I18N.md)。

## 项目边界

TST Chain 当前不将以下内容作为主线：

- 可交易原生代币；
- 虚拟货币融资或兑换；
- 以 NFT 替代土地、房屋或行政许可的法定权利凭证；
- 将大体量 GIS/BIM/遥感原始数据直接写入链；
- 用智能合约替代依法应由行政主体作出的裁量和审批决定。

## Repository

`KiYouJyo/TSTChain`

项目全称：**Territorial Spatial Trust Chain**  
中文名：**国土空间可信链**  
日文名：**国土空間信頼チェーン**
