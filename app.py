from pathlib import Path
import json
import sqlite3

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "processed" / "complaints.db"
MODEL_METRICS = ROOT / "outputs" / "model_metrics.json"

st.set_page_config(page_title="Consumer Finance Risk Intelligence", page_icon="📊", layout="wide")
st.title("Consumer Finance Risk Intelligence")
st.caption("CFPB complaint monitoring, operational risk signals, and explainable NLP routing")

if not DB.exists():
    st.error("Processed data is missing. Run `make download && make build && make analyze && make model`.")
    st.stop()

@st.cache_data
def load_data():
    with sqlite3.connect(DB) as connection:
        return pd.read_sql_query(
            "SELECT date_received, year_month, product, issue, company, state, submitted_via, is_timely, has_narrative FROM complaints",
            connection,
            parse_dates=["date_received"],
        )

df = load_data()
with st.sidebar:
    st.header("Filters")
    products = st.multiselect("Product", sorted(df["product"].dropna().unique()))
    states = st.multiselect("State", sorted(df["state"].dropna().unique()))
    date_range = st.date_input("Date range", value=(df["date_received"].min().date(), df["date_received"].max().date()))

view = df.copy()
if products:
    view = view[view["product"].isin(products)]
if states:
    view = view[view["state"].isin(states)]
if len(date_range) == 2:
    view = view[view["date_received"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Complaints", f"{len(view):,}")
c2.metric("Companies", f"{view['company'].nunique():,}")
c3.metric("Timely responses", f"{100 * view['is_timely'].mean():.1f}%")
c4.metric("Product categories", f"{view['product'].nunique():,}")

st.subheader("Complaint trend")
trend = view.groupby("year_month").size().rename("complaints")
st.line_chart(trend)

left, right = st.columns(2)
with left:
    st.subheader("Product mix")
    st.bar_chart(view["product"].value_counts().head(12))
with right:
    st.subheader("Leading issues")
    st.bar_chart(view["issue"].value_counts().head(12))

st.subheader("Company response scorecard")
scorecard = (
    view.groupby("company")
    .agg(complaints=("company", "size"), timely_pct=("is_timely", "mean"))
    .query("complaints >= 25")
    .assign(timely_pct=lambda x: (100 * x["timely_pct"]).round(2))
    .sort_values("complaints", ascending=False)
    .head(25)
)
st.dataframe(scorecard, use_container_width=True)

risk_path = ROOT / "outputs" / "emerging_risks.csv"
if risk_path.exists():
    st.subheader("Emerging issue monitor")
    st.caption("Risk score combines recent volume, 90-day growth, and untimely response rate; it is a prioritization signal, not a causal estimate.")
    st.dataframe(pd.read_csv(risk_path), use_container_width=True, hide_index=True)

if MODEL_METRICS.exists():
    st.subheader("Response-outcome model")
    metrics = json.loads(MODEL_METRICS.read_text())
    m1, m2, m3 = st.columns(3)
    m1.metric("Test records", f"{metrics['test_rows']:,}")
    m2.metric("ROC AUC", f"{metrics['roc_auc']:.3f}")
    m3.metric("Relief-class F1", f"{metrics['f1']:.3f}")
    st.caption("One-hot encoded intake attributes and class-weighted logistic regression provide an explainable baseline for forecasting whether a closed complaint receives relief.")

st.divider()
st.caption("Source: Consumer Financial Protection Bureau Consumer Complaint Database. Complaint counts are not market-share adjusted and should not be interpreted as company quality rankings.")
