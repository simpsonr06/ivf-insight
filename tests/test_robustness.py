"""Unit and integration tests for Phase 5 Robustness, Sensitivity & Model Validation module."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ivf_insight.eda import load_clean_cohorts, BETA_COL
from ivf_insight.experiments import SCENARIO_FEATURES, TARGET_COL, DATE_COL
from ivf_insight.governance import ChronologicalValidationManager
from ivf_insight.validation import (
    calculate_population_stability_index,
    analyze_temporal_drift,
    evaluate_cutoff_sensitivity,
    compute_logistic_regression_odds_ratios,
    compute_calibration_diagnostics,
    evaluate_feature_importance_stability,
    evaluate_sensitivity_analyses,
    evaluate_clinical_thresholds,
)


@pytest.fixture(scope="module")
def cohorts():
    excel_path = Path("data/raw/Dataset Clean.xlsx")
    return load_clean_cohorts(excel_path)


def test_population_stability_index():
    """Verify calculation of Population Stability Index (PSI)."""
    # Identical distributions should yield PSI near 0
    np.random.seed(42)
    s1 = pd.Series(np.random.normal(0, 1, 1000))
    s2 = pd.Series(np.random.normal(0, 1, 1000))
    psi_identical = calculate_population_stability_index(s1, s2)
    assert psi_identical < 0.05

    # Substantially shifted distribution should yield PSI > 0.25
    s_shifted = pd.Series(np.random.normal(1.5, 1, 1000))
    psi_shifted = calculate_population_stability_index(s1, s_shifted)
    assert psi_shifted > 0.25


def test_temporal_drift_analysis(cohorts):
    """Verify yearly outcome prevalence and feature drift calculation."""
    df_full, df_transfer = cohorts
    df_yearly, df_drift = analyze_temporal_drift(df_full, df_transfer, cutoff_date="2024-01-01")

    # 1. Yearly dataframe checks
    assert len(df_yearly) >= 6
    assert set(df_yearly["Year"]).issubset({2019, 2020, 2021, 2022, 2023, 2024, 2025})
    assert df_yearly["Full_Cycles_Total"].sum() == 5000
    assert df_yearly["Transfer_Cycles_Total"].sum() == 3750
    assert df_yearly["Non_Return_Cycles"].sum() == 1250

    # 2. Transfer cohort surge verification (2024 prevalence > 80%)
    prev_2024 = df_yearly.loc[df_yearly["Year"] == 2024, "Transfer_Cohort_Prevalence"].values[0]
    assert prev_2024 > 0.80

    # 3. Drift dataframe checks
    assert len(df_drift) == 28  # 14 features * 2 cohorts
    assert "Population_Stability_Index" in df_drift.columns
    assert "Standardized_Mean_Diff" in df_drift.columns
    assert "KS_P_Value" in df_drift.columns


def test_cutoff_sensitivity_temporal_ordering(cohorts):
    """Verify cutoff sensitivity preserves strict chronological ordering for each split."""
    df_full, df_transfer = cohorts
    cutoffs = ["2023-01-01", "2024-01-01"]

    for c in cutoffs:
        train_tr, test_tr, _ = ChronologicalValidationManager.split(df_transfer, cutoff=c)
        assert train_tr[DATE_COL].max() < pd.Timestamp(c)
        assert test_tr[DATE_COL].min() >= pd.Timestamp(c)
        assert len(train_tr) + len(test_tr) == 3750


def test_logistic_regression_odds_ratios(cohorts):
    """Verify odds ratios match exp(beta) and confidence intervals are mathematically valid."""
    df_full, df_transfer = cohorts
    df_or = compute_logistic_regression_odds_ratios(df_full, df_transfer, cutoff_date="2024-01-01")

    assert not df_or.empty
    assert "Odds_Ratio" in df_or.columns
    assert "Coefficient_Beta" in df_or.columns
    assert "Standard_Error" in df_or.columns

    for _, row in df_or.iterrows():
        beta = row["Coefficient_Beta"]
        se = row["Standard_Error"]
        or_val = row["Odds_Ratio"]
        ci_low = row["OR_CI_95_Low"]
        ci_high = row["OR_CI_95_High"]

        # Math verification
        assert np.isclose(or_val, np.exp(beta), atol=1e-3)
        assert np.isclose(ci_low, np.exp(beta - 1.96 * se), atol=1e-3)
        assert np.isclose(ci_high, np.exp(beta + 1.96 * se), atol=1e-3)
        assert ci_low <= or_val <= ci_high
        assert 0.0 <= row["P_Value"] <= 1.0


def test_calibration_diagnostics(cohorts):
    """Verify calibration intercept, slope, and reliability estimates."""
    df_full, df_transfer = cohorts
    df_calib, reliability_data = compute_calibration_diagnostics(df_full, df_transfer, cutoff_date="2024-01-01")

    assert len(df_calib) == 12  # 2 cohorts * 3 scenarios * 2 models
    assert "Calibration_Intercept" in df_calib.columns
    assert "Calibration_Slope" in df_calib.columns
    assert "Brier_Score" in df_calib.columns

    # In transfer cohort, prospective prevalence is 78.7% vs 61.8% train, so intercept must be positive (underconfident)
    tr_calib = df_calib[
        (df_calib["Cohort"] == "Embryo-Transfer Cohort") & (df_calib["Scenario"] == "Scenario C (Pre-Transfer)")
    ]
    for _, row in tr_calib.iterrows():
        assert row["Calibration_Intercept"] > 0.0  # Pessimistic probability estimates
        assert 0.0 < row["Brier_Score"] < 0.25


def test_feature_stability_bootstrap(cohorts):
    """Verify bootstrap resampling for feature importance and rank stability."""
    _, df_transfer = cohorts
    df_stab = evaluate_feature_importance_stability(df_transfer, cutoff_date="2024-01-01", n_bootstraps=5, random_state=42)

    assert len(df_stab) == 14
    assert np.isclose(df_stab["Mean_Gini_Importance"].sum(), 1.0, atol=0.05)
    # frezzing should hold top rank
    assert df_stab.iloc[0]["Feature"] == "frezzing"
    assert df_stab.iloc[0]["Mean_Rank"] <= 2.0


def test_extreme_amh_sensitivity_and_ablation(cohorts):
    """Verify sensitivity to extreme AMH and feature ablation."""
    _, df_transfer = cohorts
    df_sens = evaluate_sensitivity_analyses(df_transfer, cutoff_date="2024-01-01", random_state=42)

    assert len(df_sens) >= 8
    # Baseline vs AMH outlier check
    baseline_row = df_sens[df_sens["Sensitivity_Domain"] == "Baseline Benchmark"].iloc[0]
    amh_row = df_sens[df_sens["Sensitivity_Domain"] == "AMH Extreme Outlier Sensitivity"].iloc[0]

    assert baseline_row["N_Train"] == 2719
    assert amh_row["N_Train"] == 2717  # 2 extreme AMH records removed from train
    # Performance difference should be minor (< 0.01 AUC)
    assert abs(baseline_row["ROC_AUC"] - amh_row["ROC_AUC"]) < 0.01

    # Ensure β-HCG is never present
    for spec in df_sens["Specification"]:
        assert "β-HCG" not in spec
        assert "B-HCG" not in spec


def test_clinical_thresholds(cohorts):
    """Verify decision threshold monotonicity and Bayes' prevalence dynamics."""
    _, df_transfer = cohorts
    df_thresh = evaluate_clinical_thresholds(df_transfer, cutoff_date="2024-01-01", random_state=42)

    assert len(df_thresh) >= 8

    # Monotonicity: As threshold increases, sensitivity must be non-increasing, specificity non-decreasing
    sens = df_thresh["Sensitivity"].to_numpy()
    spec = df_thresh["Specificity"].to_numpy()
    assert np.all(np.diff(sens) <= 1e-6)
    assert np.all(np.diff(spec) >= -1e-6)

    # In high-prevalence holdout (78.7%), PPV at threshold 0.5 must exceed 80%
    row_05 = df_thresh[df_thresh["Probability_Threshold"] == 0.5].iloc[0]
    assert row_05["Positive_Predictive_Value_PPV"] > 0.80


