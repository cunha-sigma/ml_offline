WITH auctions AS (

    SELECT
        DATE_TRUNC('minute', CAST(bid_time AS TIMESTAMP)) AS bid_minute
    FROM "vir-prod-uaadsmanager-reporting-db"."auction_us_east"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30

    UNION ALL

    SELECT
        DATE_TRUNC('minute', CAST(bid_time AS TIMESTAMP)) AS bid_minute
    FROM "vir-prod-uaadsmanager-reporting-db"."auction_us_west"
    WHERE year = 2026
      AND month = 10
      AND day >= 1
      AND day < 30
),

rps_by_minute AS (
    SELECT
        bid_minute,
        COUNT(*) * 100.0 / 60.0 AS rps
    FROM auctions
    GROUP BY 1
)

SELECT
    ROUND(AVG(rps), 2) AS avg_rps,
    ROUND(APPROX_PERCENTILE(rps, 0.25), 2) AS p25_rps,
    ROUND(APPROX_PERCENTILE(rps, 0.50), 2) AS p50_rps,
    ROUND(APPROX_PERCENTILE(rps, 0.75), 2) AS p75_rps,
    ROUND(APPROX_PERCENTILE(rps, 0.90), 2) AS p90_rps,
    ROUND(APPROX_PERCENTILE(rps, 0.99), 2) AS p99_rps,
    ROUND(MAX(rps), 2) AS max_rps

FROM rps_by_minute;
