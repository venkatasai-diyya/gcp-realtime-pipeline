-- dashboard/queries.sql
-- Sample analytics queries for Looker Studio / ad-hoc analysis
-- Replace `your_project.events_streaming.events_raw` with your actual table.

-- ─── 1. Hourly event volume (last 24 h) ─────────────────────────────────────
SELECT
  TIMESTAMP_TRUNC(processed_at, HOUR) AS hour,
  event_type,
  COUNT(*)                             AS event_count
FROM `ai-ml-labs.events_streaming.events_raw`
WHERE ingest_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;


-- ─── 2. Unique active users (rolling 7 days) ─────────────────────────────────
SELECT
  ingest_date,
  COUNT(DISTINCT user_id) AS daily_active_users
FROM `ai-ml-labs.events_streaming.events_raw`
WHERE ingest_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND user_id IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC;


-- ─── 3. Purchase revenue by day ───────────────────────────────────────────────
SELECT
  ingest_date,
  COUNT(*)                                              AS purchase_count,
  ROUND(SUM(CAST(JSON_VALUE(payload, '$.amount_usd') AS FLOAT64)), 2) AS revenue_usd
FROM `ai-ml-labs.events_streaming.events_raw`
WHERE ingest_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND event_type = 'purchase'
GROUP BY 1
ORDER BY 1 DESC;


-- ─── 4. Pipeline health — late / missing data check ──────────────────────────
SELECT
  ingest_date,
  pipeline_version,
  COUNT(*) AS total_events
FROM `ai-ml-labs.events_streaming.events_raw`
WHERE ingest_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
GROUP BY 1, 2
ORDER BY 1 DESC;


-- ─── 5. Top error codes ───────────────────────────────────────────────────────
SELECT
  JSON_VALUE(payload, '$.error_code') AS error_code,
  COUNT(*)                             AS occurrences
FROM `ai-ml-labs.events_streaming.events_raw`
WHERE event_type = 'error'
  AND ingest_date = CURRENT_DATE()
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