def test_phase5_deliverables_exist():
    """Verify all Phase 5 report deliverables, CSVs, figures, and notebooks exist."""
    expected_files = [
        "reports/robustness_validation.md",
        "reports/temporal_drift.csv",
        "reports/temporal_drift_yearly.csv",
        "reports/cutoff_sensitivity.csv",
        "reports/logistic_regression_odds_ratios.csv",
        "reports/calibration_diagnostics.csv",
        "reports/feature_stability.csv",
        "reports/threshold_analysis.csv",
        "reports/sensitivity_analyses.csv",
        "reports/robustness_figures/temporal_drift_prevalence.png",
        "reports/robustness_figures/feature_drift_ks_smd.png",
        "reports/robustness_figures/cutoff_sensitivity_comparison.png",
        "reports/robustness_figures/calibration_diagnostics_reliability.png",
        "reports/robustness_figures/feature_importance_stability_bootstrap.png",
        "reports/robustness_figures/feature_ablation_sensitivity.png",
        "reports/robustness_figures/clinical_threshold_tradeoffs.png",
        "notebooks/04_robustness_validation.ipynb",
    ]
    for rel_path in expected_files:
        p = Path(rel_path)
        assert p.exists(), f"Missing required Phase 5 deliverable: {rel_path}"
        assert p.stat().st_size > 0, f"Deliverable is empty: {rel_path}"
