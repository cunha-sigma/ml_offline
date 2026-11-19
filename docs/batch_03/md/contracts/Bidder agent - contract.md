# Custom bidding agent: scope, line-settings contract and answers

## Overview

This document proposes Sigma's preferred scope and data contract with the client for the first stage. The goal is to agree on the inputs and responsibilities so Sigma can build the first version of the bidding agent.

The client is requested to confirm which parts it can provide and suggest changes where needed. Section 3 answers the questions in the client's export documents. Section 4 outlines proposed extensions for later stages.

If the client considers any additional capabilities mandatory for the first stage, Sigma will include them. The scope, data contract, and implementation plan will be updated to account for the additional work.

## 1. Proposed scope for the first stage

**First-stage principle.** The Bidder agent works at one level, the client's ad set (an ad-server line item), with the smallest set of inputs that allows it price and pace.

For the first version, Sigma proposes that the client publishes one prepared settings record per ad set, as defined in section 2. This includes:

- A status that accounts for the ad set, organization, account and campaign, including locks and archive state.

- The applicable currency and time zone.

- The bid after the agreed fee adjustment.

- The bidding strategy and pacing mode mapped to the agreed values, plus the optimization goal and attribution window.

The ad server applies targeting and budget limits. The agent relies on these controls and the prepared settings from the client.

The proposed division of responsibilities is based on the assumption that the client may already have some of these values available or can prepare them with minimal additional effort. This keeps the feed limited to ad-set records and allows Sigma to focus on pricing and pacing.

The final division of responsibilities will be agreed with the client based on the available data and existing logic. Any changes will be reflected in the scope, implementation plan, and data contract.

The ad server's bidder sends the agent an auction with the client's line items that are eligible for it. For each one the agent returns a price, or no bid, within 10 ms.

The price is

bid = pacing factor × value × probability\
pacing factor = a number between 0 and 1 that lowers the price when the line is spending faster than planned\
value = target CPA for conversion lines, max CPM ÷ 1000 for awareness lines\
probability = chance that this impression leads to an attributed conversion (1 for awareness)

**In the first stage, the agent is responsible for**

- Pricing each candidate line item independently, in the line's currency. Before pacing, the price is max CPM ÷ 1000 for awareness lines or target CPA × probability for conversion lines. Pacing can lower this price or leave it unchanged. The pacing factor never exceeds 1.

- Pacing: the agent adjusts each line item's bids to spread its daily budget across the day. Each line has its own pacing factor between 0 and 1. The agent multiplies the price by this factor. The factor decreases when spending is faster than planned and increases when spending is slower. The client supplies the spending data through the win-log stream.

- Honouring the line item's status from the client: a paused line gets no bid, even if the ad server's bidder still sends it. This is the one eligibility input the agent reads, and it is the client's explicit decision, not something the agent derives.

- Predicting the conversion probability from a model trained on the client's impression and conversion data.

- Recording every decision so a bid can be explained and reproduced.

**In the first stage, the agent is not responsible for**

- Deciding which line items take part in an auction. The ad server decides that, using the targeting, flight dates, frequency caps, budgets and statuses that the client has synced to it. The agent prices every line the ad server's bidder sends. It checks only two things first: the line's status in the client's feed is ACTIVE, and the line's currency matches the auction's. Everything else about eligibility it takes as already decided.

- Stopping a line when a budget cap is hit. The ad server continues to stop a line at its daily budget and at campaign caps.

- Combining statuses or settings across organization, ad account, campaign and ad set. The agent sees ad sets only. If a campaign is paused, the client marks its ad sets paused in the feed.

- Attributing conversions or calculating fees. The client attributes conversions and deducts fees before the data reaches the agent.

## 2. Data contract for the first stage

Sigma proposes that the client provide a complete list of ad sets, with each record containing the current values for the fields listed below. This will allow the agent to update its local list without having to track individual changes.

**Data Provided by the client**

- The complete list at one fixed location: an S3 object, an HTTP endpoint, or another API to agree.

- One complete record per ad set, as newline-delimited JSON.

- The time the complete list was generated.

The client decides how and how often to refresh this list. No change notifications or per-change records are needed.

**How the agent reads updates**

The agent fetches the complete list at a configurable interval. An interval of 5 minutes is only a suggestion; we can change it as required.

After the client publishes changed settings, the agent reads them at the next poll. Until then, it continues using the previous settings. This applies to status changes as well as other settings.

After each fetch, the agent replaces its local copy of the ad-set settings. It stops bidding for any ad set missing from the new list.

