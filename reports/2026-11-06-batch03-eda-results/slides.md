---
theme: default
title: "Client Data Samples: What We Learned"
author: Rodrigo Cunha
transition: slide-left
paginate: true
---

<!--
FORMAT: one slide per `---`. Bullets/bold = ON-SCREEN content (low text).
HTML comments (like this one) = SPEAKER NOTES (Slidev presenter notes),
invisible to the audience. English. Slides are visual cues — the talk
carries the content. No client/vendor names, no file paths on-screen —
those stay in these notes for Q&A backup.
-->

# UA Data Samples
## What we learned so far

**Rodrigo Cunha** — Principal ML Engineer<br>
Custom Bidding Agent · ML Lane · 2026-11

<!--
- ~1 min. First real client data landed (batch-03); we ran a full EDA.
- Everything shown here comes from eda/notebooks/01_eda_dossier.ipynb —
  the notebook is the deep-dive reference, this is the summary.
- EDA environment: eda/ folder, docker compose up, loaders ready.
-->

---

## What we received

<div class="h-18"></div>

<div class="grid grid-cols-3 gap-6">

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Joined stream sample</div>
  <div class="text-4xl font-bold text-blue-500 mt-2">933</div>
  <div class="text-sm opacity-70">won impressions</div>
  <div class="text-sm mt-4">request · candidates ·<br>impression · video events</div>
  <div class="text-sm font-semibold border-t border-gray-400 mt-4 pt-2">→ the full auction lifecycle,<br>minus attribution</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Delivery-control export</div>
  <div class="text-4xl font-bold text-blue-500 mt-2">130</div>
  <div class="text-sm opacity-70">entities</div>
  <div class="text-sm mt-4">org → account → campaign →<br>ad set → ad</div>
  <div class="text-sm font-semibold border-t border-gray-400 mt-4 pt-2">→ config reality</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Traffic & workload CSVs</div>
  <div class="text-4xl font-bold text-blue-500 mt-2">29 days</div>
  <div class="text-sm opacity-70">full volume, Oct 1–29</div>
  <div class="text-sm mt-4">auctions · bids · wins ·<br>delays · active lines</div>
  <div class="text-sm font-semibold border-t border-gray-400 mt-4 pt-2">→ volumes & timing</div>
</div>

</div>

<!--
- Three sources, three different questions they answer.
- Stream sample: the upstream DSP's joined log, anonymized by the client.
- Export: the client's campaign-management config, matched to the sample.
- CSVs: client-measured, the only volume/timing ground truth.
- Sources on disk: docs/batch_03/ (+ md/ conversions); loaders in eda/.
-->

---

## What the sample cannot answer

<div class="h-18"></div>

<div class="flex justify-center">

```mermaid {scale: 1.0}
flowchart TB
  L1["no attribution data"] --> C1["no label work yet"]
  L2["user / geo / device ids<br/>anonymized"] --> C2["their signal unknown<br/>until real data"]
  L3["wins only"] --> C3["no losing-auction side"]
  L4["timestamps randomized"] --> C4["no ordering, no delays<br/>(CSVs cover timing)"]
```

</div>

<!--
- Say it before anyone asks: these are the sample's hard limits.
- Anonymization kept joins consistent inside an event but destroyed
  values: all-unique random tokens; timestamps uniform 2002-2286.
- Labels: attribution tables exist client-side, pending data access.
- So: no CVR, no class balance, no user features from this sample.
-->

---

## The data connects end to end


<div class="h-26"></div>

<div class="flex justify-center">

```mermaid {scale: 0.75}
flowchart LR
  RQ["bid request"] --> CA["candidates 1–15"]
  RQ --> WI["won impression"]
  CA -. "winner always listed<br/>933/933" .-> WI
  WI --> AC["video events 0–n"]
  WI -. "DSP-id bridge" .-> CFG["config hierarchy<br/>0 orphans"]
  WI -. "attribution<br/>NOT in the samples" .-> AT["conversions"]
```
</div>

**Keys clean** · zero duplicates · every frame joins

<!--
- All join checks passed: auction key + request id unique; activity
  joins 100%; winner among candidates in all 933 events.
- Bridge: DSP integer ids <-> client UUIDs works both ways; export
  covers 45% of impression rows (matched high-volume subset).
- The dashed attribution edge is the future label join — the only
  missing piece, waits on data access.
-->

---

## Feature availability

<div class="h-18"></div>

