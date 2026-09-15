# Interview guide

## Thirty-second explanation

I built an end-to-end consumer-finance risk intelligence project using the CFPB complaint database. The pipeline processes a large public archive in chunks, creates a reproducible analytical sample and SQLite warehouse, and feeds both a Streamlit dashboard and an explainable model that forecasts whether a closed complaint receives relief. The dashboard highlights complaint trends, company response patterns, and emerging product-issue risks. I documented important limitations so users do not confuse complaint volume with market share or causal evidence.

## Design choices to defend

**Why this dataset?** It connects financial services with real operational and customer-risk problems, and it is maintained by a credible government source.

**Why SQLite?** It makes the project easy for reviewers to run while still demonstrating relational modeling, indexes, CTEs, and window functions. A production version could migrate to PostgreSQL or a cloud warehouse.

**Why deterministic sampling?** The full database is large and changes daily. Hash-based sampling is reproducible, order-independent, and more defensible than taking the first rows.

**Why logistic regression?** It provides a strong, fast, interpretable baseline. The coefficients show which complaint attributes are associated with each response category while class weights reduce majority-class dominance.

**What would you improve?** Add market-share denominators, production data validation, model-drift monitoring, experiment tracking, and scheduled ingestion of new complaints.

## Questions to expect

1. How did you prevent data leakage?
2. Why did you report ROC AUC, precision, recall, and F1 instead of accuracy alone?
3. How does the risk score behave when prior-period volume is near zero?
4. How would you deploy and monitor this pipeline?
5. Which limitations most affect business interpretation?
