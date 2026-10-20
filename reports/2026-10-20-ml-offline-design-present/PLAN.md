# Presentation plan — ML offline design: where we stand

Talk for the team. 30–45 min + 15 min Q&A. Support deck (low text) —
slides are visual cues; the talk carries the content. Source: this
repo's `design_docs/`, `adr/`, `DISCOVERY_SUMMARY.md`, `scratchpad.md`
as of 2026-10-20.

## Who's in the room (tailoring)

- **Matheus (Senior ML Eng)** — knows ML; cares about model/calibration
  mechanics and the serving contract's precision.
- **Illia (Principal Data Eng)** — cares about the data-access boundary,
  dataset ownership, what's confirmed vs. open with the client.
- **Augusto, Yuri (Senior/Lead SW Dev, Go platform side)** — care about
  the serving contract, latency budget, what changes on their side.
- **Olena (Principal QA)** — cares about what's testable, validation
  gates, rollout guardrails.
- Potential future reuse: an adapted cut for the client. Keep the deck
  anonymization-clean (no client/parent/vendor names) so that cut is a
  trim, not a rewrite.

Role-agnostic language throughout — general lane terms (DE lane,
serving side, QA surface), no teammate names on slides.

## The one thing they should leave knowing

**The offline ML design is a complete, concrete pipeline with a fixed
contract to the Go serving side — not a research sketch.** Two
specific things block building it, both need the client, and they're
named. Everything else is ready to build once those clear.

Two myths to bust:
1. "This is just a model" — it's a pipeline (data → labels/features →
   train/calibrate → deploy/roll out → monitor) plus a serving
   contract, not a notebook artifact.
2. "We're blocked on everything" — most of the design is settled; the
   open items are two named client-facing blockers, not an open-ended
   fog.

## Narrative arc

1. Frame the question → 2. The system today, in one picture → 3.
What's already decided → 4. What composes the offline design → 5. The
contract with serving → 6. Infra this needs → 7. What's still open →
8. What happens next → 9. Discussion.

## Slide-by-slide outline (~27 slides, ~35–40 min + Q&A)

**Framing (2)**
1. Title.
2. The question / agenda + the two myths.

**Part 1 — The system today (3)**
3. [divider] Part 1.
4. The business unlock — today: every advertiser is awareness/CPM;
   this unlocks performance (CPA) bidding. Bid formula as a diagram.
5. Four services, one diagram; our lane = `P(Goal Action | Impression)`.

**Part 2 — What's already decided (4)**
6. [divider] Part 2.
7. Decision table — the four load-bearing ADRs at a glance, status
   tags.
8. Two worlds — offline (Python/Databricks) trains, online (Go,
   embedded) serves, ONNX is the bridge.
9. The latency budget — 10 ms whole-agent timeout vs. the ML step's
   own firm ~3 ms slice.

**Part 3 — What composes the offline design (6)**
10. [divider] Part 3.
11. One end-to-end diagram: data in → labels/features → train &
    calibrate → deploy & roll out → monitor, feeding back.
12. Data in — five curated datasets; what we require vs. who produces
    them (open, DE-lane/client boundary).
13. Building the training set — label join + shared feature
    definitions (hot store for serving, materialized tables for
    training).
14. Train & calibrate — GBDT → ONNX, calibration baked in as a
    matched pair, evaluation gates.
15. Deploy & roll out — one deployment job, progressive rollout
    states, two human approval gates, automatic abort on guardrail
    breach.
16. Monitor & retrain — drift/calibration checks close the loop.

**Part 4 — The contract with serving (3)**
17. [divider] Part 4.
18. The four touchpoints diagram — artifact+manifest, rollout config,
    hot-feature store, decision logs — who writes, who reads.
19. Why this boundary matters — what changes on which side, when.

**Part 5 — Infra this needs (3)**
20. [divider] Part 5.
21. The stack, confirmed vs. ours-to-decide — one table.
22. New things to stand up — two repos, Redis, orchestration.

**Part 6 — What's still open (3)**
23. [divider] Part 6.
24. The two real client-facing blockers, named plainly (attribution
    window + method; cross-boundary data-access mechanism).
25. Everything else — categorized counts only, pointing at the living
    register.

**Part 7 — What happens next (2)**
26. [divider] Part 7.
27. The path forward — phase diagram: resolve blockers → EDA → build.

**Wrap (2)**
28. Takeaways recap.
29. Discussion — seed questions for Q&A.

## Design rules for the deck

- **Low text.** Per slide: a short title + one diagram *or* ≤5
  bullets. No paragraphs.
- Visual-first: a mermaid diagram for every pipeline/flow claim, a
  table for every comparison/decision/status claim.
- Role-agnostic — no teammate names.
- Anonymization carries over from the repo's standing rule: never name
  the client, parent company, or vendors; no raw table names on
  slides (simplify rather than cite — this is a talk, not a design
  doc).
- No ADR numbers, file paths, or internal doc citations visible on
  slides — those live in the speaker notes only, for Q&A backup.
- Status/provenance tags where relevant (Settled / Ours / Open /
  Client-blocked).
- Speaker notes (HTML comments) carry the talk track; slides are
  visual cues.
- English; Slidev `default` theme, `slide-left` transition, paginated.
