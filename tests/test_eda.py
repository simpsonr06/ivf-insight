"""Unit and integration tests for Phase 3 Exploratory Data Analysis (EDA) module."""

from pathlib import Path
import pandas as pd
import pytest

from ivf_insight.eda import (
    load_clean_cohorts,
    compute_descriptive_statistics,
    compute_statistical_associations,
    analyze_data_quality_anomalies,
    generate_eda_figures,
    run_eda_pipeline,
    TARGET_COL,
    BETA_COL,
)


def test_load_clean_cohorts_authoritative():
    excel_path = Path("data/raw/Dataset Clean.xlsx")
    df_full, df_transfer = load_clean_cohorts(excel_path)

    # 1. Row count verification
    assert len(df_full) == 5000
    assert len(df_transfer) == 3750

    # 2. Non-return exclusion in transfer cohort
    assert (df_transfer[BETA_COL] == "Non-return of embryos").sum() == 0
    assert (df_full[BETA_COL] == "Non-return of embryos").sum() == 1250

    # 3. Clean columns present
    assert "Female Age" in df_full.columns
    assert "AMH" in df_full.columns
    assert TARGET_COL in df_full.columns


def test_compute_descriptive_statistics_synthetic():
    # Synthetic dataframe with 20 rows
    df_full = pd.DataFrame({
        "Female Age": [30 + (i % 10) for i in range(20)],
        "AMH": [1.5 + (i * 0.2) for i in range(20)],
        "Medicines and treatments": [1 if i % 2 == 0 else 2 for i in range(20)],
        BETA_COL: ["Non-return of embryos"] * 5 + ["POSITIVE"] * 15,
        TARGET_COL: [0.0] * 5 + [1.0] * 10 + [0.0] * 5,
    })
    df_transfer = df_full[df_full[BETA_COL] != "Non-return of embryos"].copy()

    desc_df = compute_descriptive_statistics(df_full, df_transfer)

    assert not desc_df.empty
    assert "Cohort" in desc_df.columns
    assert "Standardized Name" in desc_df.columns
    assert "IQR" in desc_df.columns
    assert "Skewness" in desc_df.columns

    # Verify both cohorts represented
    cohorts_present = set(desc_df["Cohort"])
    assert any("Full-Cycle" in c for c in cohorts_present)
    assert any("Embryo-Transfer" in c for c in cohorts_present)


def test_compute_statistical_associations_synthetic():
    df_full = pd.DataFrame({
        "Female Age": [25, 26, 27, 28, 35, 36, 37, 38],
        "AMH": [2.0, 2.5, 3.0, 3.5, 0.5, 0.8, 1.0, 1.2],
        "Medicines and treatments": [1, 1, 1, 1, 2, 2, 2, 2],
        BETA_COL: ["POSITIVE"] * 8,
        TARGET_COL: [1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    })
    df_transfer = df_full.copy()

    stats_df = compute_statistical_associations(df_full, df_transfer)

    assert not stats_df.empty
    assert "p_value" in stats_df.columns
    assert "q_value_bh" in stats_df.columns
    assert "effect_size" in stats_df.columns

    # Verify all q-values in valid probability range
    assert (stats_df["q_value_bh"] >= 0.0).all()
    assert (stats_df["q_value_bh"] <= 1.0).all()

    # For continuous features, Mann-Whitney U test was performed
    fem_row = stats_df[stats_df["feature"] == "Female Age"].iloc[0]
    assert fem_row["test_type"] == "Mann-Whitney U"
    assert fem_row["effect_size_metric"] == "Rank-Biserial Correlation (r)"

    # For categorical feature, Chi-Square was performed
    proto_row = stats_df[stats_df["feature"] == "Medicines and treatments"].iloc[0]
    assert proto_row["test_type"] == "Chi-Square Independence"
    assert proto_row["effect_size_metric"] == "Cramer's V"


def test_analyze_data_quality_anomalies_authoritative():
    df_full, _ = load_clean_cohorts("data/raw/Dataset Clean.xlsx")
    quality = analyze_data_quality_anomalies(df_full)

    # 1. AMH extremes
    assert quality["amh_extremes"]["count_equal_482_1"] == 3
    assert quality["amh_extremes"]["max"] == 482.1

    # 2. Protocol cardinality
    assert quality["protocol_cardinality"]["unique_protocols"] == 182
    assert quality["protocol_cardinality"]["top_protocol_id"] == 1
    assert quality["protocol_cardinality"]["top_protocol_count"] == 816

    # 3. Oocyte and embryo consistency
    assert quality["oocyte_embryo_consistency"]["fertilized_greater_than_mii"] == 549
    assert quality["oocyte_embryo_consistency"]["fertilized_greater_than_total_oocytes"] == 12

    # 4. Repeated cycles
    assert quality["repeated_cycle_clusters"]["cycles_in_potential_clusters"] > 0


def test_generate_eda_figures_synthetic(tmp_path):
    # Create small synthetic dataframe with required columns
    dates = pd.date_range("2020-01-01", periods=30, freq="30D")
    df_synth = pd.DataFrame({
        "Female Age": [30 + (i % 10) for i in range(30)],
        "Male Age": [33 + (i % 10) for i in range(30)],
        "Number of attempts": [1] * 30,
        "AMH": [1.0 + (i * 0.1) for i in range(30)],
        "Medicines and treatments": [1 if i % 2 == 0 else 2 for i in range(30)],
        "Sperm count": [30.0 + i for i in range(30)],
        "Sperm motility": [0.4 + (i * 0.01) for i in range(30)],
        "Sperm morphology": [0.02] * 30,
        "Oocyte Maturity MII": [5 + (i % 5) for i in range(30)],
        "Oocyte Maturity MI": [1] * 30,
        "Oocyte Maturity others": [1] * 30,
        "Number of fertilized eggs": [4 + (i % 4) for i in range(30)],
        "Embryo Grade 1": [2] * 30,
        "Embryo Grade 2": [1] * 30,
        "Embryo Grade 3": [0] * 30,
        "Embryo Grade 4": [0] * 30,
        "Number of embryos": [2] * 30,
        "frezzing": [1 if i % 2 == 0 else 0 for i in range(30)],
        "Egg retrieval date": dates,
        BETA_COL: ["Non-return of embryos"] * 5 + ["POSITIVE"] * 25,
        TARGET_COL: [0.0] * 5 + [1.0] * 20 + [0.0] * 5,
    })
    df_transfer = df_synth[df_synth[BETA_COL] != "Non-return of embryos"].copy()

    figs_dir = tmp_path / "figures"
    generated = generate_eda_figures(df_synth, df_transfer, figs_dir)

    assert len(generated) == 9
    for p in generated:
        assert p.exists()
        assert p.stat().st_size > 0


def test_run_eda_pipeline_integration(tmp_path):
    # Run full pipeline with output directed to tmp_path
    excel_path = Path("data/raw/Dataset Clean.xlsx")
    res = run_eda_pipeline(excel_path=excel_path, output_dir=tmp_path)

    assert res["status"] == "success"
    assert res["full_cohort_size"] == 5000
    assert res["embryo_transfer_cohort_size"] == 3750
    assert Path(res["descriptive_statistics_csv"]).exists()
    assert Path(res["statistical_tests_csv"]).exists()
    assert Path(res["eda_summary_md"]).exists()
    assert res["figures_count"] == 9
