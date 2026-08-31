# Territorial Spatial Trust Chain

**TST Chain** is a trusted digital infrastructure project for the full lifecycle of territorial spatial planning.

[简体中文](../../README.md) · [日本語](../ja-JP/README.md) · **English**

TST Chain does **not** aim to replace GIS, TIM, CSPON, planning supervision platforms, BIM, or existing administrative systems. It provides a common **trust, event, evidence, and provenance layer** beneath them.

## Core domain model

- **Spatial Object** — administrative units, planning units, parcels, buildings, roads, ecological spaces, infrastructure, and other territorial entities.
- **Planning Rule** — land-use rules, indicators, control boundaries, access conditions, planning requirements, and their versions.
- **Spatial Event** — survey, plan preparation, amendment, review, approval, permit, construction, verification, monitoring, evaluation, and renewal events.
- **Authority** — organizations, persons, roles, jurisdictions, credentials, and legally grounded powers.
- **Provenance** — verifiable relationships showing where plans, rules, indicators, and spatial states came from and how they changed or were transmitted across planning levels.

## Design principles

1. **Planning-first, not finance-first.** Tradable tokens, DeFi, and speculative markets are outside the core roadmap.
2. **Keep source data off-chain; anchor evidence and relationships on-chain.** Large GIS, BIM, remote-sensing, documents, and sensor datasets stay in their native systems.
3. **Map real-world authority; do not invent it.** The chain validates digitally expressed authority but does not create legal or administrative power.
4. **Make planning rules machine-readable and versioned.** External GIS/BIM/rule engines perform computation; TST Chain proves which rules and inputs were used.
5. **Scale by jurisdiction and hierarchy.** Local domains process local events while upper layers verify signed checkpoints rather than replicating every record.
6. **Prefer compatibility with TIM/CSPON and existing planning platforms.** TST Chain is a trust layer, not another GIS database.
7. **Keep the protocol durable and implementations replaceable.** The long-term asset is the verifiable territorial spatial model and protocol.

## Architecture

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

See the [roadmap](../../ROADMAP.md), the [architecture overview](ARCHITECTURE.md), and the localization policy in `locales/` and `docs/zh-CN/I18N.md`.

## Repository languages

The repository officially supports:

- `zh-CN` — Simplified Chinese
- `ja-JP` — Japanese
- `en-US` — English

Protocol fields, schema identifiers, enum values, persistent keys, canonical payloads, and code symbols use stable English machine identifiers. Human-facing text is localized separately and must never change consensus-critical bytes.

## Project identity

**English:** Territorial Spatial Trust Chain  
**Chinese:** 国土空间可信链  
**Japanese:** 国土空間信頼チェーン  
**Short name:** TST Chain
