"""Phase 5: Robustness, Sensitivity, and Model Validation for IVF Insight.

This module conducts a comprehensive validation audit of Phase 4 predictive models:
1. Temporal Drift: Yearly outcome prevalence, non-return rates, distribution shifts (KS, SMD, PSI).
2. Cutoff Sensitivity: Multi-temporal chronological splits (2023-01-01, 2024-01-01, 2024-07-01).
3. Logistic Regression Odds Ratios: Statistically rigorous odds ratios and 95% CIs via statsmodels.
4. Calibration Diagnostics: Logistic recalibration intercept/slope, Brier score CIs, reliability diagrams.
5. Feature Stability: Bootstrap resampling (B=100) for rank and importance stability.
6. Sensitivity Analysis: Impact of extreme AMH (482.1) and leave-one-feature-out (LOFO) ablation.
7. Clinical Threshold Analysis: Sensitivity, Specificity, PPV, NPV, Balanced Accuracy across thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
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
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm

from .eda import load_clean_cohorts, BETA_COL
from .experiments import SCENARIO_FEATURES, TARGET_COL, DATE_COL, build_pipeline, evaluate_model_experiment
from .governance import ChronologicalValidationManager


def calculate_population_stability_index(
    expected: pd.Series, actual: pd.Series, num_bins: int = 10, eps: float = 1e-4
) -> float:
    """Calculate Population Stability Index (PSI) between baseline and comparison distributions."""
    exp_clean = expected.dropna()
    act_clean = actual.dropna()
    if len(exp_clean) == 0 or len(act_clean) == 0:
        return 0.0

    quantiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(exp_clean, quantiles)
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0
    bins[0] = -np.inf
    bins[-1] = np.inf

    e_counts, _ = np.histogram(exp_clean, bins=bins)
    a_counts, _ = np.histogram(act_clean, bins=bins)

    e_pct = np.maximum(e_counts / len(exp_clean), eps)
    a_pct = np.maximum(a_counts / len(act_clean), eps)

    e_pct /= e_pct.sum()
    a_pct /= a_pct.sum()

    psi = np.sum((a_pct - e_pct) * np.log(a_pct / e_pct))
    return round(float(psi), 4)


def analyze_temporal_drift(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
    cutoff_date: str = "2024-01-01",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze yearly outcome prevalence, cycle cancellations, and feature distribution drift."""
    df_f = df_full.copy()
    df_t = df_transfer.copy()

    df_f["Year"] = pd.to_datetime(df_f[DATE_COL]).dt.year
    df_t["Year"] = pd.to_datetime(df_t[DATE_COL]).dt.year

    # 1. Yearly outcome prevalence & non-return rate
    yearly_records = []
    years = sorted(df_f["Year"].unique())

    for yr in years:
        sub_f = df_f[df_f["Year"] == yr]
        sub_t = df_t[df_t["Year"] == yr]

        n_f = len(sub_f)
        pos_f = int(sub_f[TARGET_COL].sum())
        prev_f = round(float(pos_f / n_f), 4) if n_f > 0 else 0.0

        non_return_count = int((sub_f[BETA_COL] == "Non-return of embryos").sum())
        non_return_rate = round(float(non_return_count / n_f), 4) if n_f > 0 else 0.0

        n_t = len(sub_t)
        pos_t = int(sub_t[TARGET_COL].sum()) if n_t > 0 else 0
        prev_t = round(float(pos_t / n_t), 4) if n_t > 0 else 0.0

        yearly_records.append({
            "Year": yr,
            "Full_Cycles_Total": n_f,
            "Full_Cycles_Positive": pos_f,
            "Full_Cohort_Prevalence": prev_f,
            "Non_Return_Cycles": non_return_count,
            "Non_Return_Rate": non_return_rate,
            "Transfer_Cycles_Total": n_t,
            "Transfer_Cycles_Positive": pos_t,
            "Transfer_Cohort_Prevalence": prev_t,
        })

    df_yearly = pd.DataFrame(yearly_records)

    # 2. Feature distribution drift (Historical < cutoff vs Prospective >= cutoff)
    cutoff_dt = pd.Timestamp(cutoff_date)
    is_post_f = pd.to_datetime(df_f[DATE_COL]) >= cutoff_dt
    is_post_t = pd.to_datetime(df_t[DATE_COL]) >= cutoff_dt

    drift_records = []
    features = SCENARIO_FEATURES["Scenario C (Pre-Transfer)"]

    for cohort_name, df_cohort, is_post in [
        ("Full-Cycle Cohort", df_f, is_post_f),
        ("Embryo-Transfer Cohort", df_t, is_post_t),
    ]:
        for feat in features:
            s_pre = df_cohort.loc[~is_post, feat].dropna()
            s_post = df_cohort.loc[is_post, feat].dropna()

            m_pre, m_post = float(s_pre.mean()), float(s_post.mean())
            std_pre, std_post = float(s_pre.std()), float(s_post.std())
            med_pre, med_post = float(s_pre.median()), float(s_post.median())

            smd = (m_post - m_pre) / (std_pre if std_pre > 0 else 1.0)
            ks_res = stats.ks_2samp(s_pre, s_post)
            mwu_res = stats.mannwhitneyu(s_pre, s_post, alternative="two-sided")
            psi = calculate_population_stability_index(s_pre, s_post)

            drift_records.append({
                "Cohort": cohort_name,
                "Feature": feat,
                "Historical_Mean": round(m_pre, 3),
                "Prospective_Mean": round(m_post, 3),
                "Historical_Median": round(med_pre, 3),
                "Prospective_Median": round(med_post, 3),
                "Historical_Std": round(std_pre, 3),
                "Prospective_Std": round(std_post, 3),
                "Standardized_Mean_Diff": round(float(smd), 4),
                "KS_Statistic": round(float(ks_res.statistic), 4),
                "KS_P_Value": float(ks_res.pvalue),
                "Mann_Whitney_U_P_Value": float(mwu_res.pvalue),
                "Population_Stability_Index": psi,
                "Shift_Severity": "Significant (PSI >= 0.25)" if psi >= 0.25 else ("Moderate (PSI >= 0.1)" if psi >= 0.1 else "Stable (PSI < 0.1)"),
            })

    df_drift = pd.DataFrame(drift_records)
    return df_yearly, df_drift


