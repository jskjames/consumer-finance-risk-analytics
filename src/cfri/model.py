"""Train an explainable model to forecast complaint response outcomes."""

from __future__ import annotations

import json

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .config import MODEL_DIR, OUTPUT_DIR, PROCESSED_CSV, RANDOM_STATE

FEATURES = ["product", "sub_product", "issue", "sub_issue", "company", "state", "submitted_via", "tags"]
TARGET = "received_relief"


def prepare_model_data(df: pd.DataFrame, max_rows: int = 150_000) -> pd.DataFrame:
    model_df = df[FEATURES + ["company_response"]].copy().dropna(subset=["company_response"])
    model_df = model_df.loc[model_df["company_response"].isin([
        "Closed with explanation", "Closed with non-monetary relief", "Closed with monetary relief"
    ])]
    model_df[TARGET] = model_df["company_response"].str.contains("relief", case=False).astype("int8")
    model_df = model_df.drop(columns="company_response")
    if len(model_df) > max_rows:
        model_df = model_df.sample(max_rows, random_state=RANDOM_STATE).reset_index(drop=True)
    return model_df


def train_model(source=PROCESSED_CSV, model_dir=MODEL_DIR, output_dir=OUTPUT_DIR) -> dict:
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}. Run: python -m cfri.pipeline")
    df = pd.read_csv(source, compression="gzip", low_memory=False)
    model_df = prepare_model_data(df)
    if model_df[TARGET].nunique() < 2:
        raise ValueError("Need at least two response classes with enough records")

    x_train, x_test, y_train, y_test = train_test_split(
        model_df[FEATURES], model_df[TARGET], test_size=0.20,
        random_state=RANDOM_STATE, stratify=model_df[TARGET],
    )
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", min_frequency=20)),
    ])
    pipeline = Pipeline([
        ("preprocess", ColumnTransformer([("categorical", categorical, FEATURES)])),
        ("classifier", LogisticRegression(max_iter=1_000, class_weight="balanced", solver="lbfgs")),
    ])
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    metrics = {
        "model": "one-hot encoded categorical features + class-weighted logistic regression",
        "purpose": "forecast whether a closed complaint receives monetary or non-monetary relief",
        "training_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "classes": 2,
        "positive_class": "closed with monetary or non-monetary relief",
        "positive_rate": round(float(model_df[TARGET].mean()), 4),
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions)), 4),
        "recall": round(float(recall_score(y_test, predictions)), 4),
        "f1": round(float(f1_score(y_test, predictions)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "random_state": RANDOM_STATE,
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_dir / "response_outcome_model.joblib")
    (output_dir / "model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame(report).T.to_csv(output_dir / "classification_report.csv")

    feature_names = pipeline.named_steps["preprocess"].get_feature_names_out()
    classifier = pipeline.named_steps["classifier"]
    top_rows = []
    coefficients = classifier.coef_[0]
    for direction, indices in [
        ("more associated with relief", coefficients.argsort()[-15:][::-1]),
        ("more associated with explanation only", coefficients.argsort()[:15]),
    ]:
        for index in indices:
            top_rows.append({
                "direction": direction,
                "feature": feature_names[index].replace("categorical__", ""),
                "coefficient": round(float(coefficients[index]), 4),
            })
    pd.DataFrame(top_rows).to_csv(output_dir / "top_model_features.csv", index=False)
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    train_model()