<div class="grid grid-cols-3 gap-6 mt-4">

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold text-green-500">Usable now</div>
  <div class="text-sm mt-3">app / content identity</div>
  <div class="text-sm">content metadata — genre · rating · length</div>
  <div class="text-sm">video specs</div>
  <div class="text-sm">auction context — deals · floor · seller</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold text-amber-500">Present, signal unknown</div>
  <div class="text-sm mt-3">device · geo · user</div>
  <div class="text-sm opacity-70 mt-2">anonymized in the sample —<br>judged only on real data</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold text-gray-500">Excluded</div>
  <div class="text-sm mt-3">~25 constant fields</div>
  <div class="text-sm opacity-70 mt-2">same value everywhere —<br>no signal to learn from</div>
</div>

<div class="border border-gray-400 rounded-lg p-4 col-span-3 flex items-center justify-between">
  <div class="text-sm"><b>Ad-set config</b> — targeting breadth · frequency caps · budgets</div>
  <div class="text-sm font-semibold">→ day-one features for brand-new ad sets</div>
</div>

</div>

<!--
- ~65 bid-time fields at full coverage; the usable core is the
  app/content/video/auction side.
- Device/geo/user: available at bid time, value judged only on real data.
- Config-derived features = cold-start answer for the sparse-signal
  requirement; derived offline, served via feature tables + Redis —
  no new serving mechanics.
- Deliberate pending decision: bid/target-CPA as feature (feedback loop).
-->

---

## Inside a bid request

<div class="h-11"></div>

<div class="flex justify-center">

```mermaid {scale: 1.0}
flowchart LR
  subgraph REQ["one request"]
    CTX["context<br/>app · device · geo<br/><i>same for all candidates</i>"] ~~~ C1["candidate A<br/>line item · creatives · bid"] ~~~ C2["candidate B<br/>line item · creatives · bid"]
  end
  C1 & C2 --> PICK["ad server<br/>picks"]
```

</div>

<div class="h-4"></div>

Scores are separated by **candidate-side** information: the candidate's identity plus everything we attach to it — **precomputed per-ad-set features** (rolling metrics, config) — the shared request context raises or lowers all candidates together, never reorders them

**The ad server picks the winner** — top bid wins only **42%**: bid influences, does not decide

<!--
- Within a request only candidate identity + bid vary (100% / 91%);
  request fields are context — confirms advertisers-as-features.
- Winners bid higher (median 7.41 vs 6.41 USD CPM) but rank-1 bid wins
  only 42.5%; winners seen down to bid rank 13.
- Implication: raising our bid buys probability, not certainty; a
  win-rate model must condition on more than price.
-->

---

## Traffic reality: scale

<div class="h-8"></div>

| per second | average | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| **auctions** | 444 K | 440 K | 564 K | 693 K | **1.92 M** |
| **bids** | 21 K | 4.3 K | 66 K | 142 K | 373 K |

<div class="h-6"></div>

Oct 1–29 totals: **1.11 T** auctions → **52.6 B** bids (4.75%) → **465 M** wins (0.88%) → **USD 4.63 M** spend

<!--
- Client-measured, full population, Oct 1-29.
- Peak is ~4.3x the average — whatever we size must survive 1.92 M/s.
- Bids are ~20x fewer and far spikier (p25 is 811/s!) — that's pacing,
  next slide shows it.
-->

---

## Traffic reality: bids follow budgets, not viewers

<div class="h-8"></div>

<img src="/images/hourly_profile.png" class="mx-auto h-80" />

<div class="h-6"></div>

**The 444 K/s is the request stream the Bidder Agent inherits** — the **ad server's pacing filters the candidates** before the request (auctions losing all candidates are never sent); the low bid count follows from that

<!--
- Auctions peak 0-5 UTC = US prime time (viewers).
- Bids peak 15-20 UTC = middle of the budget day (resets at US-local
  midnight, right after prime time): budgets fresh in the US morning,
  spent by prime time -> upstream pacing throttles exactly at the peak.
- Corroboration: per-interval bid rate swings 0.09%-34%; sample ad sets
  carry business-hours dayparting.
- When our λ-pacing replaces the upstream α, this bid curve will change.
-->

---

## Traffic reality: candidates per request

<div class="h-6"></div>

<div class="flex justify-center">

```mermaid {scale: 0.72}
xychart-beta
    title "requests by candidate count (sample, n=933)"
    x-axis [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    y-axis "requests" 0 --> 450
    bar [437, 44, 32, 35, 27, 35, 74, 31, 38, 32, 12, 31, 15, 14, 76]
```