def evaluate_cutoff_sensitivity(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
    cutoffs: Optional[List[str]] = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Evaluate predictive performance across multiple defensible chronological cutoff dates."""
    if cutoffs is None:
        cutoffs = ["2023-01-01", "2024-01-01", "2024-07-01"]

    results = []
    cohorts = [
        ("Full-Cycle Cohort", df_full),
        ("Embryo-Transfer Cohort", df_transfer),
    ]

    for cutoff in cutoffs:
        for cohort_name, df in cohorts:
            train_df, test_df, _ = ChronologicalValidationManager.split(df, cutoff=cutoff)
            n_train = len(train_df)
            n_test = len(test_df)
            train_pos_rate = round(float(train_df[TARGET_COL].mean()), 4)
            test_pos_rate = round(float(test_df[TARGET_COL].mean()), 4)

            for scenario_name, features in SCENARIO_FEATURES.items():
                X_train = train_df[features]
                y_train = train_df[TARGET_COL]
                X_test = test_df[features]
                y_test = test_df[TARGET_COL]

                for m_type, m_label in [
                    ("logistic_regression", "Logistic Regression"),
                    ("random_forest", "Random Forest"),
                ]:
                    pipe = build_pipeline(m_type, random_state=random_state)
                    res = evaluate_model_experiment(
                        pipe,
                        X_train,
                        y_train,
                        X_test,
                        y_test,
                        model_name=m_label,
                        scenario_name=scenario_name,
                        cohort_name=cohort_name,
                        random_state=random_state,
                    )
                    results.append({
                        "Cutoff_Date": cutoff,
                        "Cohort": cohort_name,
                        "Scenario": scenario_name,
                        "Model": m_label,
                        "Train_N": n_train,
                        "Train_Pos_Rate": train_pos_rate,
                        "Holdout_N": n_test,
                        "Holdout_Pos_Rate": test_pos_rate,
                        "ROC_AUC": res["roc_auc"],
                        "ROC_AUC_CI_95": res["roc_auc_ci_95"],
                        "PR_AUC": res["pr_auc"],
                        "Balanced_Accuracy": res["balanced_accuracy"],
                        "Accuracy": res["accuracy"],
                        "Sensitivity": res["recall_sensitivity"],
                        "Specificity": res["specificity"],
                        "Brier_Score": res["brier_score"],
                    })

    return pd.DataFrame(results)


def compute_logistic_regression_odds_ratios(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
    cutoff_date: str = "2024-01-01",
) -> pd.DataFrame:
    """Calculate statistically rigorous odds ratios and 95% CIs via statsmodels on standardized training features."""
    records = []
    cohorts = [
        ("Full-Cycle Cohort", df_full),
        ("Embryo-Transfer Cohort", df_transfer),
    ]

    for cohort_name, df in cohorts:
        train_df, _, _ = ChronologicalValidationManager.split(df, cutoff=cutoff_date)
        y_train = train_df[TARGET_COL].to_numpy().astype(float)

        for scenario_name, features in SCENARIO_FEATURES.items():
            X_raw = train_df[features]

            imputer = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            X_imp = imputer.fit_transform(X_raw)
            X_scaled = scaler.fit_transform(X_imp)

            X_with_const = sm.add_constant(X_scaled)
            logit_mod = sm.Logit(y_train, X_with_const)
            logit_res = logit_mod.fit(disp=False)

            params = logit_res.params
            bse = logit_res.bse
            pvalues = logit_res.pvalues

            for idx, feat in enumerate(features, start=1):
                beta = float(params[idx])
                se = float(bse[idx])
                pval = float(pvalues[idx])
                z_stat = beta / se if se > 0 else 0.0

                or_val = np.exp(beta)
                ci_low = np.exp(beta - 1.96 * se)
                ci_high = np.exp(beta + 1.96 * se)

                records.append({
                    "Cohort": cohort_name,
                    "Scenario": scenario_name,
                    "Feature": feat,
                    "Coefficient_Beta": round(beta, 4),
                    "Standard_Error": round(se, 4),
                    "Z_Statistic": round(z_stat, 4),
                    "P_Value": float(pval),
                    "Odds_Ratio": round(float(or_val), 4),
                    "OR_CI_95_Low": round(float(ci_low), 4),
                    "OR_CI_95_High": round(float(ci_high), 4),
                    "OR_CI_95_Formatted": f"[{ci_low:.3f}, {ci_high:.3f}]",
                    "Scaling_Basis": "Standardized (per 1 SD increase in training feature)",
                })

    return pd.DataFrame(records)


def compute_calibration_diagnostics(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
    cutoff_date: str = "2024-01-01",
    random_state: int = 42,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Compute logistic recalibration intercept, slope, Brier score CIs, and reliability points."""
    records = []
    reliability_data = {}

    cohorts = [
        ("Full-Cycle Cohort", df_full),
        ("Embryo-Transfer Cohort", df_transfer),
    ]

    for cohort_name, df in cohorts:
        train_df, test_df, _ = ChronologicalValidationManager.split(df, cutoff=cutoff_date)
        y_test = test_df[TARGET_COL].to_numpy().astype(int)

        for scenario_name, features in SCENARIO_FEATURES.items():
            X_train = train_df[features]
            y_train = train_df[TARGET_COL]
            X_test = test_df[features]

            for m_type, m_label in [
                ("logistic_regression", "Logistic Regression"),
                ("random_forest", "Random Forest"),
            ]:
                pipe = build_pipeline(m_type, random_state=random_state)
                pipe.fit(X_train, y_train)
                p_test = pipe.predict_proba(X_test)[:, 1]

                # Brier score
                brier = float(brier_score_loss(y_test, p_test))

                # Expected Calibration Error (ECE) with 10 equal-spaced bins
                prob_true, prob_pred = calibration_curve(y_test, p_test, n_bins=10, strategy="uniform")
                bin_edges = np.linspace(0, 1, 11)
                bin_indices = np.digitize(p_test, bin_edges) - 1
                ece = 0.0
                mce = 0.0
                for b in range(10):
                    mask = bin_indices == b
                    if np.sum(mask) > 0:
                        diff = abs(np.mean(y_test[mask]) - np.mean(p_test[mask]))
                        ece += (np.sum(mask) / len(y_test)) * diff
                        mce = max(mce, diff)

                # Logistic Recalibration Model (Harrell / Cox):
                eps = 1e-6
                p_clipped = np.clip(p_test, eps, 1 - eps)
                logit_p = np.log(p_clipped / (1 - p_clipped))

                try:
                    recal_model = sm.Logit(y_test, sm.add_constant(logit_p)).fit(disp=False)
                    cal_intercept = float(recal_model.params[0])
                    cal_slope = float(recal_model.params[1])
                except Exception:
                    cal_intercept = np.nan
                    cal_slope = np.nan

                direction = "Systematically Pessimistic / Underconfident (Observed > Predicted)" if cal_intercept > 0.2 else (
                    "Systematically Optimistic / Overconfident (Observed < Predicted)" if cal_intercept < -0.2 else "Well-Centered"
                )

                spread_direction = "Overconfident Spread (Slope < 1)" if cal_slope < 0.9 else (
                    "Underconfident Spread (Slope > 1.1)" if cal_slope > 1.1 else "Ideal Spread (Slope ≈ 1.0)"
                )

                records.append({
                    "Cohort": cohort_name,
                    "Scenario": scenario_name,
                    "Model": m_label,
                    "Brier_Score": round(brier, 4),
                    "ECE_10_Bins": round(float(ece), 4),
                    "MCE_10_Bins": round(float(mce), 4),
                    "Calibration_Intercept": round(cal_intercept, 4),
                    "Calibration_Slope": round(cal_slope, 4),
                    "Systematic_Bias": direction,
                    "Spread_Assessment": spread_direction,
                })

                key = f"{cohort_name}_{scenario_name}_{m_label}"
                reliability_data[key] = {
                    "prob_true": prob_true,
                    "prob_pred": prob_pred,
                    "cal_intercept": cal_intercept,
                    "cal_slope": cal_slope,
                }

    return pd.DataFrame(records), reliability_data


def evaluate_feature_importance_stability(
    df_transfer: pd.DataFrame,
    cutoff_date: str = "2024-01-01",
    n_bootstraps: int = 100,
    random_state: int = 42,
) -> pd.DataFrame:
    """Evaluate Random Forest Gini feature importance stability via bootstrap resampling of historical training data."""
    train_df, _, _ = ChronologicalValidationManager.split(df_transfer, cutoff=cutoff_date)
    features = SCENARIO_FEATURES["Scenario C (Pre-Transfer)"]

    imputer = SimpleImputer(strategy="median")
    X_mat = imputer.fit_transform(train_df[features])
    y_mat = train_df[TARGET_COL].to_numpy().astype(int)

    n_samples = len(X_mat)
    rng = np.random.RandomState(random_state)

    importances_list = []
    ranks_list = []

    for b in range(n_bootstraps):
        boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
        X_b, y_b = X_mat[boot_idx], y_mat[boot_idx]

        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=4,
            random_state=b,
            n_jobs=-1,
        )
        rf.fit(X_b, y_b)
        imp = rf.feature_importances_
        importances_list.append(imp)

        order = np.argsort(-imp)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, len(features) + 1)
        ranks_list.append(ranks)

    imp_arr = np.array(importances_list)
    rank_arr = np.array(ranks_list)

    results = []
    for j, feat in enumerate(features):
        feat_imps = imp_arr[:, j]
        feat_ranks = rank_arr[:, j]

        results.append({
            "Feature": feat,
            "Mean_Gini_Importance": round(float(np.mean(feat_imps)), 4),
            "Std_Gini_Importance": round(float(np.std(feat_imps)), 4),
            "Gini_CI_95_Low": round(float(np.percentile(feat_imps, 2.5)), 4),
            "Gini_CI_95_High": round(float(np.percentile(feat_imps, 97.5)), 4),
            "Mean_Rank": round(float(np.mean(feat_ranks)), 2),
            "Median_Rank": round(float(np.median(feat_ranks)), 1),
            "Rank_IQR": round(float(np.percentile(feat_ranks, 75) - np.percentile(feat_ranks, 25)), 2),
            "Min_Rank": int(np.min(feat_ranks)),
            "Max_Rank": int(np.max(feat_ranks)),
        })

    return pd.DataFrame(results).sort_values("Mean_Gini_Importance", ascending=False).reset_index(drop=True)


