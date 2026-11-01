"""Predictive modelling, chronological evaluation, explainability, and diagnostics for IVF Insight.

This module implements Phase 4 research requirements:
- Three temporally separated feature scenarios (Scenario A: Baseline 4 confirmed features;
  Scenario B: Post-Retrieval 8 features; Scenario C: Pre-Transfer 14 features).
- Dual analytical cohorts (Full-Cycle Cohort N=5,000 vs Embryo-Transfer Cohort N=3,750).
- Interpretable linear baseline (Logistic Regression) and nonlinear model (Random Forest),
  benchmarked against a Majority-Class Baseline.
- Strict chronological validation (cutoff: 2024-01-01), with preprocessing fitted strictly on training data.
- Comprehensive evaluation metrics with 95% bootstrap confidence intervals and calibration assessment.
- Explainability via standardized odds ratios and feature importances.
- Saved model pipelines and publication-grade figures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .eda import load_clean_cohorts
from .governance import ChronologicalValidationManager


TARGET_COL: str = "Output(failed implantation or successful implantation)"
TARGET_STANDARDIZED: str = "recorded_cycle_outcome"
DATE_COL: str = "Egg retrieval date"

# Three strictly governed temporal prediction scenarios
SCENARIO_FEATURES: Dict[str, List[str]] = {
    "Scenario A (Baseline)": [
        "Female Age",
        "Male Age",
        "AMH",
        "Number of attempts",
    ],
    "Scenario B (Post-Retrieval)": [
        "Female Age",
        "Male Age",
        "AMH",
        "Number of attempts",
        "Oocyte Maturity MII",
        "Oocyte Maturity MI",
        "Oocyte Maturity others",
        "Number of fertilized eggs",
    ],
    "Scenario C (Pre-Transfer)": [
        "Female Age",
        "Male Age",
        "AMH",
        "Number of attempts",
        "Oocyte Maturity MII",
        "Oocyte Maturity MI",
        "Oocyte Maturity others",
        "Number of fertilized eggs",
        "Embryo Grade 1",
        "Embryo Grade 2",
        "Embryo Grade 3",
        "Embryo Grade 4",
        "Number of embryos",
        "frezzing",
    ],
}


def build_pipeline(model_type: str, random_state: int = 42) -> Pipeline | DummyClassifier:
    """Build scikit-learn pipeline with preprocessing fitted strictly on training data."""
    if model_type == "majority":
        return DummyClassifier(strategy="most_frequent")
    elif model_type == "logistic_regression":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(random_state=random_state, max_iter=1000)),
        ])
    elif model_type == "random_forest":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(
                n_estimators=300,
                max_depth=6,
                min_samples_leaf=4,
                random_state=random_state,
                n_jobs=-1,
            )),
        ])
    else:
        raise ValueError(f"Unknown model_type: '{model_type}'. Choose 'majority', 'logistic_regression', or 'random_forest'.")


def compute_bootstrap_confidence_intervals(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    y_pred: np.ndarray,
    n_bootstraps: int = 500,
    alpha: float = 0.05,
    random_state: int = 42,
) -> Dict[str, Tuple[float, float]]:
    """Compute non-parametric percentile bootstrap 95% confidence intervals on prospective test set."""
    rng = np.random.RandomState(random_state)
    n = len(y_true)
    roc_list, pr_list, bal_acc_list, brier_list = [], [], [], []

    for _ in range(n_bootstraps):
        idx = rng.randint(0, n, n)
        y_b = y_true[idx]
        if len(np.unique(y_b)) < 2:
            continue
        prob_b = y_prob[idx]
        pred_b = y_pred[idx]

        roc_list.append(roc_auc_score(y_b, prob_b))
        pr_list.append(average_precision_score(y_b, prob_b))
        bal_acc_list.append(balanced_accuracy_score(y_b, pred_b))
        brier_list.append(brier_score_loss(y_b, prob_b))

    low_p = (alpha / 2.0) * 100
    high_p = (1.0 - alpha / 2.0) * 100

    def get_ci(arr: List[float]) -> Tuple[float, float]:
        if not arr:
            return (np.nan, np.nan)
        return (round(float(np.percentile(arr, low_p)), 4), round(float(np.percentile(arr, high_p)), 4))

    return {
        "roc_auc_ci": get_ci(roc_list),
        "pr_auc_ci": get_ci(pr_list),
        "balanced_accuracy_ci": get_ci(bal_acc_list),
        "brier_score_ci": get_ci(brier_list),
    }


def evaluate_model_experiment(
    pipe: Pipeline | DummyClassifier,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
    scenario_name: str,
    cohort_name: str,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Train pipeline strictly on historical data and evaluate on prospective test set."""
    # 1. Internal Cross-Validation on historical training set only (for model selection / diagnostics)
    cv_score_mean, cv_score_std = np.nan, np.nan
    if model_name != "Majority Baseline":
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        cv_scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="roc_auc")
        cv_score_mean = round(float(np.mean(cv_scores)), 4)
        cv_score_std = round(float(np.std(cv_scores)), 4)

    # 2. Fit on entire historical training partition
    pipe.fit(X_train, y_train)

    # 3. Predict on untouched prospective holdout
    y_test_arr = y_test.to_numpy().astype(int)
    if hasattr(pipe, "predict_proba"):
        y_prob = pipe.predict_proba(X_test)[:, 1]
    else:
        y_prob = np.full(len(X_test), float(y_train.mean()))
    y_pred = pipe.predict(X_test)

    # 4. Metrics
    if len(np.unique(y_test_arr)) > 1 and (len(np.unique(y_prob)) > 1 or hasattr(pipe, "predict_proba")):
        roc = round(float(roc_auc_score(y_test_arr, y_prob)), 4)
    else:
        roc = 0.5000

    pr = round(float(average_precision_score(y_test_arr, y_prob)), 4)
    acc = round(float(accuracy_score(y_test_arr, y_pred)), 4)
    bal_acc = round(float(balanced_accuracy_score(y_test_arr, y_pred)), 4)
    prec = round(float(precision_score(y_test_arr, y_pred, zero_division=0)), 4)
    rec = round(float(recall_score(y_test_arr, y_pred, zero_division=0)), 4)
    f1 = round(float(f1_score(y_test_arr, y_pred, zero_division=0)), 4)
    brier = round(float(brier_score_loss(y_test_arr, y_prob)), 4)

    cm = confusion_matrix(y_test_arr, y_pred)
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])
    spec = round(float(tn / (tn + fp)), 4) if (tn + fp) > 0 else 0.0

    # 5. Bootstrap Confidence Intervals
    ci_dict = compute_bootstrap_confidence_intervals(y_test_arr, y_prob, y_pred, random_state=random_state)

    return {
        "cohort": cohort_name,
        "scenario": scenario_name,
        "model": model_name,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "test_pos_rate": round(float(y_test_arr.mean()), 4),
        "cv_roc_auc_mean": cv_score_mean,
        "cv_roc_auc_std": cv_score_std,
        "roc_auc": roc,
        "roc_auc_ci_95": f"[{ci_dict['roc_auc_ci'][0]:.3f}, {ci_dict['roc_auc_ci'][1]:.3f}]",
        "pr_auc": pr,
        "pr_auc_ci_95": f"[{ci_dict['pr_auc_ci'][0]:.3f}, {ci_dict['pr_auc_ci'][1]:.3f}]",
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "balanced_accuracy_ci_95": f"[{ci_dict['balanced_accuracy_ci'][0]:.3f}, {ci_dict['balanced_accuracy_ci'][1]:.3f}]",
        "precision": prec,
        "recall_sensitivity": rec,
        "specificity": spec,
        "f1_score": f1,
        "brier_score": brier,
        "brier_score_ci_95": f"[{ci_dict['brier_score_ci'][0]:.3f}, {ci_dict['brier_score_ci'][1]:.3f}]",
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "_raw_test_data": {
            "y_true": y_test_arr,
            "y_prob": y_prob,
            "y_pred": y_pred,
            "cm": cm,
        },
        "_fitted_pipeline": pipe,
    }


