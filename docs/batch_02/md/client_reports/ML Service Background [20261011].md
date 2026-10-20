# ML Service Background \[20261011\]

## Last Updated: 2026-10-11@ 10:00 PM PT

# Background

Advertisers should be able to allocate their budgets toward their goal objective, and we should be able to evaluate each potential bid opportunity based on the likelihood of it resulting in the advertiser’s goal objective. As we build our custom bidding agent, the ML Service will provide the expected-value component needed to make that outcome-based bid evaluation.

At bid time, the bidder will consult the Pacing Service for the ad set's pacing multiplier, **λ**, and the ML Service for the predicted expected value to construct the bid. The two components answer different questions: **how valuable is this impression opportunity for the advertiser (expected value)** and **how aggressively should the ad set bid given** **its spend level relative to budget (pacing)?** Together they form a final bid of:

*Final Bid = pacing λ × Expected Value*

where expected value is a function of the advertiser’s maximum goal cost per action and the likelihood that, should an impression be shown, it will drive an attributed goal action\>

*Expected Value = Max CPA Bid ×* *P(Goal Action \| Impression)*

The ML Service must therefore support two related responsibilities: selecting the appropriate outcome model and providing the expected-value input required by the selected bidding strategy. This document establishes the background and initial requirements; model architecture and detailed service interfaces remain to be defined.

In addition to the existing **max_bid f**ield, the ML service will need to consult two fields that do not yet exist in the ad set data model:

- **bidding_strategy** defines how the advertiser expects bid price and budget delivery to be prioritized. Proposed values include **max_cpm**, **goal_cpa**, and **lowest_cost,** (with “lowest_cost” synonymous with “auto bid”)

- **optimization_goa**l identifies the action the advertiser wants to drive and therefore the prediction model to use. Eventually we would include support for **impressions**, **PIXEL_PAGE_VIEW, PIXEL_PURCHASE,** and **app_installs.**

Together, these fields determine which model should be consulted and how the **max_bid** field should be interpreted when formulating the final bid. For example, a **goal_cpa** ad set with a PIXEL_PAGE_VIEW requires a page-view prediction model, while a PIXEL_PURCHASE goal requires a purchase prediction, and IMPRESSION goal requires no model.

For conversion goals, the service should estimate **P(Goal Action \| Impression**) for each eligible ad set using the available auction/request attributes and relevant ad set context. For an ad set with an IMPRESSIONS optimization goal, P(Impression \| Impression) is 1; no conversion prediction model is required.

The ML Service must therefore support two related responsibilities: selecting the appropriate outcome model and providing the expected-value input required by the selected bidding strategy. This document establishes the background and initial requirements; model architecture and detailed service interfaces remain to be defined.

# Bidding Strategies

Today, all ad sets effectively use a **max_cpm** bidding strategy with an ***Impressions o***ptimization goal. Supporting goal-based bidding and lowest-cost bidding will require us to make the advertiser's bidding intent explicit and estimate the probability that each eligible impression produces the desired outcome. The below table expresses the advertiser intent behind each bidding strategy and its relation to expected value formulation:

<table style="width:91%;">
<colgroup>
<col style="width: 16%" />
<col style="width: 22%" />
<col style="width: 25%" />
<col style="width: 26%" />
</colgroup>
<thead>
<tr>
<th><strong>Bidding Strategy:</strong></th>
<th><strong>max_cpm</strong></th>
<th><strong>goal_cpa</strong></th>
<th><strong>lowest_cost</strong><br />
<strong>(auto bid)</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Advertiser intent</strong></td>
<td>Bid up to $X CPM for eligible impressions.</td>
<td>Bid assuming each desired action is worth up to $X CPA.</td>
<td>Spend my budget in full, when achievable, at the lowest possible cost per desired action.</td>
</tr>
<tr>
<td><strong>Value used</strong></td>
<td>Advertiser-set maximum CPM.</td>
<td>Advertiser-set maximum CPA for the selected optimization goal.</td>
<td>High internal CPA value; no advertiser-set CPA limit.</td>
</tr>
<tr>
<td><strong>Model use</strong></td>
<td>No conversion model. The effective goal is impressions, with P(Impression | Impression) = 1.</td>
<td>Uses P(Action) from the model selected by optimization_goal.</td>
<td>Uses the same goal-specific probability model as goal_cpa.</td>
</tr>
<tr>
<td><strong>Price vs. budget priority</strong></td>
<td>Seek budget delivery without bidding above the maximum CPM.</td>
<td>Seek budget delivery within the advertiser's expected-value bid limit; delivery may be constrained by the CPA goal.</td>
<td>Prioritize full budget delivery, when achievable; pacing λ adjusts bids toward the lowest eCPA needed to spend the budget.</td>
</tr>
<tr>
<td><strong>Expected value per impression</strong></td>
<td>max_bid / 1,000</td>
<td>max_bid × P(Action)</td>
<td>Internal CPA Value × P(Action)</td>
</tr>
</tbody>
</table>