</div>

**47% carry exactly 1** · median 2 · spike at **15 — looks like a cap**, true max pending from the vendor

<!--
- Bimodal: half the requests are single-candidate; a quarter carry 8+.
- The 76 requests at exactly 15 are NOT a tail — a spike at the edge,
  consistent with the DSP truncating candidate lists at 15. If so, the
  real maximum is unknown — exactly the number still pending from the
  ad-server vendor.
- Client-measured averages (full population): 1.3 with the upstream
  pacing filter, 13.9 without — the sample sits between (mean 4.9).
-->

---

## Traffic reality: the scoring stream

<div class="h-10"></div>

<div class="grid grid-cols-2 gap-6 mt-10">

<div class="border border-gray-400 rounded-lg p-4 text-center">
  <div class="text-sm">with the upstream pacing filter<br>(1.3 candidates/auction)</div>
  <div class="text-4xl font-bold text-blue-500 mt-3">0.6 M/s</div>
  <div class="text-sm opacity-70 mt-1">candidates to score, average</div>
</div>

<div class="border border-gray-400 rounded-lg p-4 text-center">
  <div class="text-sm">without it<br>(13.9 candidates/auction)</div>
  <div class="text-4xl font-bold text-amber-500 mt-3">6 M/s</div>
  <div class="text-sm opacity-70 mt-1">candidates to score, average</div>
</div>

</div>

<div class="h-6"></div>

A **10×** swing decided upstream — and the roadmap moves pacing to our side

<!--
- Exact averages from client two-week totals (candidates before/after
  the upstream probabilistic-pacing elimination, divided by the period).
- Not a forecast of ML load: awareness lines skip the model today.
  It bounds the candidate stream, not the model calls.
- Peaks run ~4x the average on top of this.
-->

---

## Traffic reality: how fresh is spend/win data

<div class="h-10"></div>

<img src="/images/delay_cdf.png" class="mx-auto h-85" />

Spend-based signals see **complete** data only **~1–1.5 h** after the fact

<!--
- Delay from bid to impression event in the win log; client's own
  histogram (their prose said "90% in 15 min" — actual: 81%; p90=24 min).
- p50 2.3 min / p90 24 min / p99 78 min.
- Floors pacing inputs, rollout spend guardrails, early readouts;
  irrelevant for daily label builds.
-->

---

## Traffic reality: summary

<div class="h-8"></div>

- **444 K auctions/s** average · **1.92 M/s** peak
- **Half the requests carry a single candidate**; spike at 15 looks like a cap — true max pending
- Candidate stream, **average**: **0.6 M/s** with the upstream pacing filter, **6 M/s** without it — a **10×** swing; peaks run ~4× the average
- Bids follow **budgets**, not viewers — the **ad server's pacing filters candidates** upstream; the bid volume follows from that
- Win-log freshness floor: **p50 2.3 min · p90 24 min**

<!--
- One breath: huge scale, a 10x swing we don't control, a bid curve
  shaped by pacing, and spend data that is always ~an hour behind.
-->

---

## Economics: price levels

<div class="h-8"></div>

<div class="flex justify-center">

```mermaid {scale: 0.8}
flowchart LR
  B["the bidder's price"] -->|"bid shading<br/>−18% median"| SUB["submitted bid<br/>median USD 7.41"]
  SUB -->|"auction won,<br/>vendor fees added<br/>+8% median"| CH["charged price<br/>median USD 8.10"]
```

</div>

<div class="h-8"></div>

| USD CPM, per impression | median | mean | min | max |
|---|---|---|---|---|
| **submitted bid** (post-shading) | 7.41 | 8.54 | 5.00 | 50 |
| **charged price** | 8.10 | 8.98 | 5.42 | 50 |

<div class="h-6"></div>

Agrees with the 29-day whole-period CPM of **USD 9.95** — the sample's economics are not exotic

<!--
- Sample: 933 won impressions, 14 ad sets. Single-digit CPM market.
- "Submitted bid" = what went to the exchange, already shaded.
- Cross-check vs the traffic profile totals: USD 4.63M / 465M wins.
-->

---

## Economics: the charge includes fees

<div class="h-6"></div>

<img src="/images/win_over_bid.png" class="mx-auto h-85" />

