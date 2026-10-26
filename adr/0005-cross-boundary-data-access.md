# ADR-0005: Cross-boundary data-access pattern (curated exports vs. direct Athena)

**Status:** Proposed (blocker — needs client input; owned by the Data Engineering lane) · **Date:** 2026-09-22 · **Amended:** 2026-10-15 (ownership reframe + batch-02 source inventory) · **Deciders:** Illia Slobozhanin (Data Eng lane), Rodrigo Cunha (ML lane, requirements side); pending client + infra lane

**Context.** The bidder most likely runs in its own AWS account (the client's docs say "most likely"; a competing doc frames it as a Terraform-ownership boundary inside shared infra instead) and must consume client data (training data + online features) across an account boundary either way. The docs conflict: the infra-and-data-context doc says use **curated, bidder-prepared datasets** (push/export); the infra doc prescribes **direct Athena + Glue + Lake Formation** grants (pull/query). The batch-02 ML report made the question concrete by naming the internal source tables (auctions and bid logs in `vir-prod-uaadsmanager-reporting-db`, east/west; batched `win_logs` and the web/app conversion and per-window attribution tables in `ua-data-jobs-prod-reporting`; a streamed `silver_win_logs_stream`) — whether that list is the menu the client curates from, or tables we query directly, is unresolved.

**Decision (ownership, 2026-10-15).** This decision belongs to the **Data Engineering lane** (team DE, not yet started), together with the curation mechanics it implies (regional unions, batched-vs-streamed reconciliation, cross-account mechanism, identity-mapping execution). The **ML lane treats the five curated datasets as a given** — whether the client delivers them or our DE curates them from the named sources is immaterial to the ML platform design. The ML lane's part is the **requirements contract** on those datasets: the impression-level dataset is the label universe (served impressions) and carries a key the attribution rows reference; the attribution dataset preserves per-window structure and `event_name`; the id triplets arrive filled; hot-feature inputs meet the freshness floor. Working lean on the pattern itself is unchanged: curated datasets for pipelines, direct Athena at most for exploration.

**Why.**
- Curated exports (push): the client owns joins/identity mapping and cadence; stable contract, decoupled from the client schema; least ML-lane scope. Less flexible for ad-hoc needs.
- Direct Athena/Lake Formation (pull): the consuming side owns the joins; flexible and always-current; couples to the client schema, heavier cross-account IAM, largest scope increase — now DE-lane scope, not ML-lane.
- Hybrid: the client delivers core joined datasets; scoped direct access for exploration.

**Consequences.**
- Still the critical path for training data and online features; drives IAM, feature freshness, schema-coupling risk. Escalation and resolution sit with the DE and infra lanes.
- The ML-lane docs (`design_docs/`) design against the five curated datasets and record the requirements contract; they adapt to whichever mechanism the DE lane lands.
- The batch-02 table list is recorded as the provenance inventory for the DE's work.
