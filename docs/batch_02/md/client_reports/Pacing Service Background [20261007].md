# Pacing Service Background \[20261006\]

## Last Updated: 2026-10-07 @ 5:00 PM PT

## Background

Advertisers expect campaign budgets to be spent intelligently over time and for their achieved cost per action to generally increase as their budget scales up. An effective pacing service should aim to spend an ad set’s budget in full, when achievable, while minimizing the cost required to achieve that budget in full.

Today, the ad server / the DSP provides built-in pacing that can be used by custom bidding agents through **Pacing-as-a-Service**. However, this system is somewhat limited in how we can establish traffic curves (maps of how budget should be distributed throughout the day) and only uses **probabilistic pacing** (modulating spend velocity through the bid inclusion rate), rather than price-based or **discount pacing**. As we build our custom bidding agent, we have an opportunity to develop pacing logic that is more tightly integrated with our bidding and optimization approach.

A pacing system must solve two related but distinct problems:

# 1. Establishing Desired Spend Curves

For every ad set, the pacing system must determine **how much of the budget should have been spent at each point in time**.

For example, for an ad set with a \$240 daily budget, an E**ven** pacing strategy would target approximately:

- \$24 spent per hour

- \$0.40 spent per minute

- \$0.0067 spent per second

Although Even pacing, our current default with the ad server’s pacing, is intuitive, it is suboptimal as auction volume and value may vary materially by time of day. There may be significantly more eligible inventory at certain hours for a line, and the probability that an impression produces the advertiser's desired outcome may also vary over time.

As a result, the optimal spend curve should not necessarily be linear, but should represent the cumulative percentage of an ad set's budget we expect to have spent at any point in the day based on expected value throughout the day.

Conceptually, the service should be able to answer: “**for an ad set X, how much should budget should be spent by time T?”**

Even a simple “even pacing” curve will need to be able to consider:

- changes to budget

- changes to line-item day parting targeting

- and the account time zone of the line

This expected spend becomes the target against which actual delivery can be evaluated.

## 2. Modulating Spend Velocity

Once a desired spend curve has been established, the pacing system must continuously determine whether an ad set is spending too quickly or too slowly relative to that target.

At each pacing interval—potentially every several seconds or minutes—the system can compare:

**Actual cumulative spend vs. expected cumulative spend**

and adjust participation in upcoming auctions accordingly.

There are two primary mechanisms available for controlling spend velocity:

**Discount Pacing** adjusts the price submitted into the auction via a discount factor (pacing **λ in previous documentation)**. When an ad set is ahead of pace, bids can be reduced, lowering both the probability of winning and the expected cost of winning impressions. When an ad set is behind the goal pace, this discount can be reduced, allowing bids to move closer to their maximum value.

**Probabilistic Pacing** adjusts the percentage of otherwise-eligible auctions in which the ad set participates. For example, an inclusion rate of 0.50 would cause the line to participate in approximately 50% of auctions for which it otherwise qualifies.

Both mechanisms can be used to adjust a line’s spend rate, but they have different implications for advertiser efficiency.

Whenever possible, it is preferable to control spend through **discount pacing** because reducing bids can both slow delivery and reduce the clearing price of impressions that are still won. Probabilistic pacing reduces spending by skipping auction opportunities entirely and therefore does not provide the same price-efficiency benefit.

The pacing system should therefore seek to rely on discount pacing as much as practical, while retaining probabilistic pacing as a secondary mechanism when bid adjustment alone cannot sufficiently control spending.

## **Pacing in Bid Formulation**

Our proposed custom bidder can be represented conceptually as:

**Final Bid =pacing λ × Max CPA × P(Goal Action \| Impression)**

where:

- **Max CPA** represents the advertiser's maximum value for the desired outcome.

- **P(Goal Action \| Impression)** represents the bidder's estimated probability that the impression generates that outcome.

- **λ** represents a pacing multiplier that adjusts the bid based on the ad set's current delivery position.

Under this architecture, the **Pacing Service** would maintain and continuously update λ at the ad set / line level.

For example:

- **λ = 1.0:** no pacing discount; submit the full expected-value bid.

- **λ \< 1.0:** reduce bids to slow spend and/or improve auction efficiency.

- As the line falls behind pace, λ moves toward 1.0.

- As the line moves ahead of pace, λ decreases.

A separate parameter, **α**, can represent the probabilistic **bid inclusion rate**:

where:

- **α = 1.0:** participate in every otherwise-eligible auction.

- **α = 0.5:** participate in approximately half of eligible auctions.

- **α = 0.0:** do not participate.

This gives us two independent pacing controls:

**α → How frequently should we participate in auctions for a line?**

**λ → How aggressively should we bid when we participate?**

Advertisers receive the best deals and value by participating in every possible auction (bid inclusion rate **α always at** 1) and depend on discount factor **λ** to drive the lowest possible price to achieve the budget. For this reason, it is best to depend as little as possible on probabilistic pacing. However, there will be cases where this is necessary (e.g., extremely small budgets may be more dependent on probabilistic pacing since the entire budget could be spent in a single pacing cycle).

The pacing service would determine the pacing discount factor **λ** and, if necessary, bid inclusion rate α based on the rate of actual vs desired spend.

The ad server’s pacing as a service, enabled by default for custom bidders, uses only a probabilistic pacing approach currently. We can derive bid inclusion rate **α** in data provided by the ad server, but the latency of this data can be 30-45 minutes stale (in table "ua-data-jobs-prod-reporting"."auction_data_test")

## **the ad server / the DSP Integration**

The ad server currently provides probabilistic pacing through a “**Pacing-as-a-Service"** that is enabled by default for all custom bidders, although this can be functionally removed by disabling pacing entirely. The ad server's pacing service filters bids returned by a custom bidding agent based on the line's current delivery relative to its pacing goal.

We could continue using the ad server Pacing-as-a-Service for probabilistic pacing while implementing our own discount-pacing logic through λ. Alternatively, we could disable the ad server pacing—for example, by configuring the line for effectively unrestricted pacing—and implement both λ and α within the client bidder.

For an initial implementation, a hybrid approach may reduce engineering complexity:

**client Pacing Service provides λ**

- Determines desired spend curve based on **even** pacing (to align with the ad server default)

  - Initially this is simplest, but we should eventually have smart traffic curved based on expected intraday auction distribution or advertiser value distribution throughout the day.

- Sets an initial pacing **λ**

  - Custom bidder applies λ to discount expected-value bid

- Updates pacing λ based on actual spend relative to desired spend

**the ad server Pacing-as-a-Service still provides α**

- continues to apply probabilistic **pacing** as a final delivery control

- The client decreases pacing **λ** to force **α to 1 over time**

Over time, we can evaluate whether bringing α into the client pacing service would provide sufficient additional control or performance benefit to justify replacing the ad server's probabilistic pacing.

## **Proposed Initial Requirements**

- Pacing service provides pacing index mapping line item to pacing **λ**

- Pacing service sets initial pacing **λ** for new lines

- Pacing service updates pacing **λ** for each line based on difference between goal spend achieved spend to date per pacing cycle (e.g. every N seconds/minutes)

  - Goal spend to be achieved to be based on even pacing curves

## **Initial Key Investigation Areas / Open Questions**

- How does impression delay (time between impression and impression receipt time) impact our ability to pace efficiently? What is the distribution of impression delay

  - (STP to follow up on this distribution).

- How do we decide the initial discount pacing lambda value on initial ad set start?

- How do we progress from “Even” pacing curves to more intelligent traffic curves based on expected auction volume/value?
