---
name: doc-conventions
description: Where the writing and structural conventions for this repo live, plus the few universal rules not written elsewhere. Read before editing any doc in the repo root, adr/, or design_docs/.
---

# Doc conventions (client ML discovery)

The conventions are owned by the CLAUDE.md files, not duplicated here:

- Root `CLAUDE.md` — repo-wide conventions (Python offline / Go serving, ADRs by agreement for load-bearing decisions only, direct and non-verbose prose, client questions must read as real, self-contained questions).
- `design_docs/CLAUDE.md` — the strictest set, for everything in that folder: writing style (banned LLM smells, structure rules), the no-assumptions rule, and the no-outside-references rule (nothing points at `../` anything, including ADR numbers — `adr/` is outside the folder; external repos only by GitHub URL).
- `adr/README.md` — ADR style (MADR-lite, ~15 lines, atomic); `adr/template.md` — the section set (Context / Decision / Why / Consequences).

Universal rules not stated elsewhere:

- Team voice ("we/our") in all project docs; never address the reader as "you".
- **Anonymization** (rule stated in root `CLAUDE.md`): never name the client, its parent company, or its vendors — "the client", "the ad-server vendor", "the web-attribution provider", "the upstream DSP". Exceptions: literal data identifiers in backticks and client-original files stay verbatim. Every new client doc reparsed into a `md/` folder gets the anonymization pass before anything cites it.
- Client questions are referenced **by topic**, never by Q-number, outside the delivered report's own frozen Q1–Q16 list. The living register is `design_docs/OPEN_QUESTIONS.md`. Delivered reports under `reports/` are frozen — never edit them.
- `DISCOVERY_SUMMARY.md` keeps Part 1 (client facts) and Part 2 (our analysis) strictly separate; anything not client-attributable in Part 1 must be explicitly attributed (SW team / ours) or moved.
- When client sources disagree or a fact comes from one doc only, state the provenance (batch-01 vs batch-02) instead of presenting one side as settled.
- Scratchpad entries: short atomic bullets, info-dense, no long paragraphs.