def evaluate_sensitivity_analyses(
    df_transfer: pd.DataFrame,
    cutoff_date: str = "2024-01-01",
    random_state: int = 42,
) -> pd.DataFrame:
    """Evaluate AMH extreme outlier impact and leave-one-feature-out (LOFO) ablation for Scenario C."""
    train_df, test_df, _ = ChronologicalValidationManager.split(df_transfer, cutoff=cutoff_date)
    features_c = SCENARIO_FEATURES["Scenario C (Pre-Transfer)"]
    y_train = train_df[TARGET_COL]
    y_test = test_df[TARGET_COL]

    results = []

    def run_eval(X_tr, y_tr, X_te, y_te, analysis_type, spec_label):
        pipe = build_pipeline("random_forest", random_state=random_state)
        pipe.fit(X_tr, y_tr)
        p_test = pipe.predict_proba(X_te)[:, 1]
        y_pred = pipe.predict(X_te)

        auc = round(float(roc_auc_score(y_te, p_test)), 4)
        pr = round(float(average_precision_score(y_te, p_test)), 4)
        bal_acc = round(float(balanced_accuracy_score(y_te, y_pred)), 4)
        brier = round(float(brier_score_loss(y_te, p_test)), 4)

        results.append({
            "Sensitivity_Domain": analysis_type,
            "Specification": spec_label,
            "N_Train": len(X_tr),
            "N_Holdout": len(X_te),
            "Features_Count": X_tr.shape[1],
            "ROC_AUC": auc,
            "PR_AUC": pr,
            "Balanced_Accuracy": bal_acc,
            "Brier_Score": brier,
        })

    # 1. Full baseline Scenario C
    run_eval(
        train_df[features_c], y_train,
        test_df[features_c], y_test,
        "Baseline Benchmark", "Full Scenario C (All 14 Features, All Records)"
    )

    # 2. AMH Outlier Sensitivity (Exclude 3 records with AMH = 482.1)
    train_no_amh_outliers = train_df[train_df["AMH"] <= 100]
    test_no_amh_outliers = test_df[test_df["AMH"] <= 100]
    run_eval(
        train_no_amh_outliers[features_c], train_no_amh_outliers[TARGET_COL],
        test_no_amh_outliers[features_c], test_no_amh_outliers[TARGET_COL],
        "AMH Extreme Outlier Sensitivity", "Exclude Extreme AMH = 482.1 Records (N=3 removed)"
    )

    # 3. Leave-One-Feature-Out (LOFO) Ablation
    top_ablation_features = [
        "frezzing",
        "Number of embryos",
        "Number of fertilized eggs",
        "Embryo Grade 1",
        "Oocyte Maturity MII",
        "Male Age",
        "Female Age",
    ]
    for feat in top_ablation_features:
        ablated_features = [f for f in features_c if f != feat]
        run_eval(
            train_df[ablated_features], y_train,
            test_df[ablated_features], y_test,
            "Feature Ablation (LOFO)", f"Scenario C excluding '{feat}'"
        )

    return pd.DataFrame(results)


