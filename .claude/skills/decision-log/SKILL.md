---
name: decision-log
description: How to add, resolve, supersede, or withdraw an Architecture Decision Record (ADR) in adr/ and keep the adr/README.md index in sync. Use when a new load-bearing decision arises for the client bidding-agent ML lane, when the author resolves an open blocker, or when a client answer changes a decision.
---

# ADR workflow (client ML discovery)

Architecture decisions live as **ADRs** in `adr/` (MADR-lite; see `adr/template.md` and `ADR-0000`). The index is **`adr/README.md`**.

## When to write an ADR

Only for **load-bearing** decisions — costly to reverse, or needed to keep downstream work coherent. Not every step. **Add ADRs by agreement**: propose the decision to the author first; write it once approved. Non-critical detail stays in `DISCOVERY_SUMMARY.md` or `scratchpad.md`.

## Statuses

`Proposed` · `Accepted` · `Superseded` · `Withdrawn`.
- **Accepted** = our working decision during discovery (may still be revised on client input).
- **Proposed (blocker)** = decision framed with options + our lean, but needs a client answer before work proceeds (e.g. ADR-0004 attribution label, ADR-0005 data access).

## To add a new ADR

1. Copy `adr/template.md` → `adr/000N-short-title.md` (next number).
2. Fill Context / Decision / Why / Consequences (per `adr/template.md`). State the decision plainly.
3. Cross-link related ADRs by relative path (e.g. `[ADR-0003](0003-calibration-matched-pair-artifact.md)`).
4. Add a row to the table in `adr/README.md`.

## To resolve a `Proposed (blocker)`

When the client answers: set `Status: Accepted` (date, deciders), replace the "pending" Decision with the concrete outcome, fill Consequences, and update the `adr/README.md` row. Propagate the resolved fact into `DISCOVERY_SUMMARY.md` and `scratchpad.md` where it appears (never into the frozen reports under `reports/`).

## To supersede / withdraw

- **Supersede:** new ADR `Status: Accepted` with a "Supersedes ADR-000X" note; set the old one `Status: Superseded` pointing forward. Keep both files.
- **Withdraw:** set `Status: Withdrawn` with a one-line reason; keep the file as a tombstone so numbers don't shift.

Always keep the `adr/README.md` index consistent with the files.
