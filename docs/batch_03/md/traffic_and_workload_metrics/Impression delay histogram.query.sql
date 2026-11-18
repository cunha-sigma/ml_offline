WITH time_diffs AS (
    SELECT
        DATE_DIFF(
            'millisecond',
            TRY_CAST(NULLIF(TRIM(CAST(bid_time AS VARCHAR)), '') AS TIMESTAMP),
            TRY_CAST(NULLIF(TRIM(CAST(rx_timestamp AS VARCHAR)), '') AS TIMESTAMP)
        ) / 1000.0 AS seconds_elapsed
    FROM "ua-data-jobs-prod-reporting"."win_logs"
    WHERE bid_hour >= TIMESTAMP '2026-10-01 00:00:00'
      AND bid_hour < TIMESTAMP '2026-10-30 00:00:00'
      AND NULLIF(TRIM(CAST(bid_time AS VARCHAR)), '') IS NOT NULL
      AND NULLIF(TRIM(CAST(rx_timestamp AS VARCHAR)), '') IS NOT NULL
),

histogram AS (
    SELECT
        CAST(FLOOR(seconds_elapsed) AS BIGINT) AS seconds_bucket,
        COUNT(*) AS impressions
    FROM time_diffs
    WHERE seconds_elapsed IS NOT NULL
      AND seconds_elapsed >= 0
    GROUP BY 1
)

SELECT
    seconds_bucket,
    impressions,
    SUM(impressions) OVER (
        ORDER BY seconds_bucket
    ) AS cumulative_impressions,
    ROUND(
        100.0 * SUM(impressions) OVER (
            ORDER BY seconds_bucket
        ) / SUM(impressions) OVER (),
        2
    ) AS cumulative_pct
FROM histogram
ORDER BY seconds_bucket;
