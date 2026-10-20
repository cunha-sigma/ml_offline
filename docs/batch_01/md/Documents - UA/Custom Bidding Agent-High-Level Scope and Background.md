# Custom Bidding Agent: High-Level Scope and Background \[20260902\]

## Last Updated: 2026-09-03 @ 4PM PT

## 1. Background and Objective

The client is building a custom bidding agent to provide significantly more granular and dynamic control over bid decisions than is possible through the current process through the ad server.

The long-term objective is for each bid to be determined at the individual bid-request / candidate level as a function of:

1.  the **expected value of the opportunity**, based on the advertiser's optimization goal and the predicted probability of achieving that goal; and

2.  a **pacing discount factor**, which adjusts the line’s bid based on need to win in order to fully achieve budget given expected spend distribution intraday.

The bidding agent will be co-located with the ad server bidding infrastructure and will receive and respond to bid requests through the ad server's protobuf interface. This service will be a low-latency service that ingests the ad server bid requests, evaluates eligible line items and creatives, makes the bidding decision, and returns the corresponding response.

The initial goal is to establish the real-time architecture and services required to support this bidding framework. More sophisticated optimization models and decisioning can then be introduced incrementally without requiring major changes to the underlying bidding infrastructure.

The bidder will ingest the raw ad request from the ad server and formulate a bid response for each valid line item with a bid value. For performance-optimized advertisers, bid is a function of expected value and discount pacing factor **λ**:

- **Final Bid = discount pacing factor (λ) × Expected Value**

  - **Final Bid = λ\* Max CPA × p(*Goal Action \| impression*)**

- **Expected Value = Max CPA ×** **p(*Goal Action \| impression*)**

  - **Max CPA** is the advertiser-defined maximum cost per desired action, which will be collected in the client ads manager.

  - **p(*Goal Action \| impression*)** is the predicted probability that serving the impression will result in the desired action, as determined by the client ML models.

  - For awareness campaigns, advertisers will continue to provide CPM-based goals. This can be represented as an advertiser having an “Impression” goal within the same framework as a per-impression value where:

    - **p(*Impression \| Impression*) = 1**

  - Although the client collects conversion data from advertisers who place our conversion pixel, currently the client does not offer advertisers the ability to bid against a specific cost per action goal. All advertisers are effectively “awareness” campaigns

- **λ (pacing lambda)** is the pacing discount factor for the line item.

  - Lambda will be determined based on the relationship between:

<!-- -->

- how much the line item was **expected to have spent** by the current point in the day

- how much the line item has **spent** by that point.

  - A line item that is spending comfortably relative to its desired pacing trajectory can bid below its full expected value, whereas a line item that needs additional delivery will receive less or no discounting.

  - After each pacing cycle, pacing **λ** will adjust based on the discrepancy between actual and expected spend to date.

<!-- -->

- With bids informed by fully featured discount pacing service and expected value models, we plan to offer advertisers the ability to **“auto bid”**, by which they will not need to set a Max CPA goal and instead we will modulate their bid entirely via pacing **λ**.

  - Since this is effectively equivalent to an advertiser setting a very high Max CPA and then letting discount pacing determine bid levels needed to hit budget, with the services described in this document completed, auto bid can be enabled for advertisers by setting a flag at the line item level and assuming a very high max CPA bid.

# 2. Initial Service Architecture

The bidding agent should be designed as a set of logically separate components so that pacing, prediction, and bidding logic can evolve independently. See high-level system design below:

## 2.1 Bid Ingestor / Processor Service

### **Purpose**

Serve as the entry point for the ad server bid requests and orchestrate the downstream bidding workflow. The request sent by the ad server will contain both the raw ad request and the array of eligible line items for bid (so no line-item retrieval will need to be done).

### **Responsibilities**

The service should:

- Receive bid requests from the ad server bidder through the defined protobuf interface.

- Deserialize and validate incoming requests.

- Extract the candidate for line items, creatives, and relevant request-level attributes.