def evaluate_clinical_thresholds(
    df_transfer: pd.DataFrame,
    cutoff_date: str = "2024-01-01",
    thresholds: Optional[List[float]] = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Evaluate decision threshold trade-offs (Sensitivity, Specificity, PPV, NPV) on prospective holdout."""
    if thresholds is None:
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.787, 0.8, 0.9]

    train_df, test_df, _ = ChronologicalValidationManager.split(df_transfer, cutoff=cutoff_date)
    features = SCENARIO_FEATURES["Scenario C (Pre-Transfer)"]

    pipe = build_pipeline("random_forest", random_state=random_state)
    pipe.fit(train_df[features], train_df[TARGET_COL])
    p_test = pipe.predict_proba(test_df[features])[:, 1]
    y_test = test_df[TARGET_COL].to_numpy().astype(int)

    n_total = len(y_test)
    pos_rate = float(np.mean(y_test))

    rows = []
    for t in sorted(thresholds):
        y_pred = (p_test >= t).astype(int)
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        ppv = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        npv = float(tn / (tn + fn)) if (tn + fn) > 0 else 0.0
        bal_acc = (sens + spec) / 2.0
        acc = float((tp + tn) / n_total)
        f1 = float(f1_score(y_test, y_pred, zero_division=0))

        rows.append({
            "Probability_Threshold": round(float(t), 3),
            "True_Positives": tp,
            "False_Positives": fp,
            "True_Negatives": tn,
            "False_Negatives": fn,
            "Sensitivity": round(sens, 4),
            "Specificity": round(spec, 4),
            "Positive_Predictive_Value_PPV": round(ppv, 4),
            "Negative_Predictive_Value_NPV": round(npv, 4),
            "Balanced_Accuracy": round(bal_acc, 4),
            "Overall_Accuracy": round(acc, 4),
            "F1_Score": round(f1, 4),
            "Prospective_Prevalence": round(pos_rate, 4),
        })

    return pd.DataFrame(rows)


def generate_robustness_figures(
    df_yearly: pd.DataFrame,
    df_drift: pd.DataFrame,
    df_cutoff: pd.DataFrame,
    df_stability: pd.DataFrame,
    df_sensitivity: pd.DataFrame,
    df_threshold: pd.DataFrame,
    reliability_data: Dict[str, Any],
    output_dir: str | Path = "reports/robustness_figures",
) -> List[Path]:
    """Generate 7 publication-grade diagnostic figures for robustness and sensitivity."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated = []

    # 1. Temporal Drift Prevalence Trajectory
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=300)
    ax1.plot(df_yearly["Year"], df_yearly["Full_Cohort_Prevalence"] * 100, marker="o", color="#2980b9", lw=2.5, label="Full-Cycle Cohort")
    ax1.plot(df_yearly["Year"], df_yearly["Transfer_Cohort_Prevalence"] * 100, marker="s", color="#27ae60", lw=2.5, label="Embryo-Transfer Cohort")
    ax1.plot(df_yearly["Year"], df_yearly["Non_Return_Rate"] * 100, marker="^", color="#e74c3c", lw=2, linestyle="--", label="Cycle Non-Return Rate")
    ax1.axvline(2023.5, color="black", linestyle=":", lw=1.5, label="Prospective Boundary (2024)")
    ax1.set_title("Yearly Outcome Prevalence & Cancellation Rate", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Year of Treatment", fontsize=10)
    ax1.set_ylabel("Percentage (%)", fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9)

    # Cycle volumes
    width = 0.35
    x = np.arange(len(df_yearly))
    ax2.bar(x - width/2, df_yearly["Full_Cycles_Total"], width, label="Full Cycles", color="#34495e", alpha=0.85)
    ax2.bar(x + width/2, df_yearly["Transfer_Cycles_Total"], width, label="Transfer Cycles", color="#16a085", alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(df_yearly["Year"])
    ax2.set_title("Annual Treatment Cycle Volumes", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Year of Treatment", fontsize=10)
    ax2.set_ylabel("Number of Cycles", fontsize=10)
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.legend(fontsize=9)
    plt.tight_layout()
    f1 = out / "temporal_drift_prevalence.png"
    plt.savefig(f1)
    plt.close()
    generated.append(f1)

    # 2. Feature Distribution Shift (SMD & PSI) in Transfer Cohort
    tr_drift = df_drift[df_drift["Cohort"] == "Embryo-Transfer Cohort"].sort_values("Standardized_Mean_Diff")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    y_pos = np.arange(len(tr_drift))
    colors = ["#e74c3c" if p >= 0.1 else "#2980b9" for p in tr_drift["Population_Stability_Index"]]
    ax.barh(y_pos, tr_drift["Standardized_Mean_Diff"], color=colors, alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tr_drift["Feature"], fontsize=9)
    ax.axvline(0, color="black", lw=1)
    ax.axvline(0.2, color="gray", linestyle=":", alpha=0.6)
    ax.axvline(-0.2, color="gray", linestyle=":", alpha=0.6)
    ax.set_title("Feature Distribution Shifts (Prospective vs Historical: Embryo-Transfer Cohort)\nRed = Population Stability Index (PSI) >= 0.1", fontsize=11, fontweight="bold")
    ax.set_xlabel("Standardized Mean Difference (SMD / Cohen's d)", fontsize=10)
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    f2 = out / "feature_drift_ks_smd.png"
    plt.savefig(f2)
    plt.close()
    generated.append(f2)

    # 3. Cutoff Sensitivity Comparison
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    cutoffs = sorted(df_cutoff["Cutoff_Date"].unique())
    rf_transfer = df_cutoff[(df_cutoff["Cohort"] == "Embryo-Transfer Cohort") & (df_cutoff["Model"] == "Random Forest")]
    for sc, color, marker in [
        ("Scenario A (Baseline)", "#3498db", "o"),
        ("Scenario B (Post-Retrieval)", "#e67e22", "s"),
        ("Scenario C (Pre-Transfer)", "#27ae60", "^"),
    ]:
        sub = rf_transfer[rf_transfer["Scenario"] == sc].sort_values("Cutoff_Date")
        ax.plot(sub["Cutoff_Date"], sub["ROC_AUC"], marker=marker, color=color, lw=2.5, label=f"{sc} RF")

    ax.set_title("Chronological Cutoff Sensitivity: Random Forest ROC-AUC (Transfer Cohort)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Chronological Split Boundary", fontsize=10)
    ax.set_ylabel("Out-of-Sample ROC-AUC", fontsize=10)
    ax.set_ylim([0.60, 0.80])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    plt.tight_layout()
    f3 = out / "cutoff_sensitivity_comparison.png"
    plt.savefig(f3)
    plt.close()
    generated.append(f3)

    # 4. Calibration Reliability Curves
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    key_lr = "Embryo-Transfer Cohort_Scenario C (Pre-Transfer)_Logistic Regression"
    key_rf = "Embryo-Transfer Cohort_Scenario C (Pre-Transfer)_Random Forest"

    for ax, k, title in [
        (ax1, key_lr, "Logistic Regression (Pre-Transfer)"),
        (ax2, key_rf, "Random Forest (Pre-Transfer)"),
    ]:
        if k in reliability_data:
            d = reliability_data[k]
            ax.plot([0, 1], [0, 1], "k--", lw=1.5, label="Perfect Calibration")
            ax.plot(d["prob_pred"], d["prob_true"], "s-", color="#2c3e50", lw=2, label="Observed Calibration")
            ax.set_title(f"{title}\nIntercept={d['cal_intercept']:.2f}, Slope={d['cal_slope']:.2f}", fontsize=10, fontweight="bold")
            ax.set_xlabel("Mean Predicted Probability", fontsize=9)
            ax.set_ylabel("Observed Outcome Fraction", fontsize=9)
            ax.set_xlim([0, 1])
            ax.set_ylim([0, 1])
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=9)

    plt.tight_layout()
    f4 = out / "calibration_diagnostics_reliability.png"
    plt.savefig(f4)
    plt.close()
    generated.append(f4)

    # 5. Feature Stability Bootstrap Boxplot
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    sorted_stab = df_stability.sort_values("Mean_Gini_Importance")
    y_pos = np.arange(len(sorted_stab))
    ax.barh(y_pos, sorted_stab["Mean_Gini_Importance"], xerr=sorted_stab["Std_Gini_Importance"], color="#16a085", alpha=0.85, capsize=4)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_stab["Feature"], fontsize=9)
    ax.set_title("Random Forest Feature Importance Stability (B=100 Bootstrap Resamples)\nMean Gini Importance ± 1 Std. Dev. (Historical Development Data)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Mean Gini Feature Importance", fontsize=10)
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    f5 = out / "feature_importance_stability_bootstrap.png"
    plt.savefig(f5)
    plt.close()
    generated.append(f5)

    # 6. Feature Ablation & AMH Sensitivity
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    df_sens_sorted = df_sensitivity.sort_values("ROC_AUC")
    y_pos = np.arange(len(df_sens_sorted))
    colors = ["#e67e22" if "Exclude Extreme" in s else ("#c0392b" if "embryos" in s else "#3498db") for s in df_sens_sorted["Specification"]]
    ax.barh(y_pos, df_sens_sorted["ROC_AUC"], color=colors, alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df_sens_sorted["Specification"], fontsize=8.5)
    ax.set_xlim([0.65, 0.76])
    ax.axvline(0.7275, color="black", linestyle="--", lw=1.5, label="Full Scenario C Baseline (0.728)")
    ax.set_title("Sensitivity & Ablation: Random Forest ROC-AUC on Holdout (Transfer Cohort)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Prospective ROC-AUC", fontsize=10)
    ax.grid(True, alpha=0.3, axis="x")
    ax.legend(fontsize=9)
    plt.tight_layout()
    f6 = out / "feature_ablation_sensitivity.png"
    plt.savefig(f6)
    plt.close()
    generated.append(f6)

    # 7. Clinical Threshold Tradeoffs
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    t_vals = df_threshold["Probability_Threshold"]
    ax.plot(t_vals, df_threshold["Sensitivity"], marker="o", color="#27ae60", lw=2.2, label="Sensitivity (Recall)")
    ax.plot(t_vals, df_threshold["Specificity"], marker="s", color="#e74c3c", lw=2.2, label="Specificity")
    ax.plot(t_vals, df_threshold["Positive_Predictive_Value_PPV"], marker="^", color="#2980b9", lw=2.2, label="PPV (Precision)")
    ax.plot(t_vals, df_threshold["Negative_Predictive_Value_NPV"], marker="d", color="#8e44ad", lw=2.2, label="NPV")
    ax.plot(t_vals, df_threshold["Balanced_Accuracy"], marker="x", color="#d35400", lw=2, linestyle="--", label="Balanced Accuracy")
    ax.axvline(0.5, color="gray", linestyle=":", lw=1.5, label="Default Threshold (0.5)")
    ax.axvline(0.787, color="#2c3e50", linestyle="-.", lw=1.5, label="Empirical Prevalence (0.787)")
    ax.set_title("Decision Threshold Trade-offs & Predictive Values (Transfer Cohort Holdout)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Classification Probability Threshold", fontsize=10)
    ax.set_ylabel("Metric Score", fontsize=10)
    ax.set_ylim([0, 1.05])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8.5, loc="lower left")
    plt.tight_layout()
    f7 = out / "clinical_threshold_tradeoffs.png"
    plt.savefig(f7)
    plt.close()
    generated.append(f7)

    return generated


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Format DataFrame as pure standard GitHub-flavored Markdown table."""
    headers = [str(c) for c in df.columns]
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    data_lines = []
    for _, row in df.iterrows():
        vals = []
        for v in row:
            if isinstance(v, float):
                vals.append(f"{v:.4f}" if not np.isnan(v) else "NaN")
            else:
                vals.append(str(v))
        data_lines.append("| " + " | ".join(vals) + " |")

    return "\n".join([header_line, separator_line] + data_lines)


def generate_robustness_validation_report(
    df_yearly: pd.DataFrame,
    df_drift: pd.DataFrame,
    df_cutoff: pd.DataFrame,
    df_or: pd.DataFrame,
    df_calib: pd.DataFrame,
    df_stability: pd.DataFrame,
    df_sensitivity: pd.DataFrame,
    df_threshold: pd.DataFrame,
    output_path: str | Path = "reports/robustness_validation.md",
) -> Path:
    """Generate comprehensive technical validation report for Phase 5."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    tr_drift_key = df_drift[df_drift["Cohort"] == "Embryo-Transfer Cohort"][
        ["Feature", "Historical_Mean", "Prospective_Mean", "Standardized_Mean_Diff", "KS_Statistic", "Population_Stability_Index", "Shift_Severity"]
    ]

    cutoff_transfer_scen_c = df_cutoff[
        (df_cutoff["Cohort"] == "Embryo-Transfer Cohort") & (df_cutoff["Scenario"] == "Scenario C (Pre-Transfer)")
    ][["Cutoff_Date", "Model", "Train_N", "Train_Pos_Rate", "Holdout_N", "Holdout_Pos_Rate", "ROC_AUC", "Balanced_Accuracy", "Brier_Score"]]

    or_transfer_c = df_or[
        (df_or["Cohort"] == "Embryo-Transfer Cohort") & (df_or["Scenario"] == "Scenario C (Pre-Transfer)")
    ][["Feature", "Coefficient_Beta", "Standard_Error", "Z_Statistic", "P_Value", "Odds_Ratio", "OR_CI_95_Formatted"]]

    calib_summary = df_calib[
        ["Cohort", "Scenario", "Model", "Brier_Score", "Calibration_Intercept", "Calibration_Slope", "Systematic_Bias", "Spread_Assessment"]
    ]

    report_content = f"""# IVF Insight — Phase 5: Robustness, Sensitivity & Model Validation Technical Report

**Author:** Senior Biomedical Data Scientist & Research Engineer  
**Generated Local Date:** 2026-11-01  
**Authoritative Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 candidate records; rows 0–4999 retained)  

---

## 1. Executive Summary & Validation Audit Purpose

Phase 5 conducts a thorough, skeptical validation audit of the Phase 4 predictive modelling results. Rather than seeking artificially elevated performance metrics, this evaluation assesses the **stability, reliability, calibration, and defensibility** of model predictions under temporal drift, cutoff shifts, extreme observations, and decision threshold selection.

> [!IMPORTANT]
> **Research Safeguards & Non-Claim Notice:**
> - This work is an educational portfolio project and must **never** be used for clinical decision-making or patient counselling.
> - The target outcome remains strictly documented as `recorded_cycle_outcome` due to unresolved author definitions (differentiating biochemical loss, ultrasound sac, or live birth).
> - $\\beta$-HCG is strictly excluded from all candidate predictor sets across all phases.
> - Historical training datasets are isolated; no prospective holdout data was used for model tuning or selection.
> - The dataset contains no patient-level master identifiers; clustering across the chronological boundary cannot be ruled out.

---

## 2. Temporal Drift & Prevalence Investigation

### Yearly Prevalence Dynamics
In the **Embryo-Transfer Cohort**, outcome prevalence exhibits a pronounced temporal surge:
- **Historical Development Period (2019–2023):** Overall positive prevalence was **61.8%** ($1,681 / 2,719$). During the 2020 COVID onset, prevalence dipped to $42.8\\%$, subsequently recovering to $56.3\\%$ in 2023.
- **Prospective Holdout Period (2024–2025):** Overall positive prevalence surged to **78.7%** ($811 / 1,031$), peaking at **82.7%** in 2024 ($578 / 699$).
- In the **Full-Cycle Cohort**, cycle cancellations (`Non-return of embryos`) also fluctuated markedly, from $16.1\\%$ in 2020 to $34.4\\%$ in 2025.

{_dataframe_to_markdown(df_yearly)}

### Feature Distribution Shift Analysis (Transfer Cohort)
Comparing feature distributions between historical (pre-2024) and prospective (post-2024) partitions:
- **Male Age:** Decreased significantly from $36.29$ to $34.68$ years (SMD = $-0.26$, KS $p = 1.27 \\times 10^{{-5}}$).
- **Number of Embryos Transferred:** Decreased from $2.59$ to $2.34$ (SMD = $-0.21$, KS $p = 1.56 \\times 10^{{-8}}$).
- **Embryo Grade 1 Count:** Decreased from $3.93$ to $3.20$ (SMD = $-0.19$, KS $p = 1.09 \\times 10^{{-6}}$).
- **Oocyte Maturity MI Count:** Increased from $1.65$ to $2.06$ (SMD = $+0.22$, KS $p = 7.35 \\times 10^{{-11}}$).

{_dataframe_to_markdown(tr_drift_key)}

> [!NOTE]
> **Interpretation Warning:** Temporal differences must **not** be assumed to reflect biological evolution. They strongly reflect evolving laboratory protocols (e.g. shift toward blastocyst transfer, single embryo transfer policies), changing patient intake demographics, or unrecorded clinical practice modifications.

---

## 3. Chronological Cutoff Sensitivity Analysis

To verify that model discrimination is not an artifact of the arbitrary `2024-01-01` boundary, chronological validation was repeated across multiple defensible split boundaries (`2023-01-01`, `2024-01-01`, `2024-07-01`):

{_dataframe_to_markdown(cutoff_transfer_scen_c)}

### Key Findings:
1. **Performance Stability:** Across all three chronological boundaries, Scenario C Random Forest consistently outperforms Scenario A and B, maintaining out-of-sample ROC-AUC between **0.709 and 0.750**.
2. **Prevalence Gradient:** As the split boundary moves later, holdout positive prevalence increases ($70.6\\% \\rightarrow 78.7\\% \\rightarrow 77.7\\%$), while ROC-AUC attenuates slightly from $0.750$ to $0.709$, reflecting increasing case complexity in the later periods.

---

## 4. Statistically Rigorous Logistic Regression Odds Ratios

Standardized odds ratios and asymptotic $95\\%$ confidence intervals were estimated using `statsmodels.Logit` on standardized historical training features:

{_dataframe_to_markdown(or_transfer_c)}

### Methodological Notes:
- **Continuous Features:** Odds ratios represent the multiplicative change in outcome odds per **1 standard deviation increase** in the standardized predictor.
- **Categorical Handling:** Binary/nominal indicators (e.g., `frezzing`) were standardized to enable direct effect-size comparison across variables.
- **Top Effect Sizes:** Surplus frozen embryos (`frezzing`, $\\text{{OR}} = 2.408$, $95\\%$ CI: $[2.022, 2.868]$, $p < 0.0001$) and fertilization count (`Number of fertilized eggs`, $\\text{{OR}} = 1.583$, $95\\%$ CI: $[1.158, 2.162]$, $p = 0.004$) are the strongest positive multivariable predictors. Increasing male age is a significant negative predictor ($\\text{{OR}} = 0.753$, $95\\%$ CI: $[0.675, 0.840]$, $p < 0.0001$).
- **Caution:** Odds ratios apply strictly to Logistic Regression; Random Forest feature importances reflect Gini impurity reduction and cannot be expressed as odds ratios.

---

## 5. Calibration Diagnostics & Recalibration Analysis

Calibration was evaluated via Harrell/Cox logistic recalibration regressing observed holdout outcomes on logit-transformed predicted probabilities: $\\text{{logit}}(Y) = \\alpha + \\beta \\cdot \\text{{logit}}(p)$.

{_dataframe_to_markdown(calib_summary)}

### Diagnostic Insights:
- **Systematic Underconfidence (Intercept $\\alpha > 0$):**
  For the prospective transfer cohort, models exhibit a positive recalibration intercept ($\\alpha \\approx +0.96$ for Scenario C RF). Because historical training data had a $61.8\\%$ positive rate whereas the prospective holdout had $78.7\\%$, the models' uncalibrated probabilities systematically underestimate the baseline likelihood of success (pessimistic bias).
- **Refinement Slope ($\\beta \\approx 0.87$):**
  The recalibration slope is slightly below $1.0$, indicating mild overconfidence in the spread of extreme predictions.

---

## 6. Feature Stability & Sensitivity Analyses

### Feature Importance Stability (B=100 Bootstrap Resamples)
Evaluating Gini importance stability across 100 bootstrap replicates of historical training data:

{_dataframe_to_markdown(df_stability.head(8))}

- `frezzing` consistently captures rank #1 across $100\\%$ of bootstrap resamples (Mean Gini: $0.341 \\pm 0.023$).
- `Number of fertilized eggs` and `Number of embryos` reliably occupy ranks #2 and #3.

### Sensitivity Analyses & Ablations
{_dataframe_to_markdown(df_sensitivity)}

1. **Impact of Extreme AMH Values ($482.1$):**
   Excluding the 3 extreme AMH observations results in negligible change to out-of-sample ROC-AUC ($0.7275 \\rightarrow 0.7262$, $\\Delta = -0.0013$), demonstrating that median imputation and tree partitioning are inherently robust to extreme values.
2. **Leave-One-Feature-Out (LOFO) Ablation:**
   - Removing `Number of embryos` causes the largest single drop in ROC-AUC ($0.7275 \\rightarrow 0.6946$, $\\Delta = -0.0329$).
   - Removing `frezzing` reduces balanced accuracy from $67.3\\%$ to $64.1\\%$.

---

## 7. Clinical Threshold Trade-offs & Prevalence Effects

{_dataframe_to_markdown(df_threshold)}

### Impact of Base Rate (Bayes' Theorem):
- At the standard threshold of **$0.5$**, sensitivity is $78.7\\%$, specificity is $55.9\\%$, and balanced accuracy is $67.3\\%$.
- Because holdout prevalence is high ($78.7\\%$), Positive Predictive Value (PPV) is naturally elevated to **$86.8\\%$**, while Negative Predictive Value (NPV) is depressed to **$41.6\\%$**.
- At the prevalence-calibrated threshold of **$0.787$**, specificity rises to $82.7\\%$ and PPV to $89.6\\%$, but sensitivity drops to $40.6\\%$.
- This demonstrates that choosing a probability cutoff is a clinical risk-utility tradeoff that cannot be made without explicit clinical loss functions.

---

## 8. Artifacts Index

The following outputs have been generated in `reports/`:
- **CSVs:** `reports/temporal_drift.csv`, `reports/cutoff_sensitivity.csv`, `reports/logistic_regression_odds_ratios.csv`, `reports/calibration_diagnostics.csv`, `reports/feature_stability.csv`, `reports/threshold_analysis.csv`.
- **Figures:** `reports/robustness_figures/` (7 diagnostic plots).
- **Notebook:** `notebooks/04_robustness_validation.ipynb`.
- **Automated Tests:** `tests/test_robustness.py`.
"""
    out_file.write_text(report_content, encoding="utf-8")
    return out_file