*P(Action) refers to* *P(Goal Action \| Impression). For all three strategies, Final Bid = λ × Expected Value. A goal_cpa is not a guarantee of observed CPA in every reporting period.*

# Role of Optimization Goal

Optimization goal is utilized to identify the action that the advertiser wants to drive and which action we should predict in bid formulation.

For conversion goals, the service should estimate P(Goal Action \| Impression) for each eligible ad set using the available auction/request attributes and relevant ad set context. For an ad set with an IMPRESSIONS goal, P(Impression \| Impression) is 1 -- so no conversion model would be required.

Together, these fields determine whether model inference is needed, which model should be consulted, and how max_bid should be interpreted. For example, a goal_cpa ad set with a PIXEL_PAGE_VIEW goal requires a page-view prediction, while a PIXEL_PURCHASE goal requires a purchase prediction.

In addition to optimization goal, we may allow advertisers to select a goal attribution window (e.g., an advertiser wants to drive PIXEL*PURCHASE events* at a \$20 CPA but only if the purchase event occurs within 7 days of the impression event). This may live at the optimization goal level *(e.g., optimization*\_*goal = “PIXEL_PURCHASE_7_day” vs. PIXEL_PURCHASE_14_day or PIXEL_PURCHASE_1_day)* or as its own ad set specific column.

# Formulating Expected Value

### Max CPM (max_cpm)

*Advertiser intent: "Bid up to \$X CPM in any eligible auction."*

This represents the current bidding approach. max_bid is a CPM amount, and the effective optimization goal is impressions. Because P(Impression \| Impression) is 1, expected value is simply the maximum CPM bid converted to a per-impression value:

> **Expected Value per impression = max_bid / 1,000**
>
> **Final Bid per impression = λ × (max_bid / 1,000)**

The bidder could calculate this value directly without consulting an ML model. The Pacing Service still supplies λ, allowing the final bid to be discounted below the advertiser's maximum CPM.

### Goal CPA (goal_cpa)

*Advertiser intent: "Bid assuming the desired action is worth up to \$X CPA."*

Under this strategy, max_bid represents the advertiser's maximum value for one desired action. The optimization_goal determines which action probability should be used:

> **Expected Value per impression = max_bid ×** **P(Goal Action \| Impression)**

For an ad set with a \$2.50 CPA goal and a PIXEL_PAGE_VIEW optimization goal:

> **Expected Value per impression = \$2.50 ×** **P(Page View \| Impression)**
>
> **Final Bid per impression = λ × \$2.50 ×** **P(Page View \| Impression)**

For illustration, a predicted page-view probability of 0.4% produces an undiscounted expected value of \$0.01 per impression, equivalent to \$10 CPM. A pacing λ of 0.6 would reduce the final bid to \$6 CPM.

The intended behavior is an expected cost per page view at or below \$2.50, assuming the model is appropriately calibrated for the impressions purchased, and the impression cost used in the CPA calculation does not exceed the bid. This is an expected-performance objective, not a guarantee of observed CPA in every reporting period. The evaluation window and treatment of fees remain to be defined.

### Lowest Cost / Auto Bid (lowest_cost)

*Advertiser intent: "Spend my budget in full, when achievable, at the lowest possible cost per desired action."*

Lowest-cost bidding (also known as “auto bid”) uses the same goal-specific probability model as goal-CPA bidding, but the advertiser does not need to provide a maximum CPA limit. Instead, the initial approach would assign a sufficiently high internal CPA value and allow the pacing multiplier to determine the effective bid level needed to achieve budget.

> **Expected Value per impression = Internal CPA Value ×** **P(Goal Action \| Impression)**
>
> **Final Bid per impression = λ × Internal CPA Value ×** **P(Goal Action \| Impression)**

The model continues to differentiate opportunities based on the probability of the desired action. The Pacing Service adjusts the overall bid level: reducing λ when the ad set can achieve its budget at lower prices and increasing λ when additional delivery is needed.

The internal CPA value is a scaling input, not an advertiser-defined CPA commitment. Full budget delivery remains dependent on the availability of eligible inventory and achievable auction prices, but the goal of lowest cost bidding is to fulfill budget at the cheapest goal CPA for that budget level.

## **ML Service Role in Bidding Service**

For each eligible ad set, the bidder needs its bidding configuration, its current pacing λ, and either a goal-specific probability/expected-value signal or the deterministic per-impression value for a max-CPM line. The Bidding service then applies pacing and constructs the final bid response. The ML component determines **how valuable the opportunity is**, while the Pacing Service determines **how much of that value to bid given the ad set's spend progress relative to budget**. Model predictions and pacing should remain independently changeable.

