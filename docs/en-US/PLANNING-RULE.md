# Planning Rule Protocol — v0.3

TST Chain v0.3 makes planning requirements versioned, machine-readable and verifiable.

A `PlanningRule` states **what** must be checked; a `RuleEngine` states **how** a particular input was evaluated. The ledger records the rule version, input digest, engine identity and result. It does not replace GIS, BIM, TIM, or administrative discretion.

### Supported rule expressions
- numeric threshold and range
- enumeration
- boolean
- spatial predicates

Decimals use canonical strings such as `"2.5"` and `"45"`. JSON floats are excluded from protocol facts.

### Exceptions
Exceptions are explicit objects with their own issuer, validity period and basis. They never silently mutate a rule. `review_required` produces a `review` outcome rather than an automatic approval/rejection.

### External engine profile
`TST-RULE-ENGINE/0.3` declares capabilities. GIS/BIM/TIM implementations may compute geometry or model facts off-chain and return evidence-backed observations.

### Result semantics
`pass`, `fail`, `review`, `not_applicable`, and `error` describe machine evaluation only. Production systems must keep statutory/administrative decisions as separate signed events.
