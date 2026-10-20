---
name: consistency-audit
description: Run the 3-scan consistency audit on the client ML discovery repo (internal coherence / vs client docs / vs the ml_serving contract). Use before starting a new design doc, after a batch of client docs lands, or when the author asks for an audit or consistency check.
---

# Consistency audit (client ML discovery)

**Goal:** verify the live doc set is internally coherent, faithful to the client sources, and aligned with the serving contract. Findings first, fixes only after the author approves a fix plan.

## Scope

In: root `CLAUDE.md`, `DISCOVERY_SUMMARY.md`, `scratchpad.md`, `adr/*.md`, `design_docs/*.md`, `.claude/skills/`, `.claude/commands/`.
Out: `archive/` (superseded project), `docs/` (client sources — they are the yardstick, not audit targets), `reports/` (delivered, frozen artifacts — **never flag or update their content**, only files that mis-cite them) — and anything not listed as in-scope above.

## Yardsticks

- Decisions: `adr/` (0000–0006 + any later; `adr/README.md` is the index). Amended ADRs carry an "Amended" date in the status line.
- Client facts: `docs/batch_01/md/` and `docs/batch_02/md/client_reports/` (converted Markdown). `docs/batch_02/md/testing/` is team-authored (QA), never client fact.
- Serving contract: the local ml_serving checkout (real path recorded in session memory; the repo is github.com/cunha-sigma/ml_serving) — docs under its `docs/`, plus the Go types when docs are ambiguous. Its `docs/ML_SERVING_SOA.md` is an untouched external reference, not adopted design — never cite it as a serving commitment.

## Process

Launch 3 read-only Explore subagents in parallel, one per scan:

1. **Internal coherence** — contradictions between any two in-scope files, stale claims vs. the ADRs, broken cross-references (sections, ADR numbers, file paths, per-doc open-question numbers), mermaid node labels contradicting their doc's text, violations of `design_docs/`'s rules (no `../` paths, no ADR-number citations, external repos only by GitHub URL).
2. **Vs client docs** — field-level verification of every quoted or paraphrased client claim (formulas, enum values, table and field names, cadence tiers, windows). Flag anything presented as client fact that the sources don't state (exceptions: facts explicitly marked as working assumptions, and Databricks, which is client-confirmed via direct client knowledge outside the doc set). `DISCOVERY_SUMMARY.md` Part 1 must be purely client-attributable or explicitly attributed (SW team / ours).
3. **Vs ml_serving** — every claim about the four touchpoints (artifact + manifest, rollout config, hot store, decision logs), verified against the serving docs and code. Classify as MISMATCH / GAP (we assert something serving doesn't define yet — these become cross-repo follow-ups in `scratchpad.md`) / OK-but-imprecise.

Each agent reports numbered findings: file:line, short conflicting quotes, severity (HIGH = false under current decisions or sources; MED = stale or overstated; LOW = cosmetic). Agents never edit.

## After the scans

1. Consolidate and deduplicate findings; resolve conflicts between agents against the sources directly.
2. Present a fix plan to the author (plan mode); surface genuinely open judgment calls as questions rather than deciding them.
3. Apply fixes only after approval; verify with targeted greps and a re-read of changed sections; confirm the frozen report and `docs/` sources show no modifications in `git status`.

## Conventions that findings must respect

- Client questions are referenced **by topic**, never by Q-number, outside `DISCOVERY_SUMMARY.md` §2.4's own list (the delivered report's Q1–Q16 is a frozen snapshot with different numbering).
- Leans are marked as leans; working assumptions as assumptions, with who can confirm them.
- Facts get provenance when sources disagree (for example, batch-01 vs batch-02 statements).