The ML service does not necessarily need to produce the full EV but must at least provide the goal p(Action), in which case the advertiser's maximum value applied by the Bid Decision / Response Service. Whether the ML interface returns probability, completed expected value, or both remains a technical design decision. Applying pacing and constructing the response remain responsibilities of the Bidding Service.

All equations above express monetary value **per impression**. When a bid is represented in CPM, the corresponding per-impression value is multiplied by 1,000. The implementation must preserve consistent units across configuration, model output, expected-value calculation, and bid response.

The bidder scope sets an initial latency target of **under 10 milliseconds for the full real-time service path**, not for ML inference alone. The ML serving approach must fit within its allocated portion of that budget; the scope identifies in-memory inference, precomputed features, low-latency serving, and precomputed lookups as options rather than a selected architecture.

## **Initial Model Priorities**

Initial model development should prioritize **Page View** and **Purchase**. These models would support PIXEL_PAGE_VIEW and PIXEL_PURHCASE for both goal-CPA and lowest-cost bidding. New goals, like app events (installs, purchases) and other pixel-based optimization goals (like Lead Generation), should be supported in the future without replacing the core bidding architecture.

New advertisers should be able to use these models, and we should expect many advertisers to have relatively sparse conversion signals. The initial approach therefore cannot depend on every advertiser having enough historical conversions to train a separate advertiser-specific model before using outcome-based bidding.

The desired behavior is to provide useful predictions for new or low-signal advertisers and incorporate advertiser-specific information as it becomes available. Whether this is achieved through shared models, advertiser-specific calibration layer, or another approach should be discussed!

## **Proposed Initial Requirements**

- Support the proposed bidding_strategy and optimization_goal configuration and interpret max_bid consistently with the selected strategy. Preserve a deterministic, non-ML path for max-CPM/impressions ad sets.

- Provide a goal-specific prediction or expected-value input for each eligible ad set, initially prioritizing Page Views and Purchases, with an approach that supports new and sparse-signal advertisers.

- Support goal-CPA expected-value formulation and the proposed lowest-cost formulation using a system-assigned CPA value, while keeping pacing control separate from prediction.

- Fit model evaluation within the bidder's end-to-end latency target and define behavior when a model, required input, or prediction is unavailable.

- Log the prediction, value input, expected value, and pacing multiplier used in bid formulation so decisions can be reconstructed. Allow models and additional optimization goals to evolve without redesigning the request-processing architecture.

## **Initial Key Investigation Areas / Open Questions**

- **Attribution Windows for Goals:** What attribution windows should be offered for advertisers to select against optimization goals? How should we approach this from a model building and selection perspective?

  - If we offer, for example, a 7-day view-through page view model, should we train off a 1-day view through and then up-calibrate? Should they have separate models?

- **New advertisers and sparse signals.** What shared information can the models use before advertiser-specific history is available? How should advertiser-specific information be incorporated, and what behavior is appropriate when measurement or training signal is insufficient?

- **Calibration and model evaluation:** How should prediction quality and calibration be evaluated for each optimization goal, including on purchased impressions and for sparse-signal advertisers? What constitutes readiness to launch or update a model, and how should the goal-CPA behavior be assessed?

- **Serving, latency, and fallback:** Which features are available at bid time, and which need precomputation? What share of the end-to-end latency budget is available for ML, how should multiple candidates be evaluated, and what should the bidder do when a prediction is unavailable or invalid?

- **Service ownership and ongoing model improvement**. Should the ML interface return probability, expected value, or both? How should we test new models and improvements such as model improvements, new model deployment, rollback, and expansion to additional optimization goals?

## **Datasets Needed for Training**

- Auction/bid/impression side

  - Auctions:

    - "vir-prod-uaadsmanager-reporting-db"."auction_us_east"

    - "vir-prod-uaadsmanager-reporting-db"."auction_us_west"

  - Bids:

    - "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_east"

    - "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_west"

    - "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_east"

  - Batched Win Logs: “ua-data-jobs-prod-reporting"."win_logs"

    - Streamed win logs: "vir-prod-uaadsmanager-reporting-db"."silver_win_logs_stream"

- Conversions

  - Pixel

    - Pixel events:

      - "ua-data-jobs-prod-reporting"."silver_kochava_events"

    - Attributed events:

      - "ua-data-jobs-prod-reporting"."gold_kochava_seven_day_attribution"

        - (one/fourteen/thirty day are available)

  - App

    - App events

      - "ua-data-jobs-prod-reporting"."bronze_mobile_app_events"

    - Attributed events:

      - "ua-data-jobs-prod-reporting"."gold_app_events_seven_day_attribution"

        - (one/fourteen/thirty day are available)
