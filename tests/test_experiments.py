"""Unit and integration tests for Phase 4 Predictive Modelling and Evaluation module."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline

from ivf_insight.experiments import (
    SCENARIO_FEATURES,
    TARGET_COL,
    DATE_COL,
    build_pipeline,
    compute_bootstrap_confidence_intervals,
    evaluate_model_experiment,
    extract_explainability_metrics,
    run_predictive_experiments,
)
from ivf_insight.governance import ChronologicalValidationManager
from ivf_insight.eda import load_clean_cohorts


def test_scenario_features_governance():
    """Verify strict temporal scenario feature definitions and exclusions."""
    # 1. Scenario A must have exactly 4 confirmed baseline features
    expected_scenario_a = [
        "Female Age",
        "Male Age",
        "AMH",
        "Number of attempts",
    ]
    assert SCENARIO_FEATURES["Scenario A (Baseline)"] == expected_scenario_a
    assert len(SCENARIO_FEATURES["Scenario A (Baseline)"]) == 4

    # 2. Scenario B must have exactly 8 features
    expected_scenario_b = expected_scenario_a + [
        "Oocyte Maturity MII",
        "Oocyte Maturity MI",
        "Oocyte Maturity others",
        "Number of fertilized eggs",
    ]
    assert SCENARIO_FEATURES["Scenario B (Post-Retrieval)"] == expected_scenario_b
    assert len(SCENARIO_FEATURES["Scenario B (Post-Retrieval)"]) == 8

    # 3. Scenario C must have exactly 14 features
    expected_scenario_c = expected_scenario_b + [
        "Embryo Grade 1",
        "Embryo Grade 2",
        "Embryo Grade 3",
        "Embryo Grade 4",
        "Number of embryos",
        "frezzing",
    ]
    assert SCENARIO_FEATURES["Scenario C (Pre-Transfer)"] == expected_scenario_c
    assert len(SCENARIO_FEATURES["Scenario C (Pre-Transfer)"]) == 14

    # 4. Mandatory exclusions across all scenarios
    forbidden_features = [
        "β-HCG",
        "β-HCG (mIU/mL)",
        "B-HCG",
        "b-hcg",
        "Medicines and treatments",
        "Sperm count",
        "Sperm motility",
        "Sperm morphology",
        "Output(failed implantation or successful implantation)",
        "recorded_cycle_outcome",
    ]
    for scenario_name, features in SCENARIO_FEATURES.items():
        for forbidden in forbidden_features:
            assert forbidden not in features, f"{forbidden} found in {scenario_name}"


def test_chronological_split_isolation():
    """Verify chronological split enforces strict cutoff without future leakage."""
    excel_path = Path("data/raw/Dataset Clean.xlsx")
    df_full, df_transfer = load_clean_cohorts(excel_path)
    # Test full-cycle cohort split
    train_full, test_full, _ = ChronologicalValidationManager.split(df_full, cutoff="2024-01-01")
    assert len(train_full) == 3542
    assert len(test_full) == 1458
    assert train_full[DATE_COL].max() < pd.Timestamp("2024-01-01")
    assert test_full[DATE_COL].min() >= pd.Timestamp("2024-01-01")

    # Test embryo-transfer cohort split
    train_tr, test_tr, _ = ChronologicalValidationManager.split(df_transfer, cutoff="2024-01-01")
    assert len(train_tr) == 2719
    assert len(test_tr) == 1031
    assert train_tr[DATE_COL].max() < pd.Timestamp("2024-01-01")
    assert test_tr[DATE_COL].min() >= pd.Timestamp("2024-01-01")

    # Verify no overlap between training and testing sets
    assert set(train_full.index).isdisjoint(set(test_full.index))
    assert set(train_tr.index).isdisjoint(set(test_tr.index))


def test_pipeline_preprocessing_leakage_prevention():
    """Verify imputer and scaler learn statistics strictly from training data."""
    # Synthetic dataset with different distributions and missing values
    X_train = pd.DataFrame({
        "feat1": [10.0, 20.0, 30.0, np.nan],  # train median = 20.0, train mean = 20.0
        "feat2": [100.0, 200.0, 300.0, 400.0],
    })
    y_train = pd.Series([0, 1, 0, 1])

    X_test = pd.DataFrame({
        "feat1": [np.nan, 1000.0],  # extreme value in test that should NOT affect train statistics
        "feat2": [5000.0, 6000.0],
    })

    pipe = build_pipeline("logistic_regression")
    assert isinstance(pipe, Pipeline)

    pipe.fit(X_train, y_train)

    # Imputer statistics should reflect only X_train
    imputer = pipe.named_steps["imputer"]
    assert imputer.statistics_[0] == 20.0  # Median of [10, 20, 30]

    # Scaler mean should reflect only imputed X_train
    scaler = pipe.named_steps["scaler"]
    # imputed feat1 in train is [10, 20, 30, 20], mean = 20.0
    assert scaler.mean_[0] == pytest.approx(20.0)


def test_metrics_and_majority_baseline():
    """Verify evaluation metric computation and majority baseline behavior."""
    # Create synthetic test dataset
    # 70% positive (1) and 30% negative (0)
    y_train = pd.Series([1] * 70 + [0] * 30)
    X_train = pd.DataFrame({"f1": np.random.randn(100), "f2": np.random.randn(100)})

    y_test = pd.Series([1] * 80 + [0] * 20)
    X_test = pd.DataFrame({"f1": np.random.randn(100), "f2": np.random.randn(100)})

    # Test Majority Baseline
    majority_pipe = build_pipeline("majority")
    maj_results = evaluate_model_experiment(
        majority_pipe,
        X_train,
        y_train,
        X_test,
        y_test,
        model_name="Majority Baseline",
        scenario_name="Scenario A (Baseline)",
        cohort_name="Synthetic Cohort",
    )

    # Majority baseline must always predict class 1, yielding:
    # Accuracy = 80%, Balanced Accuracy = 50%, ROC-AUC = 0.5000
    assert maj_results["roc_auc"] == 0.5000
    assert maj_results["balanced_accuracy"] == 0.5000
    assert maj_results["accuracy"] == 0.8000
    assert maj_results["recall_sensitivity"] == 1.0000
    assert maj_results["specificity"] == 0.0000

    # Test Logistic Regression pipeline evaluation
    lr_pipe = build_pipeline("logistic_regression")
    lr_results = evaluate_model_experiment(
        lr_pipe,
        X_train,
        y_train,
        X_test,
        y_test,
        model_name="Logistic Regression",
        scenario_name="Scenario A (Baseline)",
        cohort_name="Synthetic Cohort",
    )
    assert "roc_auc" in lr_results
    assert "pr_auc" in lr_results
    assert "brier_score" in lr_results
    assert "roc_auc_ci_95" in lr_results
    assert lr_results["true_positives"] + lr_results["false_negatives"] == 80
    assert lr_results["true_negatives"] + lr_results["false_positives"] == 20


def test_bootstrap_confidence_intervals():
    """Verify non-parametric bootstrap confidence interval estimation."""
    rng = np.random.RandomState(42)
    y_true = np.array([0] * 50 + [1] * 50)
    # Perfect predictor with minor noise
    y_prob = np.array([0.05] * 50 + [0.95] * 50)
    y_pred = np.array([0] * 50 + [1] * 50)

    ci_dict = compute_bootstrap_confidence_intervals(y_true, y_prob, y_pred, n_bootstraps=200, random_state=42)

    assert "roc_auc_ci" in ci_dict
    assert "pr_auc_ci" in ci_dict
    assert "balanced_accuracy_ci" in ci_dict
    assert "brier_score_ci" in ci_dict

    # For perfect predictions, ROC-AUC CI should be [1.0, 1.0]
    assert ci_dict["roc_auc_ci"][0] == 1.0
    assert ci_dict["roc_auc_ci"][1] == 1.0
    assert ci_dict["balanced_accuracy_ci"][0] == 1.0


def test_explainability_extraction():
    """Verify extraction of odds ratios and Gini feature importances."""
    np.random.seed(42)
    X_train = pd.DataFrame({
        "Female Age": np.concatenate([np.random.randint(20, 30, 15), np.random.randint(38, 48, 15)]),
        "Male Age": np.concatenate([np.random.randint(22, 32, 15), np.random.randint(40, 50, 15)]),
        "AMH": np.concatenate([np.random.uniform(2.5, 5.0, 15), np.random.uniform(0.1, 1.0, 15)]),
        "Number of attempts": np.concatenate([np.random.randint(1, 2, 15), np.random.randint(3, 6, 15)]),
    })
    y_train = pd.Series([1] * 15 + [0] * 15)

    # Fit Logistic Regression
    lr_pipe = build_pipeline("logistic_regression")
    lr_pipe.fit(X_train, y_train)

    # Fit Random Forest
    rf_pipe = build_pipeline("random_forest")
    rf_pipe.fit(X_train, y_train)

    mock_experiments = [
        {
            "cohort": "Test Cohort",
            "scenario": "Scenario A (Baseline)",
            "model": "Logistic Regression",
            "_fitted_pipeline": lr_pipe,
        },
        {
            "cohort": "Test Cohort",
            "scenario": "Scenario A (Baseline)",
            "model": "Random Forest",
            "_fitted_pipeline": rf_pipe,
        },
    ]

    explain = extract_explainability_metrics(mock_experiments)

    lr_key = "Test Cohort_Scenario A (Baseline)_Logistic Regression"
    rf_key = "Test Cohort_Scenario A (Baseline)_Random Forest"

    assert lr_key in explain
    lr_df = explain[lr_key]
    assert "odds_ratio" in lr_df.columns
    assert "coefficient" in lr_df.columns
    assert len(lr_df) == 4

    assert rf_key in explain
    rf_df = explain[rf_key]
    assert "gini_importance" in rf_df.columns
    assert len(rf_df) == 4
    assert np.isclose(rf_df["gini_importance"].sum(), 1.0, atol=1e-2)


def test_phase4_saved_artifacts_and_metrics():
    """Verify that all Phase 4 outputs, models, and metric files exist and are valid."""
    # 1. Metrics CSV
    metrics_csv = Path("reports/model_metrics.csv")
    assert metrics_csv.exists()
    df_metrics = pd.read_csv(metrics_csv)
    # 18 experiments: 2 cohorts * 3 scenarios * 3 models
    assert len(df_metrics) == 18
    assert "roc_auc" in df_metrics.columns
    assert "pr_auc" in df_metrics.columns
    assert "brier_score" in df_metrics.columns

    # 2. Comparison Report Markdown
    comparison_md = Path("reports/model_comparison.md")
    assert comparison_md.exists()
    md_content = comparison_md.read_text(encoding="utf-8")
    assert "Phase 4 Predictive Modelling" in md_content
    assert "Full-Cycle Cohort (N = 5,000)" in md_content
    assert "Embryo-Transfer Cohort (N = 3,750)" in md_content
    assert "The Disillusion of Near-Perfect Prediction" in md_content

    # 3. Model Metadata and Saved Pipelines
    metadata_json = Path("models/experiment_metadata.json")
    assert metadata_json.exists()

    models_dir = Path("models")
    joblib_files = list(models_dir.glob("*.joblib"))
    assert len(joblib_files) == 18

    # 4. Confusion Matrices (18 heatmaps)
    cm_dir = Path("reports/confusion_matrices")
    cm_files = list(cm_dir.glob("*.png"))
    assert len(cm_files) == 18

    # 5. Diagnostic Figures (8 figures)
    fig_dir = Path("reports/model_figures")
    fig_files = list(fig_dir.glob("*.png"))
    assert len(fig_files) == 8

    # 6. Jupyter Notebook
    nb_path = Path("notebooks/03_predictive_modelling.ipynb")
    assert nb_path.exists()