Charged > bid on **2 of 3** impressions (median **+8%**) — and **budgets are consumed by this charged, fee-inclusive amount**, not by the bid · to confirm with the client

<!--
- Spike at 1.0 = charged exactly the bid (294 impressions); below 1.0
  is rare (14).
- All-in cost matches the win-log contract wording ("media plus
  targeting and other fees") AND budget_type "spend including vendor
  fees" — one coherent gross basis, so spend reconciliation needs no
  fee math.
-->

---

## Economics: shading and who sets the price

<div class="grid grid-cols-2 gap-6 mt-10">

<div class="border border-gray-400 rounded-lg p-4 text-center">
  <div class="text-sm">bid shading, median cut</div>
  <div class="text-4xl font-bold text-blue-500 mt-3">−18%</div>
  <div class="text-sm opacity-70 mt-1">USD 1.60 CPM, on ~70% of impressions —<br>our agent's prices may be shaded too</div>
</div>

<div class="border border-gray-400 rounded-lg p-4 text-center">
  <div class="text-sm">charged price vs best losing bid</div>
  <div class="text-4xl font-bold text-blue-500 mt-3">1.01×</div>
  <div class="text-sm opacity-70 mt-1">the winner pays its best competitor's<br>price — a shaded first-price market</div>
</div>

</div>

<!--
- Shading cut reported per impression by the stream; permission flag on
  for 12/14 sample ad sets.
- Win/best-loser median 1.01 (p90 1.21), on the 496 requests that had
  losing candidates — clears at the second-highest bid.
- The bid we compute is not the price that competes — one more reason
  the win-rate research models P(win | price, context) separately.
-->

---

## Economics: why a max-bid cap

<div class="h-10"></div>

<div class="flex justify-center">

```mermaid {scale: 0.9}
flowchart LR
  A["target CPA<br/>USD 25"] --> X["× P(action)"]
  X -->|"P well calibrated, ≈0.0004"| OK["bid ≈ USD 10 CPM<br/>inside today's market"]
  X -->|"P overestimated, ≈1"| BAD["bid = USD 25,000 CPM<br/>2,000× the market"]
```

</div>

<div class="h-4"></div>

Today's market: **USD 5–15 CPM** — a cap is cheap insurance against a miscalibrated model

<!--
- The contract asks who caps CPA bids: if the ad server has no max_bid
  on CPA lines, the agent applies its own.
- Today's price levels give the cap its natural scale.
- This is the bid-decision lane's knob; our lane's contribution is
  calibration — the cap is the backstop, not the fix.
-->

---

## Economics: summary

<div class="h-8"></div>

- Market lives at **USD 5–15 CPM** (charged median **8.10**)
- Charge **includes vendor fees** — one gross basis everywhere
- Bid shading cuts **~18%** median · winner pays its **best competitor's price**
- Overestimated P(action): USD 25 target → **USD 25,000 CPM** — the **max-bid cap** case

<!--
- One breath: cheap inventory, fees baked into every money number,
  shading between our bid and the paid price, and a cap as insurance.
-->

---

## What flows onward

<div class="grid grid-cols-2 gap-6 mt-8">

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Client follow-ups</div>
  <div class="text-sm mt-3">budget consumption: always the charged price + fees, or do other consumption types exist?</div>
  <div class="text-sm mt-2">a sample of attribution / conversion data, if possible</div>
</div>

<div class="border border-gray-400 rounded-lg p-4">
  <div class="font-bold">Design inputs</div>
  <div class="text-sm mt-3">feature list → model design</div>
  <div class="text-sm mt-2">traffic numbers → serving capacity</div>
  <div class="text-sm mt-2">price levels → max-bid-cap scale</div>
</div>

<div class="border border-gray-400 rounded-lg p-4 col-span-2 flex items-center justify-between">
  <div class="text-sm"><b>EDA environment ready</b> — dockerized notebook · data loaders · the dossier</div>
  <div class="text-sm font-semibold">→ anyone can open it and explore the data</div>
</div>

</div>

<!--
- Follow-ups go through the client-questions channel.
- Timestamps: order-preserving exports are off the table before we are
  inside the client's infra (data protection) — timing analysis waits
  for access, not for a better sample.
- Feature list feeds the features design; capacity numbers feed serving
  sizing; the cap case feeds the contract discussion.
- ENV: eda/ folder — docker compose up, two notebooks: 00 = data
  context (read first), 01 = the dossier. Matheus: this is the data
  ramp-up path after the design docs.
-->
