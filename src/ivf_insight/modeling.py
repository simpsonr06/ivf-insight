from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder


def _build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    numeric = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("numeric", numeric_pipe, numeric),
        ("categorical", categorical_pipe, categorical),
    ], remainder="drop")


def train_and_evaluate(
    df: pd.DataFrame,
    target: str,
    output_dir: str | Path,
    drop_columns: list[str] | None = None,
    positive_label: str | None = None,
    random_state: int = 42,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if target not in df.columns:
        raise ValueError(f"Target '{target}' not found. Available columns: {list(df.columns)}")

    work = df.dropna(subset=[target]).copy()
    y_raw = work.pop(target)
    excluded = [c for c in (drop_columns or []) if c in work.columns]
    X = work.drop(columns=excluded)
    # Remove constant and entirely empty columns; these cannot contribute useful signal.
    X = X.dropna(axis=1, how="all")
    X = X.loc[:, X.nunique(dropna=True) > 1]
    if X.empty:
        raise ValueError("No usable predictor columns remain after exclusions.")
    if y_raw.nunique() != 2:
        raise ValueError(f"This baseline currently requires a binary target; found {y_raw.nunique()} classes.")

    # Explicitly map the requested positive class to 1. If omitted, use the second sorted class.
    labels = sorted(y_raw.astype(str).unique().tolist())
    pos = str(positive_label) if positive_label is not None else labels[-1]
    if pos not in labels:
        raise ValueError(f"Positive label '{pos}' not found in target values {labels}")
    y = (y_raw.astype(str) == pos).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=random_state, stratify=y
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    models = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, class_weight="balanced",
            random_state=random_state, n_jobs=-1,
        ),
    }
    scoring = {"roc_auc": "roc_auc", "f1": "f1", "balanced_accuracy": "balanced_accuracy"}
    results = {}
    best_name, best_score, best_pipeline = None, -np.inf, None

    for name, estimator in models.items():
        pipe = Pipeline([("preprocess", _build_preprocessor(X_train)), ("model", estimator)])
        cv_result = cross_validate(pipe, X_train, y_train, cv=cv, scoring=scoring, n_jobs=None)
        pipe.fit(X_train, y_train)
        probabilities = pipe.predict_proba(X_test)[:, 1]
        predictions = pipe.predict(X_test)
        metrics = {
            "cv_roc_auc_mean": float(np.mean(cv_result["test_roc_auc"])),
            "cv_roc_auc_std": float(np.std(cv_result["test_roc_auc"])),
            "cv_f1_mean": float(np.mean(cv_result["test_f1"])),
            "cv_balanced_accuracy_mean": float(np.mean(cv_result["test_balanced_accuracy"])),
            "test_roc_auc": float(roc_auc_score(y_test, probabilities)),
            "test_f1": float(f1_score(y_test, predictions, zero_division=0)),
            "test_precision": float(precision_score(y_test, predictions, zero_division=0)),
            "test_recall": float(recall_score(y_test, predictions, zero_division=0)),
            "test_balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
            "test_accuracy": float(accuracy_score(y_test, predictions)),
            "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
            "classification_report": classification_report(y_test, predictions, output_dict=True, zero_division=0),
        }
        results[name] = metrics
        if metrics["cv_roc_auc_mean"] > best_score:
            best_name, best_score, best_pipeline = name, metrics["cv_roc_auc_mean"], pipe

    joblib.dump(best_pipeline, output_dir / "best_model.joblib")
    summary = {
        "target": target,
        "positive_label_encoded_as_1": pos,
        "original_target_values": labels,
        "rows_used": int(len(work)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "predictors_used": X.columns.tolist(),
        "explicitly_dropped_columns": excluded,
        "selected_model_by_training_cv_roc_auc": best_name,
        "models": results,
        "warning": "Exploratory benchmark only. Not clinically validated; test performance is dataset/split-specific.",
    }
    (output_dir / "model_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
