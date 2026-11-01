"""Unit and integration tests for feature governance, prediction scenarios, and validation safeguards."""

from pathlib import Path
import pandas as pd
import pytest

from ivf_insight.governance import (
    PredictionScenario,
    FeatureGovernanceRegistry,
    TargetProvenanceAuditor,
    ChronologicalValidationManager,
    load_authoritative_clean_data,
    generate_research_questions_document,
    run_governance_pipeline,
)


def test_registry_completeness_and_target_naming():
    reg = FeatureGovernanceRegistry()
    df = reg.to_dataframe()
    assert len(df) == 21
    assert "Original feature name" in df.columns
    assert "Clinical interpretation" in df.columns
    assert "Unresolved documentation requirements" in df.columns

    # Verify standardized target terminology
    target_row = df[df["Original feature name"] == "Output(failed implantation or successful implantation)"].iloc[0]
    assert target_row["Standardised feature name"] == "recorded_cycle_outcome"
    assert "implantation failure" in target_row["Clinical interpretation"].lower()
    assert "non-return of embryos" in target_row["Clinical interpretation"].lower()
    assert "biochemical" in target_row["Unresolved documentation requirements"].lower()


def test_scenario_candidate_predictors():
    reg = FeatureGovernanceRegistry()
    # Including conditional features (treatment protocol, sperm parameters)
    scen_a_cond = reg.get_candidate_predictors(PredictionScenario.SCENARIO_A, include_conditional=True)
    scen_b = reg.get_candidate_predictors(PredictionScenario.SCENARIO_B)
    scen_c = reg.get_candidate_predictors(PredictionScenario.SCENARIO_C)

    assert len(scen_a_cond) == 8
    assert len(scen_b) == 12
    assert len(scen_c) == 18

    # Scenario A features are subset of B, and B subset of C
    assert set(scen_a_cond).issubset(set(scen_b))
    assert set(scen_b).issubset(set(scen_c))

    # Without conditional features, Scenario A has only strictly confirmed baseline demographics/biomarkers
    scen_a_strict = reg.get_candidate_predictors(PredictionScenario.SCENARIO_A, include_conditional=False)
    assert len(scen_a_strict) == 4
    assert set(scen_a_strict) == {"Female Age", "Number of attempts", "AMH", "Male Age"}

    # Strict prohibitions across all scenarios
    for s in [scen_a_cond, scen_a_strict, scen_b, scen_c]:
        assert "β-HCG" not in s
        assert "Egg retrieval date" not in s
        assert "Output(failed implantation or successful implantation)" not in s


def test_validate_feature_set_leakage_detection():
    reg = FeatureGovernanceRegistry()

    # Valid scenario A features
    valid_a = ["Female Age", "AMH", "Male Age"]
    is_valid, violations = reg.validate_feature_set(PredictionScenario.SCENARIO_A, valid_a)
    assert is_valid is True
    assert len(violations) == 0

    # Leakage 1: β-HCG in feature set (Target leakage)
    leaked = ["Female Age", "AMH", "β-HCG"]
    is_valid, violations = reg.validate_feature_set(PredictionScenario.SCENARIO_A, leaked)
    assert is_valid is False
    assert any("CRITICAL LEAKAGE" in v for v in violations)

    # Leakage 2: Future feature in Scenario A
    premature = ["Female Age", "AMH", "Embryo Grade 1"]
    is_valid, violations = reg.validate_feature_set(PredictionScenario.SCENARIO_A, premature)
    assert is_valid is False
    assert any("UNAUTHORIZED FEATURE" in v for v in violations)