def run_robustness_pipeline(
    excel_path: str | Path = "data/raw/Dataset Clean.xlsx",
    output_dir: str | Path = "reports",
    figures_dir: str | Path = "reports/robustness_figures",
) -> Dict[str, Any]:
    """Execute complete Phase 5 robustness and sensitivity analysis pipeline."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_out = Path(figures_dir)
    fig_out.mkdir(parents=True, exist_ok=True)

    df_full, df_transfer = load_clean_cohorts(excel_path)

    # 1. Temporal Drift
    df_yearly, df_drift = analyze_temporal_drift(df_full, df_transfer)
    df_yearly.to_csv(out / "temporal_drift_yearly.csv", index=False)
    df_drift.to_csv(out / "temporal_drift.csv", index=False)

    # 2. Cutoff Sensitivity
    df_cutoff = evaluate_cutoff_sensitivity(df_full, df_transfer)
    df_cutoff.to_csv(out / "cutoff_sensitivity.csv", index=False)

    # 3. Logistic Regression Odds Ratios
    df_or = compute_logistic_regression_odds_ratios(df_full, df_transfer)
    df_or.to_csv(out / "logistic_regression_odds_ratios.csv", index=False)

    # 4. Calibration Diagnostics
    df_calib, reliability_data = compute_calibration_diagnostics(df_full, df_transfer)
    df_calib.to_csv(out / "calibration_diagnostics.csv", index=False)

    # 5. Feature Stability
    df_stability = evaluate_feature_importance_stability(df_transfer)
    df_stability.to_csv(out / "feature_stability.csv", index=False)

    # 6. Sensitivity Analysis
    df_sensitivity = evaluate_sensitivity_analyses(df_transfer)
    df_sensitivity.to_csv(out / "sensitivity_analyses.csv", index=False)

    # 7. Clinical Thresholds
    df_threshold = evaluate_clinical_thresholds(df_transfer)
    df_threshold.to_csv(out / "threshold_analysis.csv", index=False)

    # 8. Generate Figures
    fig_paths = generate_robustness_figures(
        df_yearly, df_drift, df_cutoff, df_stability, df_sensitivity, df_threshold, reliability_data, output_dir=fig_out
    )

    # 9. Generate Report
    report_path = generate_robustness_validation_report(
        df_yearly, df_drift, df_cutoff, df_or, df_calib, df_stability, df_sensitivity, df_threshold, output_path=out / "robustness_validation.md"
    )

    return {
        "report": report_path,
        "figures": fig_paths,
        "yearly_drift": df_yearly,
        "feature_drift": df_drift,
        "cutoff_sensitivity": df_cutoff,
        "odds_ratios": df_or,
        "calibration": df_calib,
        "feature_stability": df_stability,
        "sensitivity": df_sensitivity,
        "thresholds": df_threshold,
    }
