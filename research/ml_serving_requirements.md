# Requirements/gaps for `ml_serving`

**Status:** reconciled 2026-11-19 against the serving lane's per-item
record (`ml_serving_requirements.md` at the `ml_serving` repo root,
now 15 items) and its code at commit `63101d0` (branch
`updates-from-desing-docs`). **Items 1–14 are done** — the original
nine plus four of the five asks we sent on 2026-11-19
(`scratch/ml_serving_requirements_update.md`). Item 15 (hot-store
credential rotation) stays open as a joint design. Canonical source on
the offline side: `design_docs/OPEN_QUESTIONS.md` → "Serving-side
changes to schedule" and `scratchpad.md` → "Cross-repo follow-ups."

## Done — the 2026-11-19 wave (items 11–14)

- **`sample_rate` validation (11):** `Validate` rejects a shadow
  challenger whose rate is outside (0, 1] — fail static; a shadow
  config that would silently score nothing now fails the revision.
  Other modes ignore the field, so a leftover rate cannot brick a
  canary revision.
- **Hot-feature values in decision rows (12):**
  `DecisionRecord.InputsHot` carries the values the assembler joined
  from the hot snapshot (declared default on fallback, marked by
  `DefaultedFields`), on serving and shadow paths alike. The three
  maps together are the complete model input. Deliberate split we are
  asked to confirm: `InputsNumeric`/`InputsText` log the payload
  as-sent and unfiltered (joinless replay of any model);
  `InputsHot` is manifest-bounded — the witness of what the served
  model saw, **not** the hot-feature replay substrate. Replaying a
  *new* hot feature is our side: our pipelines keep queryable history
  of hot values (`derived.feature_<model>_*` and the shared
  definitions), joined by the logged join keys. Our design already
  archives this, so the assumption holds — confirmation owed to the
  serving lane; if we ever cannot archive, widening the rows gets
  revisited.
- **Doc alignment (13):** `queued` is consumable data moved by the
  readout pass's plain config write (self-trigger wording gone);
  the deployment doc's rollout sequence starts at the absolute
  training-time gate instead of offline replay.
- **S3 sync dissolved (14):** `Options.ModelRoot` points a Slot at the
  model's folder — S3 or local — and the lib reads and polls
  `<root>/rollout_config.json` itself, resolving relative version URIs
  against the root. No file lands in the pod, so there is no sync
  component to own; rollback propagation is bounded by
  `ConfigPollInterval` (30 s default) alone. Supersedes both the old
  "S3 config source" ask and the "config stays file-based" decision.

## Done — the original nine (their items 1–10 record)

Closed doc questions (approval placement, label delay), slot naming
documented, full `DecisionRecord` shape, rollout-config restructure
(`queued`, fleet-load mode, A/B nested in canary), per-candidate
`Scores`, wired challenger routing, dimensioned metrics
(+ `CountModelLoaded`, `Slot.LiveVersions`, shadow counters), the
shadow scorer, the artifact S3 source, Redis auth/TLS options.
Decisions that bind us: no response-metadata fields are coming
(goal/window ride in `model_name` per slot naming; revision rides the
decision row — ADR-0001's response-contents wording to amend);
routing unit must be request-level, one arm per request.

## Open

1. **Hot-store credential rotation (their item 15)** — joint design:
   our Airflow jobs hold the writer credentials, so the scheme
   constrains both sides. Context and candidates in their
   `docs/OPEN_QUESTIONS.md`.
2. **Staged config propagation + alarm-rollback ownership** — still
   unassigned in both repos; the propagation hop itself simplified
   (one poll against the S3 root), the staging/alarm-rollback
   ownership question remains.
3. **Deferred:** multi-slot capacity sizing (now including the
   shadow-session reservation; waits on the goal count and the
   vendor-pending candidates-per-request maximum); hot-key TTL
   semantics ownership.

## Standing prerequisite (agent config, not lib code)

Shadow scoring runs only on pods built with `Options.ShadowSessions >
0` — a process setting the rollout config cannot enable — and those
sessions are a permanent core reservation. Both belong in the serving
capacity sizing.
