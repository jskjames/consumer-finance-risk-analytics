-- 1. Monthly complaint volume and timeliness by product
SELECT year_month,
       product,
       COUNT(*) AS complaints,
       ROUND(100.0 * AVG(is_timely), 2) AS timely_response_pct
FROM complaints
GROUP BY year_month, product
ORDER BY year_month, complaints DESC;

-- 2. Company response scorecard with a minimum-volume guardrail
SELECT company,
       COUNT(*) AS complaints,
       ROUND(100.0 * AVG(is_timely), 2) AS timely_response_pct,
       ROUND(AVG(response_days), 2) AS average_days_to_route
FROM complaints
GROUP BY company
HAVING COUNT(*) >= 100
ORDER BY complaints DESC;

-- 3. Top issue within each product using a window function
WITH issue_counts AS (
    SELECT product, issue, COUNT(*) AS complaints
    FROM complaints
    GROUP BY product, issue
), ranked AS (
    SELECT *,
           DENSE_RANK() OVER (PARTITION BY product ORDER BY complaints DESC) AS issue_rank
    FROM issue_counts
)
SELECT product, issue, complaints
FROM ranked
WHERE issue_rank <= 5
ORDER BY product, complaints DESC;

-- 4. Recent-period issue growth used by the risk-monitoring layer
WITH max_date AS (
    SELECT MAX(date_received) AS latest_date FROM complaints
), windows AS (
    SELECT product, issue,
           SUM(CASE WHEN date_received >= date(latest_date, '-89 days') THEN 1 ELSE 0 END) AS recent_90d,
           SUM(CASE WHEN date_received BETWEEN date(latest_date, '-179 days')
                                            AND date(latest_date, '-90 days') THEN 1 ELSE 0 END) AS prior_90d
    FROM complaints CROSS JOIN max_date
    GROUP BY product, issue
)
SELECT product, issue, recent_90d, prior_90d,
       ROUND(100.0 * (recent_90d - prior_90d) / MAX(prior_90d, 10), 1) AS growth_pct
FROM windows
WHERE recent_90d >= 25
ORDER BY growth_pct DESC;

