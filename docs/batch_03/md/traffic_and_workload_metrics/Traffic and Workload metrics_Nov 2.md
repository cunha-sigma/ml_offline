# Traffic & Workload Metrics

**Source:** Client Slack channel\
**Provided by:** a client data/analytics contact (name redacted)\
**Date:** November 2, 2026\
**Content:** Client responses to traffic and workload metrics questions.

Purpose: Capture traffic patterns and processing volumes to inform solution architecture, load balancing, performance validation, and scalability planning.

# **1. Current traffic profile**

**Question**

What are the overall traffic characteristics, including distribution throughout the day, peak hours, and significant fluctuations?

**Client response**

- Overall traffic characteristics, including distribution throughout the day, peak hours, and any significant traffic fluctuations.

- To give a sense of traffic flow throughout the week/month, the doc Traffic profile 20261102 below has estimated auctions, bids, impressions won, and price per 15-minute interval for most of October (10/1-10/29).

**Supporting document(s):** Traffic profile 20261102

# **2. Auctions per second and Bid requests per second (RPS)**

**Question**

What are the average and peak number of auctions processed per second and average and peak incoming bid request rates.

**Client response**

- The dataset provides average, p25, p50, p75, p90, p99, and max observed bid requests (these are rows in the “auction” log) per second and bid **responses (e.g. line items that were eligible to bid, passed pacing, and returned a bid)** per second from 10/1-10/29

**Supporting document(s):** Auction Requests and Bids per second (auction/bid logs)

**Note:** The client grouped the auctions-per-second and bid-request RPS questions in one response; confirm whether any separate auction-level metric is required.

# **4. Candidates per request**

**Question**

What are the average and maximum numbers of eligible candidates evaluated per request?

**Client response**

- Ad-server vendor data is still pending for the complete answer. The client was able to calculate average candidates per auction using an approach confirmed by the ad-server vendor.

- Period: October 5–18, 2026 (two weeks).

- Total ad candidates before probabilistic pacing elimination: 7,358,413,968,000.

- Total ad candidates after the ad server's probabilistic-pacing elimination: 716,737,395,000.

- Total auction requests: 530,988,486,900.

- Average candidates per auction if the ad server's probabilistic pacing were removed entirely: 13.9.

- Average candidates per auction if the ad server's probabilistic pacing were retained, without increasing bid volume through discount pacing: 1.3.

**Status / follow-up:** Maximum candidates per request not provided; awaiting the ad server's information.

# **5. Active line items**

**Question**

How many active line items are currently participating in bidding?

**Client response**

- Hourly counts of line items receiving at least one bid are provided for every hour from October 1–29, 2026.

- Average: approximately 630-line items per hour.

- The client can provide other breakdowns or groupings if needed.

**Supporting document(s):** Active Campaigns and Active Lines per Hour

# **6. Active campaigns**

**Question**

How many campaigns are currently active?

**Client response**

- Hourly counts of campaigns receiving at least one bid are provided for every hour from October 1–29, 2026.

- Average: approximately 344 campaigns per hour.

- The client can provide other breakdowns or groupings if needed.

**Supporting document(s):** Active Campaigns and Active Lines per Hour

# **7. Impression delay histogram**

**Question**

What is the distribution of delays between auction completion (or bid win) and the corresponding impression event, ideally including P50, P90, P95, and P99?

**Client response**

- Approximately 53% of impressions are received within 3 minutes of bid time.

- Approximately 90% of impressions are received within 15 minutes of bid time.

- A full histogram and raw data are available for October 1–29, 2026.

**Supporting document(s):** Impression delay histogram

**Status / follow-up:** Exact P50, P90, P95, and P99 delay values were not quoted in the response; review the supporting histogram/raw data if these are needed.

# **General request / data interpretation**

The original request asked for both average and peak values, where applicable, over a representative traffic period. Detailed numerical distributions are in the supporting documents referenced above; those files were named by the client but were not included with this Q&A text.

Note: “Active” counts above refer to entities receiving at least one bid in a given hour, not necessarily all enabled campaigns or line items.