| Field | Type | Meaning | Required |
|----|----|----|----|
| beeswax_line_item_id | string of digits | Ad-server line item ID. Must equal the line item ID the ad server's bidder sends in the auction request. Our key | yes |
| ua_adset_id | UUID string | The client's own ID, for joining to conversion data | yes |
| updated_at | ISO 8601 UTC | When this ad-set record last changed, for troubleshooting. The agent uses the time the complete list was generated to check whether the published data is out of date | no |
| status | ACTIVE or PAUSED | Effective status after the client has applied organization, account and campaign statuses, locks and archive state. PAUSED means no bid | yes |
| bidding_strategy | MAX_CPM or GOAL_CPA | Chooses the formula | yes |
| bid | number \> 0 | MAX_CPM: maximum CPM per 1,000 impressions. GOAL_CPA: target cost per conversion. In currency. In both cases the value is already net of the client's fees: the client applies to the target CPA the same deduction it applies to max CPM today, so the agent never handles fees. Exact per-impression fee treatment for CPA lines is a later refinement | yes |
| currency | ISO 4217 code | Currency of bid and daily_budget. Must equal the candidate currency in the auction request; on a mismatch the agent does not bid | yes |
| optimization_goal | IMPRESSIONS, PIXEL_PAGE_VIEW or PIXEL_PURCHASE | What counts as a conversion. IMPRESSIONS only with MAX_CPM | yes |
| attribution_window_days | integer | Window used to attribute conversions for this goal. One static value for all advertisers in the first version; 14 proposed, see section 3 | for GOAL_CPA |
| daily_budget | number \> 0 | Budget per day in currency, spend including vendor fees, the same basis as the win-log cost | yes |
| pacing | EVEN or NONE | The client's pacing type. EVEN: the agent paces. NONE: our proposal is that the pacing factor is fixed at 1, so the price is value × probability with no pacing discount. The client maps its internal settings (even, none, catch-up overrides) onto these two | yes |
| timezone | IANA zone, e.g. America/New_York | The budget day is the calendar day in this zone; day_part hours are read in it. Including it on the ad set lets the agent read ad-set records only | yes |
| start_at_utc, end_at_utc | ISO 8601 UTC or null | Start and end times. The agent uses them only for pacing, to shorten the active hours on the first and last day. The ad server enforces these dates when selecting lines for an auction | start yes, end may be null |
| day_part | object or null | Allowed hours for each weekday, using the client's existing format. For example, start: 9 and end: 17 mean from 09:00 until 17:00; 17:00 is outside the scheduled hours. If day_part is null or {"day_parting": null}, this setting does not restrict days or hours. See the example and time-zone explanation below | may be null |

Rules for missing values: if a required field is null or absent, the ad set is treated as not biddable until a complete record arrives. Fields not listed above are ignored if present.

**Day-parting format and time zone**

A populated day_part uses the client's existing structure:

{\
"day_parting": {\
"timezone": "ad_account",\
"details": \[\
{"day": "mon", "start": 9, "end": 17}\
\]\
}\
}

For the first stage, we propose counting active hours in the ad set's timezone. If The ad server evaluates day-parting in the viewer's time zone, a 12-hour window can span about 15 hours across time zones. Please review with us how this simplification affects even delivery.

Example ad-set record:

{"beeswax_line_item_id":"28392","ua_adset_id":"618c441c-8c04-4f24-8c5f-6ddaac967457",\
"updated_at":"2026-10-27T14:02:11Z","status":"ACTIVE",\
"bidding_strategy":"GOAL_CPA","bid":25.0,"currency":"USD",\
"optimization_goal":"PIXEL_PURCHASE","attribution_window_days":14,\
"daily_budget":111,"pacing":"EVEN","timezone":"America/New_York",\
"start_at_utc":"2026-09-25T18:50:19+00:00","end_at_utc":null,\
"day_part":{"day_parting":null}}

**Open Question for the client:** How are bid and daily_budget values stored, and what decimal precision is used for each?

Not part of this feed: lifetime budgets, campaign, account and organization budgets and statuses, targeting, placements, app lists, frequency caps, ads and creatives, and the raw upstream-DSP bidding object. Spend comes from the win-log stream, not from this feed.

**Required Fields for Each Win-Log Event**

The proposed approach is for the client to store the win-log data in S3, from where Sigma would ingest it.

The names below are ours. We will match them to the client's stream schema. The table explains which fields we need per won impression and why. Other fields can stay as they are:

| Field | Meaning |
|----|----|
| Ad-server line item ID | Same value as beeswax_line_item_id above |
| Impression time | When the impression was recorded, UTC. Include bid time if available to help measure reporting delays |
| All-in cost | The amount actually charged: media plus targeting and other fees, in USD |
| Rate from USD to the line's currency | So the USD cost can be compared with daily_budget. How the client derives it from its account settings is the client's concern |
| Event ID | One unique value per charged impression, so a replayed or duplicated event is counted once |
| Auction ID | The auction identifier The ad server sent to the agent in the bid request, or a defined mapping to it, so the won impression can be matched with the decision that produced it. Not needed for pacing; needed to reconstruct decisions and to build training labels |

