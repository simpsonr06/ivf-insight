import json
import numpy as np
import pandas as pd
import pytest

from ivf_insight.reconciliation import DatasetReconciler


@pytest.fixture
def synthetic_datasets(tmp_path):
    """Generate synthetic Excel-like and CSV-like datasets for testing reconciliation."""
    n_patients = 100
    np.random.seed(42)

    # Patient records (100 rows)
    female_age = np.random.randint(22, 45, size=n_patients)
    male_age = np.random.randint(25, 55, size=n_patients)
    amh = np.round(np.random.uniform(0.5, 12.0, size=n_patients), 2)
    attempts = np.random.choice([1, 2, 3, 4], size=n_patients)
    # Introduce typo in attempts
    attempts_str = [str(x) for x in attempts]
    attempts_str[0] = "`1"

    meds = np.random.randint(1, 50, size=n_patients)
    dates = pd.date_range("2021-01-01", periods=n_patients, freq="2D")
    outcome = np.random.choice([0, 1], size=n_patients)

    # Shared numeric features
    features_dict = {
        "Female Age": list(female_age),
        "Number of attempts": attempts_str,
        "AMH": list(amh),
        "Medicines and treatments": list(meds),
        "Egg retrieval date": list(dates),
        "Oocyte Maturity MII": list(np.random.randint(0, 20, size=n_patients)),
        "Oocyte Maturity MI": list(np.random.randint(0, 10, size=n_patients)),
        "Oocyte Maturity others": list(np.random.randint(0, 5, size=n_patients)),
        "Male Age": list(male_age),
        "Sperm count": list(np.round(np.random.uniform(5, 90, size=n_patients), 1)),
        "Sperm motility": list(np.round(np.random.uniform(10, 80, size=n_patients), 1)),
        "Sperm morphology": list(np.round(np.random.uniform(1, 3, size=n_patients), 1)),
        "Number of fertilized eggs": list(np.random.randint(0, 15, size=n_patients)),
        "Embryo Grade 1": list(np.random.randint(0, 8, size=n_patients)),
        "Embryo Grade 2": list(np.random.randint(0, 8, size=n_patients)),
        "Embryo Grade 3": list(np.random.randint(0, 4, size=n_patients)),
        "Embryo Grade 4": list(np.random.randint(0, 2, size=n_patients)),
        "Number of embryos": list(np.random.randint(0, 6, size=n_patients)),
        "frezzing": list(np.random.randint(0, 10, size=n_patients)),
        "β-HCG": [
            "Non-return of embryos" if i % 10 == 0 else f"POSITIVE({100 + i * 10})" if outcome[i] == 1 else f"NEGATIVE({i + 1})"
            for i in range(n_patients)
        ],
        "Output(failed implantation or successful implantation)": [float(x) for x in outcome],
    }

    df_excel_patients = pd.DataFrame(features_dict)

    # Compute min and max bounds for synthetic tail rows
    tail_min = {}
    tail_max = {}
    for col in DatasetReconciler.NORMALIZED_NUMERIC_FEATURES:
        if col == "Number of attempts":
            clean_s = DatasetReconciler.clean_attempts_series(df_excel_patients[col])
        else:
            clean_s = pd.to_numeric(df_excel_patients[col], errors="coerce")
        tail_min[col] = clean_s.min()
        tail_max[col] = clean_s.max()

    tail_min["Egg retrieval date"] = pd.NaT
    tail_min["β-HCG"] = np.nan
    tail_min["Output(failed implantation or successful implantation)"] = np.nan

    tail_max["Egg retrieval date"] = pd.NaT
    tail_max["β-HCG"] = np.nan
    tail_max["Output(failed implantation or successful implantation)"] = np.nan

    df_tail = pd.DataFrame([tail_min, tail_max])
    df_excel = pd.concat([df_excel_patients, df_tail], ignore_index=True)

    # Generate matching normalized CSV
    df_csv = pd.DataFrame()
    for col in DatasetReconciler.NORMALIZED_NUMERIC_FEATURES:
        if col == "Number of attempts":
            v = DatasetReconciler.clean_attempts_series(df_excel_patients[col])
        else:
            v = pd.to_numeric(df_excel_patients[col], errors="coerce")
        mn = tail_min[col]
        mx = tail_max[col]
        df_csv[col] = (v - mn) / (mx - mn)

    # Date normalization: (day_of_year - 1) / 365
    df_csv["Egg retrieval date"] = (pd.to_datetime(df_excel_patients["Egg retrieval date"]).dt.dayofyear - 1) / 365.0
    
    # Beta-HCG: / 6800.0 or 0 for non-return
    def norm_beta(v):
        num, cat = DatasetReconciler.parse_beta_hcg(v)
        return (num / 6800.0) if cat != "non_return_of_embryos" else 0.0

    df_csv["?-HCG"] = df_excel_patients["β-HCG"].apply(norm_beta)
    df_csv["Output (Output(failed implantation or successful implantation)"] = outcome

    # Reorder CSV columns to match expected order
    csv_cols = list(DatasetReconciler.NORMALIZED_NUMERIC_FEATURES)
    csv_cols.insert(4, "Egg retrieval date")
    csv_cols.append("?-HCG")
    csv_cols.append("Output (Output(failed implantation or successful implantation)")
    df_csv = df_csv[csv_cols]

    excel_file = tmp_path / "synthetic_clean.xlsx"
    csv_file = tmp_path / "synthetic_norm.csv"
    df_excel.to_excel(excel_file, index=False)
    df_csv.to_csv(csv_file, index=False)

    return excel_file, csv_file, n_patients


