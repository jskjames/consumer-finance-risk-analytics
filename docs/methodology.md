# Methodology and analytical guardrails

## Business question

The project asks how a financial-services risk or operations team can use public complaint data to identify rising issues, compare response patterns, and forecast response outcomes for operational planning.

## Data source

The source is the CFPB Consumer Complaint Database. The pipeline downloads the official archive, reads it in chunks, validates required fields, deduplicates complaint IDs, derives response and narrative indicators, and creates a deterministic analytical sample.

## Reproducible sampling

The public archive is large and updates frequently. Rather than selecting the first records or using an unstable random sample, the pipeline hashes each complaint ID and retains the lowest hash values. This produces a deterministic, approximately uniform sample that is independent of source-file order. The data profile records the total rows scanned, eligible rows, sample size, date coverage, and run timestamp.

## Emerging risk score

The risk score prioritizes product-issue combinations using three transparent signals:

- Recent 90-day complaint volume: 50% of the score.
- Growth versus the prior 90 days: 30%, capped to reduce outlier dominance.
- Recent untimely-response rate: 20%, capped at a 5% rate.

It is a monitoring heuristic, not a probability of harm or a causal model. Analysts should investigate flagged issues and validate them against exposure, customer counts, and market share.

## Response-outcome model

The model predicts whether a closed complaint receives monetary or non-monetary relief rather than an explanation alone. Inputs available at intake are product, sub-product, issue, sub-issue, company, state, submission channel, and tags. One-hot encoding and class-weighted logistic regression were selected because they are efficient, explainable, and appropriate as an operational baseline. Performance is reported on a stratified 20% holdout set using ROC AUC and relief-class precision, recall, and F1.

## Limitations

- Complaints are not a representative sample of all consumers.
- Complaint volume is not adjusted for company market share or customer exposure.
- Consumer narratives are unverified descriptions and are available only when consumers consent to publication.
- Recent periods may be incomplete because companies have time to respond.
- The outcome model captures historical associations, not causal effects, and should be monitored for drift before operational use.
