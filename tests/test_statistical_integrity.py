"""Unit and integration tests for Phase 5.1 Statistical Integrity & Interpretation Audit."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ivf_insight.eda import load_clean_cohorts
from ivf_insight.integrity_audit import (
    audit_temporal_drift_hypotheses,
    audit_female_age_association,
    audit_logistic_regression_diagnostics,
    audit_calibration_equations,
    audit_feature_definitions,
)


@pytest.fixture(scope="module")
def cohorts():
    excel_path = Path("data/raw/Dataset Clean.xlsx")
    return load_clean_cohorts(excel_path)


def test_temporal_drift_hypotheses_audit():
    """Verify classification of testable empirical evidence vs untestable speculations."""
    df_hyp = audit_temporal_drift_hypotheses()
    assert len(df_hyp) >= 4
    assert "Proposed_Hypothesis" in df_hyp.columns
    assert "Testability_Status" in df_hyp.columns

    # Blastocyst adoption and culture media must be labeled untestable
    blast_row = df_hyp[df_hyp["Proposed_Hypothesis"].str.contains("Blastocyst")].iloc[0]
    assert blast_row["Testability_Status"] == "Untestable Speculation"

    media_row = df_hyp[df_hyp["Proposed_Hypothesis"].str.contains("Laboratory Equipment")].iloc[0]
    assert media_row["Testability_Status"] == "Untestable Speculation"

    # Transfer count shift must be labeled supported
    transfer_row = df_hyp[df_hyp["Proposed_Hypothesis"].str.contains("Embryo Transfer Count")].iloc[0]
    assert transfer_row["Testability_Status"] == "Supported by Dataset"


def test_female_age_association_audit(cohorts):
    """Verify deconstruction of Female Age odds-ratio, reciprocal suppression, and splines."""
    df_full, df_transfer = cohorts
    df_prog, df_brackets, audit_dict = audit_female_age_association(df_full, df_transfer, cutoff_date="2024-01-01")

    # 1. Progression table checks
    assert len(df_prog) == 8
    unadj_fem = df_prog[df_prog["Model_Specification"] == "Transfer Cohort — Unadjusted Female Age"].iloc[0]
    unadj_male = df_prog[df_prog["Model_Specification"] == "Transfer Cohort — Unadjusted Male Age"].iloc[0]
    both_age = df_prog[df_prog["Model_Specification"] == "Transfer Cohort — Female Age + Male Age"].iloc[0]

    # Unadjusted Female Age is positive; Male Age is negative
    assert unadj_fem["Female_Age_Beta_Std"] > 0
    assert unadj_male["Male_Age_Beta_Std"] < 0

    # Reciprocal suppression: Both betas increase in absolute magnitude when modeled together
    assert both_age["Female_Age_Beta_Std"] > unadj_fem["Female_Age_Beta_Std"]
    assert both_age["Male_Age_Beta_Std"] < unadj_male["Male_Age_Beta_Std"]

    # 2. Age bracket empirical check
    assert len(df_brackets) == 5
    # Paradoxical empirical gradient in this cohort: older brackets have higher prevalence
    prev_young = df_brackets.iloc[0]["Observed_Prevalence"]
    prev_old = df_brackets.iloc[-1]["Observed_Prevalence"]
    assert prev_old > prev_young

    # 3. Non-linearity spline test: linear logit is not rejected (p >= 0.05)
    assert audit_dict["spline_p_value"] >= 0.05
    assert audit_dict["linearity_supported"] is True


def test_logistic_regression_diagnostics_audit(cohorts):
    """Verify multicollinearity VIF, Box-Tidwell linearity, and bootstrap CIs."""
    _, df_transfer = cohorts
    # Run with small bootstrap n=10 for rapid test execution
    df_diag = audit_logistic_regression_diagnostics(df_transfer, cutoff_date="2024-01-01", n_bootstraps=10, random_state=42)

    assert len(df_diag) == 14
    assert "Variance_Inflation_Factor" in df_diag.columns
    assert "Bootstrap_OR_95_CI" in df_diag.columns

    # Fertilized eggs must exhibit severe collinearity (VIF >= 10)
    fert_row = df_diag[df_diag["Feature"] == "Number of fertilized eggs"].iloc[0]
    assert fert_row["Variance_Inflation_Factor"] >= 10.0
    assert fert_row["Collinearity_Flag"] == "Severe (VIF > 10)"

    # Female Age must exhibit low collinearity (VIF < 2)
    fem_row = df_diag[df_diag["Feature"] == "Female Age"].iloc[0]
    assert fem_row["Variance_Inflation_Factor"] < 2.0

    # AMH should violate linearity in logit
    amh_row = df_diag[df_diag["Feature"] == "AMH"].iloc[0]
    assert amh_row["Logit_Linearity_Status"] == "Non-linear in logit"


def test_calibration_audit(cohorts):
    """Verify canonical CITL via offset, calibration slope, and E/O ratio."""
    _, df_transfer = cohorts
    df_calib, plot_data = audit_calibration_equations(df_transfer, cutoff_date="2024-01-01", random_state=42)

    assert len(df_calib) == 6
    assert "CITL_Offset_Alpha" in df_calib.columns
    assert "Calibration_Slope_Beta" in df_calib.columns
    assert "Expected_to_Observed_Ratio_EO" in df_calib.columns

    # Scenario C RF on holdout
    scen_c_rf = df_calib[(df_calib["Scenario"] == "Scenario C (Pre-Transfer)") & (df_calib["Model"] == "Random Forest")].iloc[0]
    # CITL > 0 (underconfidence) and E/O < 1.0 (mean predicted ~ 0.63 vs observed ~ 0.79)
    assert scen_c_rf["CITL_Offset_Alpha"] > 0.5
    assert scen_c_rf["Expected_to_Observed_Ratio_EO"] < 0.90
    assert 0.70 < scen_c_rf["Calibration_Slope_Beta"] < 1.10


def test_feature_definitions_audit():
    """Verify precise documentation of variable counts, frezzing semantics, and metric separation."""
    df_feats = audit_feature_definitions()
    assert len(df_feats) >= 5

    frezz_row = df_feats[df_feats["Feature_Name"] == "frezzing"].iloc[0]
    assert "Integer Count" in frezz_row["Variable_Type"]
    assert "0–25" in frezz_row["Variable_Type"]
    assert "Misspelled" in frezz_row["Dataset_Typo_Notice"]

    # Grade 1 must be documented as an integer count, not a categorical class
    g1_row = df_feats[df_feats["Feature_Name"] == "Embryo Grade 1"].iloc[0]
    assert "Integer Count" in g1_row["Variable_Type"]


def test_phase5_1_deliverables_exist():
    """Verify all required Phase 5.1 outputs exist and are populated."""
    expected_files = [
        "reports/statistical_integrity_audit.md",
        "reports/logistic_regression_diagnostics.csv",
        "reports/age_association_analysis.csv",
        "reports/calibration_audit.csv",
        "reports/feature_interpretation_audit.csv",
        "reports/robustness_figures/age_association_splines.png",
        "reports/robustness_figures/multicollinearity_vif.png",
        "reports/robustness_figures/calibration_citl_recalibration.png",
        "notebooks/05_statistical_integrity_audit.ipynb",
    ]
    for rel_path in expected_files:
        p = Path(rel_path)
        assert p.exists(), f"Missing required Phase 5.1 deliverable: {rel_path}"
        assert p.stat().st_size > 0, f"Deliverable is empty: {rel_path}"