def test_target_provenance_auditor_subcohorts():
    df_synthetic = pd.DataFrame({
        "β-HCG": [
            "Non-return of embryos",
            "NEGATIVE(12)",
            "POSITIVE(1500)",
            "POSITIVE(35)",  # Discordant case: positive beta with target 0
        ],
        "Output(failed implantation or successful implantation)": [0.0, 0.0, 1.0, 0.0],
        "Female Age": [30, 32, 28, 35],
        "Egg retrieval date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
    })

    audit = TargetProvenanceAuditor.audit(df_synthetic)
    assert audit["target_variable_standardized"] == "recorded_cycle_outcome"
    assert audit["class_0_total"] == 3
    assert audit["class_1_total"] == 1

    # Sub-cohorts distinction
    class_0_subs = audit["class_0_subcohorts"]
    assert "cycles_without_embryo_transfer" in class_0_subs
    assert class_0_subs["cycles_without_embryo_transfer"]["count"] == 1
    assert "cycles_with_negative_pregnancy_test" in class_0_subs
    assert class_0_subs["cycles_with_negative_pregnancy_test"]["count"] == 1
    assert "cycles_with_discordant_positive_beta" in class_0_subs
    assert class_0_subs["cycles_with_discordant_positive_beta"]["count"] == 1
    assert class_0_subs["cycles_with_discordant_positive_beta"]["samples"][0]["parsed_num"] == 35.0

    # Uncertainty documentation
    assert "biochemical" in audit["clinical_uncertainty_statement"].lower()


def test_chronological_validation_split_safeguards():
    dates = pd.date_range("2023-01-01", periods=100, freq="7D")
    df_synthetic = pd.DataFrame({
        "Egg retrieval date": dates,
        "Output(failed implantation or successful implantation)": [i % 2 for i in range(100)],
        "Female Age": [30 + (i % 10) for i in range(100)],
    })

    train_df, test_df, meta = ChronologicalValidationManager.split(df_synthetic, cutoff="2024-01-01")

    # 1. Exact sample count match
    assert len(train_df) + len(test_df) == 100
    assert meta["train_size"] == len(train_df)
    assert meta["test_size"] == len(test_df)

    # 2. Strict temporal separation
    assert pd.to_datetime(train_df["Egg retrieval date"]).max() < pd.to_datetime("2024-01-01")
    assert pd.to_datetime(test_df["Egg retrieval date"]).min() >= pd.to_datetime("2024-01-01")

    # 3. Class distributions calculated separately
    assert "train_class_counts" in meta
    assert "test_class_counts" in meta
    assert "train_class_proportions" in meta
    assert "test_class_proportions" in meta
    assert sum(meta["train_class_counts"].values()) == len(train_df)
    assert sum(meta["test_class_counts"].values()) == len(test_df)

    # 4. Leakage and patient identity notices
    assert "NO CLAIM OF PATIENT-LEVEL SEPARATION" in meta["patient_identity_notice"]
    assert "leakage cannot be completely ruled out" in meta["repeated_cycle_leakage_warning"]


def test_chronological_validation_split_invalid_dates_fails():
    # DataFrame with missing/NaT date must fail validation
    df_invalid = pd.DataFrame({
        "Egg retrieval date": ["2023-01-01", None, "invalid_date_format"],
        "Output(failed implantation or successful implantation)": [0.0, 1.0, 0.0],
    })
    with pytest.raises(ValueError, match="missing or invalid 'Egg retrieval date'"):
        ChronologicalValidationManager.split(df_invalid)


def test_load_authoritative_clean_data_synthetic(tmp_path):
    patient_rows = [
        {"Female Age": 30 + i, "Number of attempts": "`1" if i == 0 else 2, "Egg retrieval date": "2021-01-01"}
        for i in range(10)
    ]
    boundary_rows = [
        {"Female Age": 20, "Number of attempts": 0, "Egg retrieval date": None},
        {"Female Age": 49, "Number of attempts": 10, "Egg retrieval date": None},
    ]
    df_all = pd.DataFrame(patient_rows + boundary_rows)
    excel_path = tmp_path / "test_data.xlsx"
    df_all.to_excel(excel_path, index=False)

    df_clean = load_authoritative_clean_data(excel_path)
    assert df_clean["Number of attempts"].iloc[0] == 1
    assert pd.api.types.is_datetime64_any_dtype(df_clean["Egg retrieval date"])


def test_generate_research_questions_document(tmp_path):
    output_file = tmp_path / "research_questions.md"
    generate_research_questions_document(output_file)

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "Exact Definition of Implantation Success" in content
    assert "Non-return of embryos" in content
    assert "AMH" in content
    assert "182 Treatment Protocol Identifiers" in content
    assert "Sperm Measurements" in content
    assert "Patient Linkage" in content
