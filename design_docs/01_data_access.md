# 01 — Data access

How we read the input data `00_overview.md` assumes is already on S3,
in an account we can read. How it got there is out of scope; this doc
is the read path from that data into Databricks, and nothing before
it.

## What we read

The five curated datasets below, taken as a given. The client's stated design
principle is that the bidder consumes curated outputs prepared on a
defined cadence, not raw internal production tables; whether the client
delivers them directly or our team's Data Engineer curates them from
the client's internal tables is the Data Engineering lane's scope and
immaterial to this platform. This doc states what we consume and what
we require of it; provenance, curation mechanics, and the boundary
mechanism are recorded here only as reference for the DE lane.

The client has proposed, not yet finalized, a five-dataset split for what
crosses the account boundary:

- Delivery-control feed — low-latency campaign, ad set, ad, creative,
  budget, status, targeting, and override state. The pacing and
  ingestor lanes' input; not ours directly.
- Impression-level training dataset — joined delivery, campaign, ad
  set, ad, creative, supply, bid, win, spend, and event-outcome data
  (the client's wording). Our working assumption, to confirm: it is wins-only,
  every row a served impression — the client's description does not say so.
  This is the training and label universe, our primary input
  (`03_labels.md` open question 3).
- Attribution labels dataset — conversion and attribution outputs
  joined back to impressions, ads, ad sets, campaigns, and attribution
  windows. Feeds `03_labels.md` directly.
- Aggregate performance dataset — hourly or daily rollups for pacing,
  reporting validation, and spend reconciliation. A secondary input,
  used for data-quality checks against the other two.
- Bidder response dataset — outbound: our decisions and model outputs,
  sent back to the client. Not an input to us. The client stated the need (visibility
  into how the bidder decided) and a candidate field list
  (auction/request IDs, the client and DSP IDs, bid/no-bid decision, bid
  price, model version, decision timestamp, latency, no-bid reason,
  selected optimization strategy), but delegated mechanism and final
  shape to us. Of the nine, model version and decision timestamp map to
  our decision log directly and entity ids map at candidate level; bid
  price, bid/no-bid, and no-bid reason belong to the Bid
  Decision/Response service; auction/request ids are the known
  serving-row gap; latency and optimization strategy come from the
  agent, not our rows. Assembling this dataset crosses lanes.
  Owned and designed by `09_monitoring.md` (a derived table plus an
  export job).

### Provenance inventory (reference for the DE lane)

The batch-02 ML Service Background names the internal tables training
data comes from, across two databases. The query engine is unstated in
that report — Athena is our inference from the client's stack, not
client-confirmed. These are the client's internal names; whether the curated datasets ship off them as-is or repackaged
is the DE lane's question, not ours. Recorded as the provenance menu:

- `vir-prod-uaadsmanager-reporting-db` — auctions
  (`auction_us_east`/`auction_us_west`), bid logs
  (`bid_logs_us_east`/`bid_logs_us_west`), and a streamed win-log
  table (`silver_win_logs_stream`). Regional east/west splits mean the
  curation step unions them.
- `ua-data-jobs-prod-reporting` — batched `win_logs` (the likely
  source of the impression-level dataset), pixel events
  (`silver_kochava_events`), per-window web attribution
  (`gold_kochava_seven_day_attribution`; the report notes
  one/fourteen/thirty-day variants are available — the 1-day one is
  not in the client's data models and needs confirming), app events
  (`bronze_mobile_app_events`), and per-window app attribution
  (`gold_app_events_seven_day_attribution`, same window variants).

Two notes that cross back into our scope: the per-window gold tables
match the union structure `02_datasets.md` gives
`cleaned.attribution_labels`; and auction/bid tables appearing in a
training-data list does not change the label universe — they are
feature and analysis sources only (`03_labels.md`).

## The account boundary

Owned by the Data Engineering and infra lanes; kept here as reference
because it bounds what we can assume about freshness and read paths.

The bidder, and this whole offline platform with it, most likely runs
in its own AWS account, separate from the client's core account; one client doc
says "most likely", another frames the boundary as Terraform ownership
within a shared VPC (with the bidder's security group added to the client's RDS
ingress), so the account topology itself is not final. Either way, the client
remains the source of truth for campaign configuration, delivery
eligibility, attribution logic, and governed warehouse outputs, and
crossing the boundary needs an explicit mechanism. The client names the
candidates, undecided among them: cross-account IAM roles, Lake
Formation sharing, S3 replication or export buckets, event streams,
APIs, or other approved transfer mechanisms.

This is the substance behind working assumption 4 in `PLAN.md` (the
five curated datasets are a given): something will cross that
boundary, but which mechanism, and therefore what we actually read
against, is not yet chosen — by the DE lane.

## Source format

The client's warehouse is Apache Iceberg tables over S3, queried through
Athena, governed by Glue Catalog and Lake Formation — plus Postgres as
the source of truth for config and entity state. Attribution outputs
land in both Postgres and the Athena-accessible tables. Whatever
curated dataset we receive most likely inherits the Iceberg-over-S3
shape, either the tables themselves or a flat export off them; which
one depends on the mechanism chosen above. Config/entity data (the
campaign hierarchy) is Postgres-origin on the client's side; whether any
curated dataset is delivered out of Postgres is open, and we do not
plan direct Postgres reads.

## Read path into Databricks

Decision: Unity Catalog external tables over external locations,
reading data where it lands rather than copying it in first, matching
working assumption 1.

Two cases, depending on the boundary mechanism:

- Lake Formation sharing of the Iceberg tables themselves: we read
  them directly, Unity Catalog's Iceberg read support covers this
  without a conversion step.
- A flat S3 export or replication bucket instead: Unity Catalog
  external tables over that bucket cover it the same way.

Either way, the raw layer (`02_datasets.md`) is a typed view over data
that stays where the client put it; we don't maintain a second copy.

## Athena's role

The client docs hold two positions. One expects the bidder to consume
curated outputs only (quoted above). The other prescribes direct access
infrastructure for the bidder: an Athena workgroup, Glue reads, Lake
Formation grants, and Postgres connectivity on port 5432. The client
has not reconciled them; resolving the access pattern is the DE lane's
work (below).

Our lean, pending that answer: curated-first. Pipelines read through
Unity Catalog only; direct Athena, if granted, serves exploratory
analysis at most, never a pipeline dependency. We don't stand up a
parallel Athena path, and we don't plan direct Postgres reads.

## Access control

Read-only, scoped per source: one credential (IAM role, Lake Formation
grant, or storage credential, depending on the mechanism chosen) per
external location, least privilege, no write access to any client bucket
or table. Writes into the serving-shared state (artifact store, rollout config)
are the deployment job's alone (`07_deployment_job.md`); our pipelines
write only our own catalogs and Redis, never the client location.

## Cadence

The client's stated cadence tiers for what crosses the boundary, not yet
finalized:

- Immediate / event-driven — delivery eligibility changes. Pacing and
  ingestor lane, not ours.
- Frequent / near-real-time — delivery settings, bid config,
  targeting. Pacing and ingestor lane.
- Hourly — delivery metrics, spend, impressions, clicks, win rate,
  bid/win diagnostics.
- Daily — attributed conversions, finalized reporting, training
  labels, feature snapshots.
- Weekly / backfill — large historical training sets, attribution
  reprocessing, feature rebuilds.

Our two label-side inputs land at the daily tier (the client names attributed
conversions, training labels, and feature snapshots there) with large
historical sets at the weekly tier. The tension that matters now:
`04_features.md` proposed a 10-minute hot-feature job cadence against
30-minute windows, but the client's stated tier for delivery metrics,
impressions, and clicks (the events hot features aggregate) is hourly.
The client ingests raw delivery data near real-time on its own side (a
dedicated Kinesis stream from the DSP), and its internal inventory
includes a streamed win-log table (`silver_win_logs_stream`, provenance
inventory above), so fresher boundary feeds are physically possible —
but nothing fresher than hourly is currently stated for what crosses
to us. Whether the streamed table can back a fresher curated feed is a
question for the DE lane. Unless a fresher feed is negotiated, hot
features work within an hourly freshness floor, and the 10-minute job
cadence only reduces our own share of the delay. The "still to be
determined" cadence language in the client's docs refers to the
delivery-control feed, which is the pacing lane's input, not ours.
The freshness budget is tracked as `04_features.md`'s open question 1.

## Open questions

1. Which cross-account mechanism the client chooses (Lake Formation sharing,
   S3 export or replication, event stream, or API), and therefore the
   concrete read path and freshness we actually get. Owned by the DE
   lane; everything above adapts to whichever answer arrives.
2. Whether the five proposed datasets ship as named or get reshaped;
   exact schemas and bucket or table names either way. Owned by the DE
   lane, with our requirements as input (label universe and join key,
   per-window attribution structure and `event_name`, filled id
   triplets, freshness floor).
3. The boundary feed's real freshness for delivery events, which sets
   the hot-feature floor; the budget itself is owned by
   `04_features.md`'s open question 1, resolved together with question
   1 here.
4. The bidder response dataset's assembly is designed
   (`09_monitoring.md`); what remains open is the client's required field list,
   cadence, and consumers, plus the Bid Decision/Response service's
   fields — their call and the agent lane's, respectively.