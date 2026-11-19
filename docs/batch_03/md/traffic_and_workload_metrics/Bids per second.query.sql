WITH bids AS (

    SELECT
        DATE_TRUNC('second', CAST(bid_time AS TIMESTAMP)) AS bid_second
    FROM "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_east"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30

    UNION ALL

    SELECT
        DATE_TRUNC('second', CAST(bid_time AS TIMESTAMP)) AS bid_second
    FROM "vir-prod-uaadsmanager-reporting-db"."bid_logs_us_west"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30
),

bps_by_second AS (
    SELECT
        bid_second,
        COUNT(*) AS bps
    FROM bids
    GROUP BY 1
)

SELECT
    ROUND(AVG(bps), 2) AS avg_bps,
    APPROX_PERCENTILE(bps, 0.25) AS p25_bps,
    APPROX_PERCENTILE(bps, 0.50) AS p50_bps,
    APPROX_PERCENTILE(bps, 0.75) AS p75_bps,
    APPROX_PERCENTILE(bps, 0.90) AS p90_bps,
    APPROX_PERCENTILE(bps, 0.99) AS p99_bps,
    MAX(bps) AS max_bps

FROM bps_by_second;