def test_clean_attempts_series():
    s = pd.Series(["`1", " 2 ", "3", "`1", 4])
    cleaned = DatasetReconciler.clean_attempts_series(s)
    assert cleaned.tolist() == [1.0, 2.0, 3.0, 1.0, 4.0]
    assert cleaned.isna().sum() == 0


def test_parse_beta_hcg():
    cases = [
        ("Non-return of embryos", 0.0, "non_return_of_embryos"),
        ("NEGATIVE", 0.0, "negative_unquantified"),
        ("NEGATIVE(14)", 14.0, "negative"),
        ("POSITIVE(1400)", 1400.0, "positive"),
        (np.nan, np.nan, "missing"),
    ]
    for raw, expected_num, expected_cat in cases:
        num, cat = DatasetReconciler.parse_beta_hcg(raw)
        if np.isnan(expected_num):
            assert np.isnan(num)
        else:
            assert num == expected_num
        assert cat == expected_cat


def test_identify_boundary_rows(synthetic_datasets):
    excel_path, csv_path, n_patients = synthetic_datasets
    reconciler = DatasetReconciler(excel_path, csv_path)
    res = reconciler.identify_boundary_rows()
    assert res["boundary_rows_detected"] is True
    assert res["boundary_indices"] == [100, 101]


def test_normalization_audit(synthetic_datasets):
    excel_path, csv_path, _ = synthetic_datasets
    reconciler = DatasetReconciler(excel_path, csv_path)
    bounds = reconciler.identify_boundary_rows()
    res = reconciler.audit_normalization(bounds)
    assert res["all_features_match_formula"] is True
    for feat, data in res["feature_details"].items():
        assert data["max_residual"] < 1e-4


def test_order_agnostic_comparison(synthetic_datasets):
    excel_path, csv_path, _ = synthetic_datasets
    reconciler = DatasetReconciler(excel_path, csv_path)
    bounds = reconciler.identify_boundary_rows()
    res = reconciler.compare_records_order_agnostic(bounds)
    assert res["multiset_order_agnostic_equality"] is True
    assert res["sequential_row_order_identical"] is True


def test_full_reconciliation_reports(synthetic_datasets, tmp_path):
    excel_path, csv_path, _ = synthetic_datasets
    out_dir = tmp_path / "reports_out"
    reconciler = DatasetReconciler(excel_path, csv_path)
    res = reconciler.run_and_save(out_dir)

    assert (out_dir / "dataset_comparison.json").exists()
    assert (out_dir / "data_quality_summary.csv").exists()
    assert (out_dir / "dataset_comparison.md").exists()

    # Verify JSON content
    data = json.loads((out_dir / "dataset_comparison.json").read_text(encoding="utf-8"))
    assert data["summary"]["row_count_diff"] == 2
    assert data["summary"]["multiset_order_agnostic_match"] is True

    # Verify CSV summary
    summary_df = pd.read_csv(out_dir / "data_quality_summary.csv")
    assert len(summary_df) == 21
    assert "excel_feature" in summary_df.columns
    assert "reconciliation_notes" in summary_df.columns

    # Verify Markdown
    md_text = (out_dir / "dataset_comparison.md").read_text(encoding="utf-8")
    assert "# IVF Insight: Dataset Reconciliation & Data Quality Forensic Audit" in md_text
    assert "CORE VERDICT:" in md_text
