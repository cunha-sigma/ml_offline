WITH metric_rows AS (

    -- East auctions (1% downsample)
    SELECT
        DATE_TRUNC('hour', CAST(bid_time AS TIMESTAMP))
            + INTERVAL '1' MINUTE
              * (FLOOR(MINUTE(CAST(bid_time AS TIMESTAMP)) / 15) * 15)
            AS bid_interval,
        COUNT(*) * 100 AS auctions,
        CAST(0 AS BIGINT) AS bids,
        CAST(0 AS BIGINT) AS impressions_won,
        CAST(0 AS DOUBLE) AS estimated_cost
    FROM "vir-prod-uaadsmanager-reporting-db"."auction_us_east"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30
    GROUP BY 1

    UNION ALL

    -- West auctions (1% downsample)
    SELECT
        DATE_TRUNC('hour', CAST(bid_time AS TIMESTAMP))
            + INTERVAL '1' MINUTE
              * (FLOOR(MINUTE(CAST(bid_time AS TIMESTAMP)) / 15) * 15)
            AS bid_interval,
        COUNT(*) * 100 AS auctions,
        CAST(0 AS BIGINT) AS bids,
        CAST(0 AS BIGINT) AS impressions_won,
        CAST(0 AS DOUBLE) AS estimated_cost
    FROM "vir-prod-uaadsmanager-reporting-db"."auction_us_west"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30
    GROUP BY 1

    UNION ALL

    -- East bids
    SELECT
        DATE_TRUNC('hour', CAST(bid_time AS TIMESTAMP))
            + INTERVAL '1' MINUTE
              * (FLOOR(MINUTE(CAST(bid_time AS TIMESTAMP)) / 15) * 15)
            AS bid_interval,
        CAST(0 AS BIGINT) AS auctions,
        COUNT(*) AS bids,
        CAST(0 AS BIGINT) AS impressions_won,
        CAST(0 AS DOUBLE) AS estimated_cost
    FROM "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_east"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30
    GROUP BY 1

    UNION ALL

    -- West bids
    SELECT
        DATE_TRUNC('hour', CAST(bid_time AS TIMESTAMP))
            + INTERVAL '1' MINUTE
              * (FLOOR(MINUTE(CAST(bid_time AS TIMESTAMP)) / 15) * 15)
            AS bid_interval,
        CAST(0 AS BIGINT) AS auctions,
        COUNT(*) AS bids,
        CAST(0 AS BIGINT) AS impressions_won,
        CAST(0 AS DOUBLE) AS estimated_cost
    FROM "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_west"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30
    GROUP BY 1

    UNION ALL

    -- Winning impressions and estimated cost
    SELECT
        DATE_TRUNC('hour', bid_time)
            + INTERVAL '1' MINUTE
              * (FLOOR(MINUTE(bid_time) / 15) * 15)
            AS bid_interval,
        CAST(0 AS BIGINT) AS auctions,
        CAST(0 AS BIGINT) AS bids,
        COUNT(*) AS impressions_won,
        SUM(win_cost_micros / 1000000.0) AS estimated_cost
    FROM "ua-data-jobs-prod-reporting"."win_logs"
    WHERE bid_hour >= TIMESTAMP '2026-10-01 00:00:00'
      AND bid_hour < TIMESTAMP '2026-10-30 00:00:00'
    GROUP BY 1
)

SELECT
    bid_interval,
    SUM(auctions) AS auctions,
    SUM(bids) AS bids,
    SUM(impressions_won) AS impressions_won,
    ROUND(SUM(estimated_cost), 2) AS estimated_cost,

    ROUND(
        100.0 * SUM(bids) / NULLIF(SUM(auctions), 0),
        2
    ) AS bid_rate_pct,

    ROUND(
        100.0 * SUM(impressions_won) / NULLIF(SUM(bids), 0),
        2
    ) AS win_rate_pct,

    ROUND(
        1000.0 * SUM(estimated_cost)
        / NULLIF(SUM(impressions_won), 0),
        2
    ) AS winning_cpm

FROM metric_rows
GROUP BY 1
ORDER BY bid_interval;
