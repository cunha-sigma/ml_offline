# ADR-0000: Record architecture decisions for this project

**Status:** Accepted · **Date:** 2026-09-22 · **Deciders:** Rodrigo Cunha

**Context.** client custom-bidding-agent is in discovery; decisions formed from client docs and analysis need a durable record that survives across sessions and team members.

**Decision.** Keep a lightweight ADR set (MADR-lite), ML-lane focused, recording only load-bearing decisions — those costly to reverse or needed to keep downstream work coherent. New ADRs added by agreement.

**Consequences.**
- Single place for why the system is shaped as it is; update the `README.md` index on every add or status change.
- Non-critical detail stays in working docs (`DISCOVERY_SUMMARY.md`, `scratchpad.md`), not here.
