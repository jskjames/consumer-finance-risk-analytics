"""Generate decision-ready aggregates and emerging-risk indicators."""

from __future__ import annotations

import json
import sqlite3

import pandas as pd

from .config import DATABASE, OUTPUT_DIR


def emerging_risk_table(connection: sqlite3.Connection) -> pd.DataFrame:
    query = """
    WITH bounds AS (
      SELECT date(MAX(date_received), '-89 days') AS recent_start,
             date(MAX(date_received), '-179 days') AS prior_start,
             date(MAX(date_received), '-90 days') AS prior_end
      FROM complaints
    ),
    issue_windows AS (
      SELECT product, issue,
             SUM(CASE WHEN date(date_received) >= recent_start THEN 1 ELSE 0 END) AS recent_90d,
             SUM(CASE WHEN date(date_received) BETWEEN prior_start AND prior_end THEN 1 ELSE 0 END) AS prior_90d,
             AVG(CASE WHEN date(date_received) >= recent_start THEN 1.0 - is_timely END) AS recent_untimely_rate
      FROM complaints CROSS JOIN bounds
      GROUP BY product, issue
    )
    SELECT product, issue, recent_90d, prior_90d,
           ROUND(100.0 * (recent_90d - prior_90d) / MAX(prior_90d, 10), 1) AS growth_pct,
           ROUND(100.0 * recent_untimely_rate, 2) AS untimely_pct,
           ROUND(
             (recent_90d * 1.0 / MAX(MAX(recent_90d) OVER (), 1)) * 50 +
             MIN(MAX((recent_90d - prior_90d) * 1.0 / MAX(prior_90d, 10), 0), 2) / 2 * 30 +
             MIN(COALESCE(recent_untimely_rate, 0) / 0.05, 1) * 20
           , 1) AS risk_score
    FROM issue_windows
    WHERE recent_90d >= 25
    ORDER BY risk_score DESC
    LIMIT 25;
    """
    return pd.read_sql_query(query, connection)


def run_analytics(database=DATABASE, output_dir=OUTPUT_DIR) -> dict:
    if not database.exists():
        raise FileNotFoundError(f"Missing {database}. Run: python -m cfri.pipeline")
    output_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        queries = {
            "monthly_product_trends": """
                SELECT year_month, product, COUNT(*) AS complaints,
                       ROUND(100.0 * AVG(1.0 - is_timely), 2) AS untimely_pct
                FROM complaints GROUP BY year_month, product
                ORDER BY year_month, complaints DESC
            """,
            "company_response_scorecard": """
                SELECT company, COUNT(*) AS complaints,
                       ROUND(100.0 * AVG(is_timely), 2) AS timely_pct,
                       ROUND(AVG(response_days), 2) AS avg_days_to_route,
                       ROUND(100.0 * AVG(has_narrative), 2) AS narrative_pct
                FROM complaints GROUP BY company HAVING COUNT(*) >= 100
                ORDER BY complaints DESC
            """,
            "state_product_mix": """
                SELECT state, product, COUNT(*) AS complaints
                FROM complaints WHERE state IS NOT NULL
                GROUP BY state, product ORDER BY complaints DESC
            """,
        }
        for name, query in queries.items():
            pd.read_sql_query(query, connection).to_csv(output_dir / f"{name}.csv", index=False)
        risks = emerging_risk_table(connection)
        risks.to_csv(output_dir / "emerging_risks.csv", index=False)
        overview = pd.read_sql_query(
            """SELECT COUNT(*) complaints, COUNT(DISTINCT company) companies,
                      COUNT(DISTINCT product) products,
                      ROUND(100.0 * AVG(is_timely), 2) timely_pct,
                      ROUND(100.0 * AVG(has_narrative), 2) narrative_pct,
                      MIN(date_received) min_date, MAX(date_received) max_date
               FROM complaints""",
            connection,
        ).iloc[0].to_dict()
    (output_dir / "overview.json").write_text(json.dumps(overview, indent=2), encoding="utf-8")
    print(json.dumps(overview, indent=2))
    return overview


if __name__ == "__main__":
    run_analytics()