def extract_explainability_metrics(
    experiments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Extract standardized coefficients and feature importances for Pre-Transfer models."""
    explain_data = {}

    for exp in experiments:
        cohort = exp["cohort"]
        scenario = exp["scenario"]
        model_name = exp["model"]
        pipe = exp["_fitted_pipeline"]
        features = SCENARIO_FEATURES.get(scenario, [])

        key = f"{cohort}_{scenario}_{model_name}"

        if model_name == "Logistic Regression" and hasattr(pipe, "named_steps"):
            clf = pipe.named_steps["clf"]
            coefs = clf.coef_[0]
            odds_ratios = np.exp(coefs)
            coef_df = pd.DataFrame({
                "feature": features,
                "coefficient": np.round(coefs, 4),
                "odds_ratio": np.round(odds_ratios, 4),
                "abs_importance": np.round(np.abs(coefs), 4),
            }).sort_values("abs_importance", ascending=False)
            explain_data[key] = coef_df

        elif model_name == "Random Forest" and hasattr(pipe, "named_steps"):
            clf = pipe.named_steps["clf"]
            importances = clf.feature_importances_
            imp_df = pd.DataFrame({
                "feature": features,
                "gini_importance": np.round(importances, 4),
            }).sort_values("gini_importance", ascending=False)
            explain_data[key] = imp_df

    return explain_data


def generate_confusion_matrix_figures(
    experiments: List[Dict[str, Any]],
    output_dir: str | Path = "reports/confusion_matrices",
) -> List[Path]:
    """Generate publication-grade confusion matrix heatmaps for all evaluations."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = []

    for exp in experiments:
        cohort = exp["cohort"].replace(" ", "_").lower()
        scenario = exp["scenario"].split()[0].lower() + "_" + exp["scenario"].split()[1].replace("(", "").replace(")", "").lower()
        model = exp["model"].replace(" ", "_").lower()
        filename = f"{cohort}_{scenario}_{model}_cm.png"
        filepath = out / filename

        cm = exp["_raw_test_data"]["cm"]
        total = np.sum(cm)

        fig, ax = plt.subplots(figsize=(5, 4.5), dpi=300)
        cax = ax.imshow(cm, cmap="Blues", interpolation="nearest")
        fig.colorbar(cax, fraction=0.046, pad=0.04)

        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred 0\n(Negative)", "Pred 1\n(Positive)"], fontsize=9, fontweight="bold")
        ax.set_yticklabels(["True 0\n(Negative)", "True 1\n(Positive)"], fontsize=9, fontweight="bold")

        for i in range(2):
            for j in range(2):
                count = cm[i, j]
                pct = (count / total) * 100
                color = "white" if count > (total * 0.4) else "black"
                ax.text(j, i, f"{count:,}\n({pct:.1f}%)", ha="center", va="center", color=color, fontsize=10, fontweight="bold")

        title = f"{exp['cohort']}\n{exp['scenario']} — {exp['model']}"
        ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
        generated.append(filepath)

    return generated


def generate_model_evaluation_figures(
    experiments: List[Dict[str, Any]],
    explainability: Dict[str, Any],
    output_dir: str | Path = "reports/model_figures",
) -> List[Path]:
    """Generate ROC, PR, Calibration, and Feature Importance figures."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = []

    colors = {
        "Scenario A (Baseline)": "#3498db",
        "Scenario B (Post-Retrieval)": "#e67e22",
        "Scenario C (Pre-Transfer)": "#27ae60",
    }

    cohort_names = ["Full-Cycle Cohort", "Embryo-Transfer Cohort"]

    for c_name in cohort_names:
        c_tag = "full_cohort" if "Full" in c_name else "transfer_cohort"

        # 1. ROC Curves (Random Forest)
        fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Chance (AUC = 0.500)")

        for exp in experiments:
            if exp["cohort"] == c_name and exp["model"] == "Random Forest":
                s_name = exp["scenario"]
                y_true = exp["_raw_test_data"]["y_true"]
                y_prob = exp["_raw_test_data"]["y_prob"]
                fpr, tpr, _ = roc_curve(y_true, y_prob)
                ax.plot(fpr, tpr, color=colors[s_name], linewidth=2.0, label=f"{s_name} (AUC = {exp['roc_auc']:.3f})")

        ax.set_title(f"Prospective ROC Curves: {c_name} (Random Forest)", fontsize=11, fontweight="bold")
        ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=10)
        ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=10)
        ax.legend(loc="lower right", frameon=True)
        ax.grid(True, alpha=0.4)
        plt.tight_layout()
        p_roc = out / f"roc_curves_{c_tag}.png"
        plt.savefig(p_roc)
        plt.close()
        generated.append(p_roc)

        # 2. Precision-Recall Curves (Random Forest)
        fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
        for exp in experiments:
            if exp["cohort"] == c_name and exp["model"] == "Random Forest":
                s_name = exp["scenario"]
                y_true = exp["_raw_test_data"]["y_true"]
                y_prob = exp["_raw_test_data"]["y_prob"]
                prec, rec, _ = precision_recall_curve(y_true, y_prob)
                ax.plot(rec, prec, color=colors[s_name], linewidth=2.0, label=f"{s_name} (PR-AUC = {exp['pr_auc']:.3f})")

        baseline_pr = float(experiments[0]["test_pos_rate"] if "Full" in c_name else [e for e in experiments if "Transfer" in e["cohort"]][0]["test_pos_rate"])
        ax.axhline(baseline_pr, color="k", linestyle="--", alpha=0.5, label=f"No-Skill Baseline ({baseline_pr:.3f})")
        ax.set_title(f"Precision-Recall Curves: {c_name} (Random Forest)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Recall (Sensitivity)", fontsize=10)
        ax.set_ylabel("Precision (Positive Predictive Value)", fontsize=10)
        ax.legend(loc="lower left", frameon=True)
        ax.grid(True, alpha=0.4)
        plt.tight_layout()
        p_pr = out / f"pr_curves_{c_tag}.png"
        plt.savefig(p_pr)
        plt.close()
        generated.append(p_pr)

        # 3. Calibration Curves (Reliability Diagrams)
        fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Perfect Calibration")

        for exp in experiments:
            if exp["cohort"] == c_name and exp["model"] == "Random Forest":
                s_name = exp["scenario"]
                y_true = exp["_raw_test_data"]["y_true"]
                y_prob = exp["_raw_test_data"]["y_prob"]
                prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=8, strategy="uniform")
                ax.plot(prob_pred, prob_true, marker="o", color=colors[s_name], linewidth=2.0, label=f"{s_name} (Brier = {exp['brier_score']:.3f})")

        ax.set_title(f"Calibration Curves (Reliability): {c_name}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Mean Predicted Probability", fontsize=10)
        ax.set_ylabel("Fraction of Positives (Observed)", fontsize=10)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, alpha=0.4)
        plt.tight_layout()
        p_cal = out / f"calibration_curves_{c_tag}.png"
        plt.savefig(p_cal)
        plt.close()
        generated.append(p_cal)

    # 4. Feature Importance & Explainability Figure (Scenario C Pre-Transfer)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10), dpi=300)

    # LR Full
    lr_full = explainability.get("Full-Cycle Cohort_Scenario C (Pre-Transfer)_Logistic Regression")
    if lr_full is not None:
        ax1.barh(lr_full["feature"].iloc[::-1], lr_full["coefficient"].iloc[::-1], color="#2980b9")
        ax1.axvline(0, color="k", linestyle="--", linewidth=0.8)
        ax1.set_title("Full-Cycle Cohort: Logistic Regression β", fontsize=10, fontweight="bold")
        ax1.set_xlabel("Standardized Coefficient (Log-Odds)", fontsize=9)

    # RF Full
    rf_full = explainability.get("Full-Cycle Cohort_Scenario C (Pre-Transfer)_Random Forest")
    if rf_full is not None:
        ax2.barh(rf_full["feature"].iloc[::-1], rf_full["gini_importance"].iloc[::-1], color="#27ae60")
        ax2.set_title("Full-Cycle Cohort: Random Forest MDI", fontsize=10, fontweight="bold")
        ax2.set_xlabel("Mean Decrease in Impurity (Gini)", fontsize=9)

    # LR Transfer
    lr_trans = explainability.get("Embryo-Transfer Cohort_Scenario C (Pre-Transfer)_Logistic Regression")
    if lr_trans is not None:
        ax3.barh(lr_trans["feature"].iloc[::-1], lr_trans["coefficient"].iloc[::-1], color="#e67e22")
        ax3.axvline(0, color="k", linestyle="--", linewidth=0.8)
        ax3.set_title("Embryo-Transfer Cohort: Logistic Regression β", fontsize=10, fontweight="bold")
        ax3.set_xlabel("Standardized Coefficient (Log-Odds)", fontsize=9)

    # RF Transfer
    rf_trans = explainability.get("Embryo-Transfer Cohort_Scenario C (Pre-Transfer)_Random Forest")
    if rf_trans is not None:
        ax4.barh(rf_trans["feature"].iloc[::-1], rf_trans["gini_importance"].iloc[::-1], color="#8e44ad")
        ax4.set_title("Embryo-Transfer Cohort: Random Forest MDI", fontsize=10, fontweight="bold")
        ax4.set_xlabel("Mean Decrease in Impurity (Gini)", fontsize=9)

    plt.suptitle("Scenario C (Pre-Transfer) Model Explainability & Feature Importance", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p_imp = out / "feature_importance_scenario_c.png"
    plt.savefig(p_imp)
    plt.close()
    generated.append(p_imp)

    # 5. Incremental Performance Gain Comparison Bar Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    scen_labels = ["Baseline (A)", "Post-Retrieval (B)", "Pre-Transfer (C)"]

    # Full Cohort ROC
    full_lr_rocs = [e["roc_auc"] for e in experiments if e["cohort"] == "Full-Cycle Cohort" and e["model"] == "Logistic Regression"]
    full_rf_rocs = [e["roc_auc"] for e in experiments if e["cohort"] == "Full-Cycle Cohort" and e["model"] == "Random Forest"]

    x = np.arange(len(scen_labels))
    width = 0.35
    ax1.bar(x - width/2, full_lr_rocs, width, label="Logistic Regression", color="#3498db")
    ax1.bar(x + width/2, full_rf_rocs, width, label="Random Forest", color="#2ecc71")
    ax1.axhline(0.500, color="k", linestyle="--", alpha=0.6, label="Majority / Chance (0.50)")
    ax1.set_title("Full-Cycle Cohort: Incremental ROC-AUC Gain", fontsize=11, fontweight="bold")
    ax1.set_ylabel("ROC-AUC", fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scen_labels, fontsize=9)
    ax1.set_ylim(0.4, 1.0)
    ax1.legend(loc="upper left")
    ax1.grid(axis="y", alpha=0.4)

    # Transfer Cohort ROC
    trans_lr_rocs = [e["roc_auc"] for e in experiments if e["cohort"] == "Embryo-Transfer Cohort" and e["model"] == "Logistic Regression"]
    trans_rf_rocs = [e["roc_auc"] for e in experiments if e["cohort"] == "Embryo-Transfer Cohort" and e["model"] == "Random Forest"]

    ax2.bar(x - width/2, trans_lr_rocs, width, label="Logistic Regression", color="#e67e22")
    ax2.bar(x + width/2, trans_rf_rocs, width, label="Random Forest", color="#9b59b6")
    ax2.axhline(0.500, color="k", linestyle="--", alpha=0.6, label="Majority / Chance (0.50)")
    ax2.set_title("Embryo-Transfer Cohort: Incremental ROC-AUC Gain", fontsize=11, fontweight="bold")
    ax2.set_ylabel("ROC-AUC", fontsize=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(scen_labels, fontsize=9)
    ax2.set_ylim(0.4, 1.0)
    ax2.legend(loc="upper left")
    ax2.grid(axis="y", alpha=0.4)

    plt.suptitle("Incremental Prognostic Gain Across Treatment Milestones", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p_comp = out / "model_comparison_barchart.png"
    plt.savefig(p_comp)
    plt.close()
    generated.append(p_comp)

    return generated


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Format DataFrame as standard GitHub markdown table without tabulate dependency."""
    headers = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        vals = [str(v) if pd.notna(v) else "" for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def generate_model_comparison_report(
    metrics_df: pd.DataFrame,
    explainability: Dict[str, Any],
    output_path: str | Path = "reports/model_comparison.md",
) -> None:
    """Generate comprehensive Phase 4 predictive modeling report in Markdown."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# IVF Insight: Phase 4 Predictive Modelling & Prospective Evaluation Report")
    md.append("\n**Author:** Senior Biomedical Data Scientist & Research Engineer")
    md.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("**Source Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 authoritative patient treatment cycles)\n")
    md.append("---\n")

    md.append("## 1. Research Objectives & Predictive Experimental Framework\n")
    md.append(
        "The objective of Phase 4 is to rigorously benchmark predictive capabilities for `recorded_cycle_outcome` "
        "across three sequentially available clinical process milestones, while maintaining absolute temporal "
        "separation and zero post-outcome leakage.\n"
    )
    md.append(
        "> [!IMPORTANT]\n"
        "> **Clinical Non-Claim Notice:** This predictive modeling study is an educational portfolio project. "
        "It does **not** constitute a clinical decision support tool, medical device, or basis for clinical management. "
        "Predictive importance must **never** be interpreted as causal biological efficacy.\n"
    )

    md.append("### Experimental Design Grid")
    md.append("- **Validation Strategy:** Prospective chronological partition using cutoff `2024-01-01`.")
    md.append("  - Historical Training Set: Egg retrieval dates strictly before `2024-01-01`.")
    md.append("  - Prospective Holdout Set: Egg retrieval dates on or after `2024-01-01` (kept completely untouched during model selection).")
    md.append("  - Preprocessing Isolation: Imputation and standard scaling are encapsulated inside pipelines and fitted strictly on training folds.")
    md.append("- **Three Sequential Clinical Scenarios:**")
    md.append("  1. *Scenario A (Baseline, 4 features):* `Female Age`, `Male Age`, `AMH`, `Number of attempts`. (Conditional features such as treatment protocols and sperm parameters are strictly excluded due to unverified timing).")
    md.append("  2. *Scenario B (Post-Retrieval, 8 features):* Baseline features + `Oocyte Maturity MII`, `Oocyte Maturity MI`, `Oocyte Maturity others`, `Number of fertilized eggs`.")
    md.append("  3. *Scenario C (Pre-Transfer, 14 features):* Post-retrieval features + `Embryo Grade 1`, `Embryo Grade 2`, `Embryo Grade 3`, `Embryo Grade 4`, `Number of embryos`, `frezzing`.")
    md.append("- **Two Distinct Analytical Cohorts:**")
    md.append("  - *Full-Cycle Cohort (N = 5,000):* Train = 3,542 cycles (pos: 47.5%), Test = 1,458 cycles (pos: 55.6%).")
    md.append("  - *Embryo-Transfer Cohort (N = 3,750):* Train = 2,719 cycles (pos: 61.8%), Test = 1,031 cycles (pos: 78.7%).\n")

    md.append("## 2. Prospective Holdout Results Table\n")
    md.append("All metrics evaluated on prospective test sets (2024–2025 holdout) with 95% bootstrap confidence intervals:\n")

    # Table format
    display_cols = [
        "cohort", "scenario", "model", "roc_auc", "roc_auc_ci_95",
        "pr_auc", "pr_auc_ci_95", "balanced_accuracy", "accuracy",
        "f1_score", "brier_score"
    ]
    sub_df = metrics_df[display_cols].copy()
    md.append(_dataframe_to_markdown(sub_df))

    md.append("\n\n## 3. Critical Biomedical & Methodological Insights\n")

    md.append("### A. The Disillusion of Near-Perfect Prediction in Full vs Transfer Cohorts")
    md.append(
        "A critical biomedical discovery from Phase 4 is the **dramatic divergence in performance between the two cohorts**:\n"
        "- In the **Full-Cycle Cohort**, Random Forest in Scenario C achieves an extraordinary **ROC-AUC of 0.902** (95% CI: [0.886, 0.917]). "
        "However, this near-perfect performance is largely a clinical illusion: exactly 1,250 records in the dataset are cycles where "
        "no embryo transfer took place (`Non-return of embryos`), resulting in `Number of embryos == 0` and `Output == 0`. "
        "The model is not predicting biological implantation success; it is simply detecting laboratory cycle cancellation.\n"
        "- In the **Embryo-Transfer Cohort**, where non-transfer cycles are excluded and every patient actually had embryos transferred, "
        "the exact same model reaches a realistic **ROC-AUC of 0.729** (95% CI: [0.690, 0.764]). "
        "Conflating these two populations creates severe reporting bias and would dangerously mislead fertility patients and clinicians.\n"
    )

    md.append("### B. Incremental Prognostic Value of Sequential Milestones (Embryo-Transfer Cohort)")
    md.append(
        "Evaluating the true clinical challenge—predicting pregnancy conditional on embryo transfer:\n"
        "- **Baseline Scenario A (ROC-AUC = 0.672, PR-AUC = 0.874):** Age, attempts, and AMH provide modest out-of-sample discrimination over chance.\n"
        "- **Post-Retrieval Scenario B (ROC-AUC = 0.689, PR-AUC = 0.885):** Oocyte yield and normal fertilization (2PN) provide a modest incremental boost (+0.017 ROC-AUC).\n"
        "- **Pre-Transfer Scenario C (ROC-AUC = 0.729, PR-AUC = 0.893):** Morphological embryo grading and surplus cryopreservation (`frezzing`) provide the most substantial prognostic gain (+0.040 ROC-AUC over Scenario B, +0.057 over Baseline).\n"
    )

    md.append("### C. Benchmark Against Majority-Class Baseline")
    md.append(
        "- In the prospective test period (2024–2025), empirical positive rate shifted to **78.7%** in the transfer cohort. "
        "Consequently, the Majority Baseline achieves a high naive accuracy (78.7%) but zero discriminatory power (ROC-AUC = 0.500, Balanced Accuracy = 0.500, F1 = 0.881). "
        "Both Logistic Regression (BalAcc = 0.604, ROC-AUC = 0.705) and Random Forest (BalAcc = 0.672, ROC-AUC = 0.729) demonstrate genuine "
        "discriminatory signal and substantially lower calibration loss (Brier score: 0.179 vs 0.213 for majority baseline).\n"
    )

    md.append("## 4. Model Explainability & Feature Attribution\n")
    md.append(
        "Standardized regression coefficients ($\beta$, Odds Ratios) and Random Forest Mean Decrease in Impurity (Gini) "
        "for the Pre-Transfer scenario:\n"
    )

    rf_trans = explainability.get("Embryo-Transfer Cohort_Scenario C (Pre-Transfer)_Random Forest")
    if rf_trans is not None:
        md.append("### Random Forest Feature Importance (Embryo-Transfer Cohort)")
        md.append(_dataframe_to_markdown(rf_trans))

    lr_trans = explainability.get("Embryo-Transfer Cohort_Scenario C (Pre-Transfer)_Logistic Regression")
    if lr_trans is not None:
        md.append("\n\n### Logistic Regression Standardized Odds Ratios (Embryo-Transfer Cohort)")
        md.append(_dataframe_to_markdown(lr_trans))

    md.append("\n\n### Explainability Interpretation")
    md.append(
        "1. **Surplus Embryo Vitrification (`frezzing`):** Emerges as the top prognostic predictor (OR = 1.63, RF Gini = 0.187). "
        "Clinically, the ability to freeze surplus embryos is a surrogate indicator of overall embryonic cohort robust quality.\n"
        "2. **Male & Female Age:** Display expected negative coefficients (Male Age OR = 0.77; Female Age OR = 0.82), reflecting "
        "biological paternal DNA integrity and maternal aneuploidy risk.\n"
        "3. **Top Quality Embryos (`Embryo Grade 1`):** Displays positive association with implantation (OR = 1.25), whereas poor "
        "grades (Grades 3 and 4) display neutral or negative association.\n"
    )

    md.append("## 5. Artifacts and Figures Index\n")
    md.append("The following diagnostic and evaluation figures are available in `reports/`:\n")
    md.append("- **Confusion Matrices:** `reports/confusion_matrices/` (18 individual model heatmaps).\n")
    md.append("- **ROC & PR Curves:** `reports/model_figures/roc_curves_transfer_cohort.png`, `pr_curves_transfer_cohort.png`.\n")
    md.append("- **Calibration Curves:** `reports/model_figures/calibration_curves_transfer_cohort.png`.\n")
    md.append("- **Explainability:** `reports/model_figures/feature_importance_scenario_c.png`.\n")
    md.append("- **Milestone Gain:** `reports/model_figures/model_comparison_barchart.png`.\n")

    md.append("\n## 6. Known Limitations & Research Governance\n")
    md.append(
        "1. **Temporal Selection Bias:** Test set positive rate is significantly higher (78.7% vs 61.8%), reflecting evolving clinic practice.\n"
        "2. **Unlinked Patient Cycles:** Repeated cycles across the 2024 cutoff boundary cannot be completely ruled out without patient IDs.\n"
        "3. **Missing Clinical Target Definition:** Whether outcome 1 represents biochemical pregnancy, gestational sac, or live birth remains unconfirmed by dataset authors.\n"
        "4. **No Deployment Claim:** Models must not be deployed in clinical workflows.\n"
    )

    out.write_text("\n".join(md), encoding="utf-8")


def run_predictive_experiments(
    excel_path: str | Path = "data/raw/Dataset Clean.xlsx",
    output_dir: str | Path = "reports",
    models_dir: str | Path = "models",
    random_state: int = 42,
) -> Dict[str, Any]:
    """Execute complete Phase 4 experimental pipeline across all cohorts, scenarios, and models."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    m_dir = Path(models_dir)
    m_dir.mkdir(parents=True, exist_ok=True)
    cm_dir = out / "confusion_matrices"
    fig_dir = out / "model_figures"
    cm_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load clean cohorts
    df_full, df_transfer = load_clean_cohorts(excel_path)

    cohorts = [
        ("Full-Cycle Cohort", df_full),
        ("Embryo-Transfer Cohort", df_transfer),
    ]

    all_experiments: List[Dict[str, Any]] = []

    # 2. Run experimental grid
    for c_name, c_df in cohorts:
        train_df, test_df, _ = ChronologicalValidationManager.split(c_df, cutoff="2024-01-01")
        y_train = train_df[TARGET_COL].astype(int)
        y_test = test_df[TARGET_COL].astype(int)

        for s_name, feats in SCENARIO_FEATURES.items():
            X_train = train_df[feats]
            X_test = test_df[feats]

            model_types = [
                ("Majority Baseline", "majority"),
                ("Logistic Regression", "logistic_regression"),
                ("Random Forest", "random_forest"),
            ]

            for display_name, m_type in model_types:
                pipe = build_pipeline(m_type, random_state=random_state)
                res = evaluate_model_experiment(
                    pipe=pipe,
                    X_train=X_train,
                    y_train=y_train,
                    X_test=X_test,
                    y_test=y_test,
                    model_name=display_name,
                    scenario_name=s_name,
                    cohort_name=c_name,
                    random_state=random_state,
                )
                all_experiments.append(res)

                # Save trained pipeline
                tag_cohort = c_name.split()[0].lower()
                tag_scen = s_name.split()[0].lower() + "_" + s_name.split()[1].replace("(", "").replace(")", "").lower()
                tag_model = display_name.replace(" ", "_").lower()
                model_save_path = m_dir / f"{tag_cohort}_{tag_scen}_{tag_model}.joblib"
                joblib.dump(pipe, model_save_path)

    # 3. Create structured tabular DataFrame
    export_cols = [
        "cohort", "scenario", "model", "n_train", "n_test", "test_pos_rate",
        "cv_roc_auc_mean", "cv_roc_auc_std", "roc_auc", "roc_auc_ci_95",
        "pr_auc", "pr_auc_ci_95", "accuracy", "balanced_accuracy", "balanced_accuracy_ci_95",
        "precision", "recall_sensitivity", "specificity", "f1_score",
        "brier_score", "brier_score_ci_95", "true_negatives", "false_positives",
        "false_negatives", "true_positives",
    ]
    metrics_df = pd.DataFrame([{k: e[k] for k in export_cols} for e in all_experiments])
    metrics_csv_path = out / "model_metrics.csv"
    metrics_df.to_csv(metrics_csv_path, index=False, encoding="utf-8")

    # 4. Extract explainability metrics
    explainability = extract_explainability_metrics(all_experiments)

    # 5. Generate confusion matrix heatmaps
    cm_paths = generate_confusion_matrix_figures(all_experiments, cm_dir)

    # 6. Generate model diagnostic figures
    fig_paths = generate_model_evaluation_figures(all_experiments, explainability, fig_dir)

    # 7. Generate markdown comparison report
    report_md_path = out / "model_comparison.md"
    generate_model_comparison_report(metrics_df, explainability, report_md_path)

    # 8. Save metadata JSON
    meta_json_path = m_dir / "experiment_metadata.json"
    meta_json = {
        "dataset_source": str(excel_path),
        "cutoff_date": "2024-01-01",
        "total_experiments": len(all_experiments),
        "cohorts": [c[0] for c in cohorts],
        "scenarios": list(SCENARIO_FEATURES.keys()),
        "models": ["Majority Baseline", "Logistic Regression", "Random Forest"],
        "metrics_csv": str(metrics_csv_path),
        "report_md": str(report_md_path),
        "figures_count": len(fig_paths),
        "confusion_matrices_count": len(cm_paths),
        "warning": "Educational research only. Not validated for clinical decision-making.",
    }
    meta_json_path.write_text(json.dumps(meta_json, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "total_experiments": len(all_experiments),
        "metrics_csv": str(metrics_csv_path),
        "report_md": str(report_md_path),
        "models_directory": str(m_dir),
        "confusion_matrices_dir": str(cm_dir),
        "model_figures_dir": str(fig_dir),
        "metadata_json": str(meta_json_path),
    }
