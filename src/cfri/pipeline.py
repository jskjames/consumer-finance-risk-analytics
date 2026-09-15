"""Create a clean, reproducible analytical sample and SQLite warehouse."""

from __future__ import annotations

import argparse
import json
import sqlite3
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    CANONICAL_COLUMNS,
    DATABASE,
    DEFAULT_MAX_ROWS,
    DEFAULT_START_DATE,
    OUTPUT_DIR,
    PROCESSED_CSV,
    RAW_ZIP,
)


def normalize_name(name: str) -> str:
    return (
        name.strip().lower().replace(" ", "_").replace("?", "")
        .replace("-", "_").replace("/", "_")
    )


def transform(chunk: pd.DataFrame) -> pd.DataFrame:
    """Standardize CFPB fields and add analytical features."""
    df = chunk.copy()
    df.columns = [normalize_name(c) for c in df.columns]
    rename = {k: v for k, v in CANONICAL_COLUMNS.items() if k in df.columns}
    df = df.rename(columns=rename)
    for column in CANONICAL_COLUMNS.values():
        if column not in df.columns:
            df[column] = pd.NA

    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")
    df["date_sent_to_company"] = pd.to_datetime(df["date_sent_to_company"], errors="coerce")
    df["complaint_id"] = pd.to_numeric(df["complaint_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["complaint_id", "date_received", "product", "company"])
    df = df.drop_duplicates(subset="complaint_id")

    text_cols = [
        "product", "sub_product", "issue", "sub_issue", "narrative", "company",
        "state", "tags", "submitted_via", "company_response", "timely_response",
    ]
    for column in text_cols:
        df[column] = df[column].astype("string").str.strip()

    df["year_month"] = df["date_received"].dt.to_period("M").astype(str)
    df["response_days"] = (df["date_sent_to_company"] - df["date_received"]).dt.days
    df["is_timely"] = df["timely_response"].str.lower().eq("yes").astype("int8")
    df["has_narrative"] = df["narrative"].notna().astype("int8")
    df["narrative_word_count"] = df["narrative"].fillna("").str.split().str.len().astype("int32")
    return df


def stable_sample(df: pd.DataFrame, existing: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    """Keep a deterministic uniform sample using hashed complaint IDs."""
    if df.empty:
        return existing
    df = df.copy()
    df["_sample_key"] = pd.util.hash_pandas_object(df["complaint_id"], index=False).astype("uint64")
    combined = pd.concat([existing, df], ignore_index=True)
    if len(combined) > max_rows:
        combined = combined.nsmallest(max_rows, "_sample_key")
    return combined


def build_dataset(
    source: Path = RAW_ZIP,
    output: Path = PROCESSED_CSV,
    database: Path = DATABASE,
    start_date: str = DEFAULT_START_DATE,
    max_rows: int = DEFAULT_MAX_ROWS,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}. Run: python -m cfri.download")

    cutoff = pd.Timestamp(start_date)
    sample = pd.DataFrame()
    rows_scanned = rows_eligible = 0
    with zipfile.ZipFile(source) as archive:
        csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("No CSV found in CFPB archive")
        with archive.open(csv_names[0]) as raw_csv:
            for raw_chunk in pd.read_csv(raw_csv, chunksize=chunksize, low_memory=False):
                rows_scanned += len(raw_chunk)
                clean = transform(raw_chunk)
                clean = clean.loc[clean["date_received"] >= cutoff]
                rows_eligible += len(clean)
                sample = stable_sample(clean, sample, max_rows)
                if rows_scanned % 1_000_000 < chunksize:
                    print(f"Scanned {rows_scanned:,} rows; retained sample of {len(sample):,}")

    sample = sample.drop(columns="_sample_key").sort_values("date_received").reset_index(drop=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output, index=False, compression="gzip", date_format="%Y-%m-%d")

    with sqlite3.connect(database) as connection:
        sql_df = sample.copy()
        sql_df["date_received"] = sql_df["date_received"].dt.strftime("%Y-%m-%d")
        sql_df["date_sent_to_company"] = sql_df["date_sent_to_company"].dt.strftime("%Y-%m-%d")
        sql_df.to_sql("complaints", connection, if_exists="replace", index=False, chunksize=5_000)
        connection.executescript(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_complaint_id ON complaints(complaint_id);
            CREATE INDEX IF NOT EXISTS idx_date ON complaints(date_received);
            CREATE INDEX IF NOT EXISTS idx_product ON complaints(product);
            CREATE INDEX IF NOT EXISTS idx_company ON complaints(company);
            CREATE INDEX IF NOT EXISTS idx_state ON complaints(state);
            """
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profile = {
        "source": "CFPB Consumer Complaint Database",
        "source_url": "https://www.consumerfinance.gov/data-research/consumer-complaints/",
        "pipeline_run_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "start_date_filter": start_date,
        "rows_scanned": rows_scanned,
        "eligible_rows": rows_eligible,
        "sample_rows": len(sample),
        "sample_method": "deterministic lowest-hash sample by complaint_id",
        "min_date": sample["date_received"].min().date().isoformat(),
        "max_date": sample["date_received"].max().date().isoformat(),
        "unique_products": int(sample["product"].nunique()),
        "unique_companies": int(sample["company"].nunique()),
        "narrative_share": round(float(sample["has_narrative"].mean()), 4),
        "timely_response_share": round(float(sample["is_timely"].mean()), 4),
    }
    (OUTPUT_DIR / "data_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(json.dumps(profile, indent=2))
    return sample


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=RAW_ZIP)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    args = parser.parse_args()
    build_dataset(source=args.source, start_date=args.start_date, max_rows=args.max_rows)


if __name__ == "__main__":
    main()