- Identify the information required for downstream ML and pacing decisions.

- Initiate calls or lookups to the appropriate downstream services.

- Manage the request lifecycle within the required bidding latency.

- Handle invalid or incomplete requests

- Generate appropriate logging and observability for incoming bidding traffic.

This includes protobuf integration, request parsing, candidate extraction, decisioning, and response generation as the core real-time path, with an initial target of **\<10 MS service latency**.

More details for this stage can be found in the ad-server vendor's documentation [here.](link-redacted-ad-server-vendor)

## 2.2 Discount Pacing Service

### **Purpose**

Create and update a referenced index of the current pacing discount factor (**lambda**) for each active line item.

The output of this service should effectively be a mapping of **<u>Line Item</u> and its c<u>urrent Lambda</u>**

### **Responsibilities**

At defined intervals, the service should:

- Determine expected spend-to-date for each active line item.

- Determine actual spend-to-date.

- Compare actual delivery against the expected pacing trajectory.

- Calculate or update the lambda associated with the line item.

- Make the latest lambda values immediately available to the bidding agent.

- Log values and changes over time for debugging and ensuring uptime of pacing service

The service should be architected so that the calculation methodology can evolve without requiring changes to the bid-request processing layer.

The lambda calculation itself does **not necessarily need to occur within the synchronous bid-request path**. The desired architecture is for lambda to be periodically calculated and for the current value to be available through a sufficiently low-latency lookup mechanism when a bid request arrives.

### **Initial requirements**

The implementation should support:

- Lambda values at the line-item level.

- Configurable refresh/update intervals.

- Efficient access to the most recent lambda.

- Safe behavior when a lambda has not yet been calculated or is stale.

- Logging of lambda values and changes over time.

- Ability to compare the lambda used for a bid against the pacing state that generated it.

## 2.3 ML Prediction Service (Expected Value formulation for Ad Ranking)

### **Purpose**

Generate **P(Action)** for each valid candidate line item in the incoming bid opportunity.

### **Responsibilities**

Given the candidate line item and available auction/request attributes, the service should return the predicted probability that serving the impression will produce the advertiser's desired outcome.

Examples could ultimately include predictions for:

- Pixel Purchase: (**likely the top priority goal we’d want to ship)**

- Page View (**likely the p0 goal we’d want to ship if purchase is not possible)**

- App Install (out of scope for MVP)

- other optimization events supported by the client in the future

The prediction is combined with the advertiser-provided maximum value for that event to determine the expected value.

For example:

**Expected Value = Max CPA × P(Purchase)**

The initial infrastructure should allow new models and optimization events without changing the basic bid-processing architecture.

### **Architectural considerations**

The implementation should account for the strict latency requirements of the bidding path. Model inference may therefore require approaches such as:

- in-memory inference;

- precomputed features;

- low-latency model serving; or

- precomputed probability/value lookups.

## 2.4 Bid Decision / Response Service

### **Purpose**

Combine the outputs of the pacing and ML components with advertiser configuration to formulate the final bid (or no bid) for each line and return a valid response.

For each valid line item, the service should obtain:

- the advertiser-defined **Max CPA / value**;

- the current **P(Action)** from the ML layer; and

- the current **lambda** from the pacing layer.

It should calculate:

**Final Bid = λ × Max CPA × P(Action)**

For CPM/awareness campaigns, the same framework should support bidding against the advertiser's impression-value goal with P(Impression) equal to 1 (so the only dynamic part of the bid would be lambda).

### **Responsibilities**

The service should:

- Retrieve the relevant line-item max bid/value configuration.

- Retrieve the candidate's P(Action).

- Retrieve the line item's current lambda.

- Calculate the final bid.

- Select the appropriate candidate(s) to return.

- Construct a valid the ad server BidAgentResponse.

- Return the bid within the required end-to-end latency.

The response should include the selected line item and bid price, with support for creative selection as the system evolves.

# 3. End-to-End Request Flow

