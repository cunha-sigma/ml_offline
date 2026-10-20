---
description: Run the 3-scan consistency audit (internal / vs client docs / vs ml_serving) via the consistency-audit skill
---

Invoke the `consistency-audit` skill and follow it: three parallel read-only scans (internal coherence; claims vs. the client sources in `docs/batch_01/md` and `docs/batch_02/md`; claims vs. the local ml_serving checkout (real path recorded in session memory)), then consolidate findings and present a fix plan for approval before editing anything.

Scope and exclusions are defined in the skill (docs/ sources, the frozen reports/ folder, and anything not listed as in-scope are out).
