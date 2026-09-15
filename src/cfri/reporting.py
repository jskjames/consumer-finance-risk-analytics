"""Create a recruiter-friendly static preview from verified project outputs."""

from __future__ import annotations

import json
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from .config import DATABASE, OUTPUT_DIR, ROOT


def build_preview() -> None:
    with sqlite3.connect(DATABASE) as connection:
        monthly = pd.read_sql_query(
            "SELECT year_month, COUNT(*) complaints FROM complaints GROUP BY year_month ORDER BY year_month",
            connection,
        )
        products = pd.read_sql_query(
            "SELECT product, COUNT(*) complaints FROM complaints GROUP BY product ORDER BY complaints DESC LIMIT 7",
            connection,
        ).sort_values("complaints")
    risks = pd.read_csv(OUTPUT_DIR / "emerging_risks.csv").head(7).sort_values("risk_score")
    metrics = json.loads((OUTPUT_DIR / "model_metrics.json").read_text())

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig = plt.figure(figsize=(15, 9), facecolor="#F5F7FA")
    grid = fig.add_gridspec(3, 4, height_ratios=[0.7, 2.2, 2.5], hspace=0.62, wspace=0.65)
    fig.suptitle("Consumer Finance Risk Intelligence", x=0.06, y=0.965, ha="left", fontsize=24, fontweight="bold", color="#172033")
    fig.text(0.06, 0.918, "CFPB complaint monitoring • 250,000-record analytical sample • 2024–2026", color="#536078", fontsize=11)

    cards = [
        ("17.7M", "Source rows scanned"),
        ("1,501", "Companies monitored"),
        ("99.61%", "Timely responses"),
        (f"{metrics['roc_auc']:.3f}", "Relief model ROC AUC"),
    ]
    for i, (value, label) in enumerate(cards):
        ax = fig.add_subplot(grid[0, i])
        ax.set_facecolor("white")
        ax.text(0.07, 0.60, value, transform=ax.transAxes, fontsize=20, fontweight="bold", color="#172033")
        ax.text(0.07, 0.22, label, transform=ax.transAxes, fontsize=9, color="#69758C")
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)

    ax1 = fig.add_subplot(grid[1, :2])
    ax1.set_facecolor("white")
    ax1.plot(monthly["year_month"], monthly["complaints"], color="#2457D6", linewidth=2.6)
    ax1.fill_between(monthly["year_month"], monthly["complaints"], alpha=0.10, color="#2457D6")
    ax1.set_title("Monthly complaint volume in sample", loc="left", fontsize=12, fontweight="bold", pad=12)
    ticks = list(range(0, len(monthly), 4))
    ax1.set_xticks(ticks, monthly["year_month"].iloc[ticks], rotation=0)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    ax1.grid(axis="y", color="#E6EAF0")
    ax1.spines[["top", "right", "left"]].set_visible(False)

    ax2 = fig.add_subplot(grid[1, 2:])
    ax2.set_facecolor("white")
    short_products = products["product"].str.replace("Credit reporting or other personal consumer reports", "Credit reporting", regex=False)
    ax2.barh(short_products, products["complaints"], color="#33A18A")
    ax2.set_title("Leading product categories", loc="left", fontsize=12, fontweight="bold", pad=12)
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    ax2.grid(axis="x", color="#E6EAF0")
    ax2.spines[["top", "right", "left"]].set_visible(False)

    ax3 = fig.add_subplot(grid[2, :2])
    ax3.set_facecolor("white")
    risk_labels = (risks["product"].str.split().str[:3].str.join(" ") + " — " + risks["issue"].str.slice(0, 30))
    ax3.barh(risk_labels, risks["risk_score"], color="#EF8354")
    ax3.set_title("Emerging issue risk score", loc="left", fontsize=12, fontweight="bold", pad=12)
    ax3.set_xlabel("Prioritization score")
    ax3.grid(axis="x", color="#E6EAF0")
    ax3.spines[["top", "right", "left"]].set_visible(False)

    ax4 = fig.add_subplot(grid[2, 2:])
    ax4.set_facecolor("white")
    model_values = [metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1"], metrics["roc_auc"]]
    labels = ["Accuracy", "Precision", "Recall", "F1", "ROC AUC"]
    bars = ax4.bar(labels, model_values, color=["#5B6C8F", "#5B6C8F", "#2457D6", "#2457D6", "#33A18A"])
    ax4.set_ylim(0, 1)
    ax4.set_title("Relief-outcome model holdout performance", loc="left", fontsize=12, fontweight="bold", pad=12)
    ax4.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
    ax4.grid(axis="y", color="#E6EAF0")
    ax4.spines[["top", "right", "left"]].set_visible(False)

    fig.text(0.06, 0.025, "Source: CFPB Consumer Complaint Database. Counts reflect a deterministic sample and are not market-share adjusted.", fontsize=9, color="#69758C")
    output = ROOT / "assets" / "dashboard_preview.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {output}")


if __name__ == "__main__":
    build_preview()
