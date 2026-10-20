# ADR-0001: ML service returns calibrated P(Action), not expected value

**Status:** Accepted · **Date:** 2026-09-22 · **Amended:** 2026-10-15 (batch-02 ML Service Background) · **Deciders:** Rodrigo Cunha (ML lane)

**Context.** `Final Bid = λ × Max CPA × P(Goal Action | Impression)`. Open question: does the ML service return the raw probability `P`, or the expected value `Max CPA × P`? The batch-01 docs' formulas have the bid-decision service apply `× Max CPA` and `× λ` downstream, while the client's own prose names the service in EV terms (the scope doc's section heading is "ML Prediction Service (Expected Value formulation for Ad Ranking)"). The batch-02 ML Service Background then reopens the question explicitly: the service "does not necessarily need to produce the full EV but must at least provide the goal p(Action)", and probability vs. EV vs. both "remains a technical design decision". It also introduces per-candidate heterogeneity: each candidate ad set carries its own `bidding_strategy` and `optimization_goal`, and the value multiplied depends on the strategy (`max_bid` as CPA for `goal_cpa`, a system-assigned internal CPA value for `lowest_cost`, `max_bid/1000` with no model for `max_cpm`).

**Decision.** The ML service returns one **calibrated probability `P(Goal Action | Impression)` per candidate**, plus score metadata; `× value` and `× λ` apply downstream in the bid-decision service. This is our proposal to the client's open interface question. The bidding agent groups candidates by goal (later by goal and window), calls the serving lib once per model slot (slots named by goal), and owns the strategy→value interpretation and the multiply.

**Why.**
- The value side is bidding policy, not prediction: `max_bid` interpretation is strategy-dependent, and the `lowest_cost` internal CPA value is a budget-delivery knob owned by another lane. Returning EV would import both into the model boundary.
- A probability stream is monitorable for calibration against realized conversion rates; an EV stream mixes model drift with config changes and confounds experiment-arm comparisons.
- λ and the final bid live outside ML in every option, so decision reconstruction requires a log join key regardless; moving the multiply solves nothing there.
- A uniform response schema holds across strategies and goals: a new goal is a new model slot, no interface change.

**Consequences.**
- The returned number must be a true probability → calibration mandatory ([ADR-0003](0003-calibration-matched-pair-artifact.md)).
- The per-candidate response carries: calibrated probability, the goal (and window, if windows become ad-set config) the score answers, model name/version/arm/revision, and a scored-versus-default status flag so the caller can distinguish a real score from a fallback.
- Decision-log rows need the request/candidate join key so probability rows join the agent's value/λ/bid rows (tracked in the serving repo; the client's reconstruction-logging requirement makes it firm).
- Present to the client as our answer to their open interface question.