Useful but not required: the bid-shading reduction, if The ad server shades agent prices, for comparing the price we returned with the price that won.

Two more things pacing needs around the stream:

- A heartbeat to show that the stream is still running. Without it, we cannot tell whether the stream has stopped or there are simply no events for a line.

- A total of the money spent so far for each line, for recovery. Include a cutoff showing which stream events are already counted in the total. Use a stream position or the time an event entered the stream as the cutoff.

  Do not use the impression time as the cutoff. Events can arrive late: an impression at 11:58 may enter the stream at 12:05. An impression-time cutoff could cause the agent to miss that spend or count it twice.

  The agent starts with the supplied total, then adds every event after the cutoff and no earlier events.

## 3. Answers to the questions in the client's export documents

The answers below apply to the proposed first-stage contract in section 2. If the client changes the field set or the delivery, some answers change with it.

**Should we track remaining spend capacity at the organization level and share it?**

No. Organization limits are enforced by the client and the ad server; the agent does not use them.

**Should the bidding strategy be included at both the campaign and ad set levels?**

Ad set only. The agent never reads campaign records.

**Preferred format for targeting configurations?**

None. The ad server applies targeting before the agent is called, so the agent does not evaluate targeting. The one targeting-like field kept, day_part, serves pacing: it tells how many hours remain today, not whether to bid.

**Are additional delivery-state metrics required for real-time pacing?**

Not in this feed. Spend comes from the win-log stream. One thing we need separately: today's spend to date per line item at the moment the agent starts or recovers from a gap, so pacing does not begin from zero. An hourly dump plus a final daily dump would do.

**Should the client send organization and ad-account statuses for the bidder to resolve, or resolve the hierarchy first?**

Resolve first. Send one effective status per ad set.

**How does the bidder use objective_type on the campaign?**

It does not. The ad set's bidding_strategy and optimization_goal are sufficient.

**Normalized bidding_strategy and pacing fields?**

As in the table above: MAX_CPM / GOAL_CPA, and EVEN / NONE.

**optimization_goal and attribution_window_days?**

As in the table. We propose one static window of 14 days for all advertisers in the first version. Please confirm this value and put it in every GOAL_CPA record.

**Bidder-facing targeting fields and targeting sharing format?**

Not needed.

**Handling of null, empty and default values?**

Required fields must be non-null; otherwise the ad set is not biddable. The campaign lifetime default of 999999999 does not reach us, since campaign records are not in the feed.

**Final field set?**

The fifteen fields in the table. Nothing else from the current export is needed.

One more point to confirm:

- **Maximum price for conversion lines.** For GOAL_CPA the price is pacing factor × target CPA × probability. Its only bound is the target CPA itself, which as a per-impression price is far above any sensible CPM: a \$25 target allows a \$25,000 CPM if the probability is overestimated. The ad server's own CPA strategy carries a max_bid for this reason. Does the client set a maximum bid on CPA lines in The ad server? If so, it reaches the agent in every auction request and no feed field is needed. If not, the agent applies a cap of its own.

## 4. Proposed extensions for later stages

These capabilities are not included in the first-stage scope and data contract proposed above.

- **Enforce campaign and ad-set budget caps.** Track daily and lifetime spending and stop bidding when reported spend reaches a cap. Campaign checks cover the combined spend of its ad sets.

- **Calculate ad-set status from the full hierarchy.** Apply organization, account and campaign statuses in the agent, so the client can publish each entity's own status.

- **Support different attribution windows.** Use the window selected for an ad set, such as 7 or 14 days, with training data and predictions that match that window.

- **Use auction patterns to plan spending.** Allocate more of the daily budget to hours with more eligible auctions or a higher predicted chance of conversion.

- **Control both bid prices and auction participation.** Our pacing service will calculate lambda (λ) to adjust prices and alpha (α) to control the chance of bidding for each eligible ad set. For example, alpha of 0.5 means bidding in roughly half of its eligible auctions. We will reduce participation when price reductions alone do not slow spending enough, especially for small budgets.

- **Check additional targeting rules.** Reject candidates that do not match agreed rules, such as geography or app lists, before returning a bid.

These extensions need additional design and testing. Some also require more data from the client, such as campaign records, targeting rules, auction history or training data for different attribution windows. For ad sets where our service manages alpha, we will agree with the client how the ad server's participation control should be configured.

We will describe the capabilities left for later stages in separate documents, including any changes to the data contract.
