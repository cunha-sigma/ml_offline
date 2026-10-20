# Client questions — ML lane

Top-priority questions for the client, 2026-10-20. Each is
self-contained and answerable without referring back to any document.

## 1. Data sources for model building

Which data will be available to us for model building, and how do we
access it?

- Served impressions (wins): which table should we treat as the
  source — `"ua-data-jobs-prod-reporting"."win_logs"`,
  `"vir-prod-uaadsmanager-reporting-db"."silver_win_logs_stream"`, or a
  curated export built from them?
- Attributed conversions: which tables should we read, and for which
  attribution windows? We see 7/14/30-day tables (for example
  `gold_kochava_seven_day_attribution`); is there also a 1-day table?
- How do the windows work operationally: one table per window, what
  update cadence, and how do reprocessing corrections land?
- Access: how does the bidder account read these — Lake Formation
  share, S3 export/replication, an event stream, or another mechanism?

*Why we ask: this unblocks exploratory analysis, which answers the
volume and window-choice questions on our side.*

## 2. Attribution windows as a product decision

Will advertisers be able to choose the attribution window per
optimization goal, or will each goal use one fixed window?

- If selectable: which windows will be offered per goal (1, 7, 14, 30
  days?), and where does the choice live — as part of the goal value
  (for example `PIXEL_PURCHASE_7_day`) or as a separate ad set field?
- If fixed: which window per goal, and who decides it?

*Why we ask: this sets the model granularity — one model per goal, or
one per goal and window — and how many label definitions we maintain.*

## 3. Identifying served impressions and joining them to conversions

- How do we identify served impressions in the impression-level data:
  is there a field that marks a win/served row (so we can filter if the
  table also carries lost bids), or is the table wins-only by
  construction?
- Which key links an impression row to its attributed conversions? The
  attribution tables carry an `impression_id`; the delivery-log side
  describes `auction_id` and `request_id`. Which should we join on, and
  is it present and populated on both sides?

*Why we ask: the filter defines which rows get training labels; the
join is what the whole label build stands on.*

## 4. Which conversion events count for each goal

The conversion tables carry an `event_name` field. Which `event_name`
values should count as a purchase, and which as a page view, when we
build training labels for the PIXEL_PURCHASE and PIXEL_PAGE_VIEW goals?
Is the mapping fixed and documented, or advertiser-dependent (the same
pixel firing differently named events per advertiser)?

*Why we ask: the label build filters conversions by `event_name`;
without the mapping we cannot connect a goal to its rows.*

## 5. Click-through versus view-through attribution

When a conversion is attributed, is it recorded anywhere whether the
attribution was click-through or view-through? If yes, can that
information be included in the conversion data we consume? This matters
because the two carry very different signal strength — knowing the
method lets us choose and inspect what the training label means,
instead of learning from an unknown blend. If it isn't recorded, we'll
treat all conversions simply as "attributed" without distinguishing the
method.

## 6. Candidates per bid request

How many candidate ad sets does a bid request carry? We need the
distribution, not just the average — median, average, p99, and the
practical maximum. If volume figures are also available (expected and
peak requests per second reaching the bidder), those help too, but the
candidates-per-request distribution is the critical piece.

*Why we ask: serving cost and latency scale linearly with candidates
per request; it is the single multiplier behind compute sizing.*

## 7. Privacy constraints on the data we'll handle

The datasets we'll consume include user-level identifiers (device ids,
IFA/IDFA, household id, user ids, emails) and consent signals (GDPR, US
privacy, do-not-track). What are the rules we must follow on our side?

- May we store these fields in our own tables if we hash them
  (deterministic, salted), or must some be dropped entirely?
- Do any consent signals restrict which impressions can be used for
  training at all?
- May sampled real data be used in the development environment, or
  must dev run on synthetic data only?

*Why we ask: this gates our storage rules, whether consent filters the
training data, and what the development environment may contain —
expensive to redo if guessed wrong.*

## 8. Identity fields in the data we receive

Will every dataset we consume carry the three identifier spaces — the
client UUID, the DSP id, and the raw-log id — as separate,
filled fields for each entity (ad set, campaign, creative, account)?
If not, which mapping is available to us to translate between them,
and where does it live?

*Why we ask: every join we do crosses these id spaces; if the mapping
is on us, that is new scope for the data lane.*

## 9. Update cadence of the shared data

The client has proposed cadence expectations per data type — hourly for
delivery metrics (impressions, clicks, spend), daily for attributed
conversions and training data. Can you confirm these as the committed
cadences for what the bidder account will actually receive, per
dataset? And where a faster feed is technically possible
(near-real-time delivery data, for example), is providing it an
option?

*Why we ask: the shared data's freshness is a hard floor under
everything we compute from it, from training recency to the online
features.*