At a high level, the initial system should operate as follows:

<img src="docs/md/Documents - the client/_media/media/image1.png" style="width:6.5in;height:3.65625in" />

# 4. Foundational Infrastructure Requirements

### **Deployment and scalability**

The service should:

- operate in infrastructure aligned with the ad server bidder to minimize network latency;

- support horizontal scaling as bidding volume changes;

- implement health checks and appropriate failure detection; and

- support controlled deployment and rollback.

### **Monitoring and observability**

At minimum, the architecture should make it possible to monitor:

- total bid requests received;

- requests successfully processed;

- response rate;

- end-to-end latency;

- latency by service/component;

- errors and timeouts;

- number of candidate lines evaluated;

- P(Action) used;

- lambda used;

- advertiser value / Max CPA used;

- calculated expected value;

- final bid;

- eventual win/loss outcome where available; and

- spend and pacing behavior.

- Decision-level logging, down-sampled as needed, to make it possible to reconstruct **why a particular bid was generated** for later debugging and model/pacing analysis.

# 5. Phase 1 Success Criteria

The first phase should establish a production-capable custom bidding framework rather than attempt to solve every optimization problem immediately.

The implementation should be considered successful when:

- The ad server bid requests can reliably be ingested and parsed.

- Candidate line items can be identified and evaluated.

- A probability/value signal can be obtained for eligible candidates.

- A line-level pacing lambda can be retrieved.

- Advertiser Max CPA / value can be combined with those signals.

- The system can calculate a final bid using the pacing index and the expected value formulation.

- A valid response can be returned to the ad server within the required latency envelope.

- The service can be deployed and scaled reliably.

- Bid decisions can be logged and reconstructed.

- Individual components can subsequently be changed or upgraded without redesigning the entire bidder.

# 6. Future Capabilities

The architecture should intentionally support capabilities beyond the initial implementation.

Likely follow-on areas include:

- improved conversion-prediction models;

- optimization toward additional conversion types;

- more sophisticated pacing/lambda algorithms (e.g. smart pacing curves)

- Dynamic/more intelligent creative selection;

- request-level creative performance prediction;

- model experimentation and A/B testing (e.g. based on aspects of the request, altering bid decisioning or

These capabilities **do not need to be fully implemented as part of the foundational bidding-agent build**, but the system should be designed so they can be added without replacing the core request-processing architecture.

# 7. Expected Deliverables

Expected deliverables include:

- Detailed system architecture and service boundaries.

- Defined interfaces between the Bid Ingestor, Pacing Service, ML Service, and Bid Decision Service.

- The ad server protobuf integration.

- Production-capable bid-ingestion service.

- Initial pacing/lambda service.

- Initial ML inference integration.

- Bid calculation and response-generation logic.

- Deployment and scaling infrastructure.

- Monitoring, logging, dashboards, and alerting.

- Load and latency testing.

- Unit and integration test coverage.

- Production deployment/runbook documentation.

- Technical documentation for maintaining and extending development of the system.

# 8. Items to Resolve During Technical Design

**(NB: List is very initial, we expect many more to come as we get deeper into execution.)**

**Pacing:**

- Minimum/maximum allowable lambda or lambda update magnitude

- Methodology for initial pacing lambda and formulation for updating lambda between pacing cycle

- Lambda refresh frequency

- Interaction with existing probabilistic pacing method

- Formulation of goal pacing curves (even pacing vs. Smart pacing curves).

**Expected Value Service (Ad Ranking)**

- ML serving architecture and possible complexity given latency restrictions

- Required model-feature availability at bid time.

- Cache / in-memory data architecture.

- Behavior when ML predictions or pacing values are unavailable.

- Precise end-to-end and component-level latency budgets.

- Expected request throughput and peak scale.

- Whether candidate evaluation should be sequential, parallel, batched, or entirely local/in-memory.

- Exact boundary between the bid processor and bid decision/response components.

- Process for on-going improvements to model performance
