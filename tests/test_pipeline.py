import pandas as pd
from ivf_insight.analysis import data_quality_report
from ivf_insight.modeling import train_and_evaluate


def sample_data(n=120):
    return pd.DataFrame({
        "age": [25 + (i % 18) for i in range(n)],
        "amh": [1.0 + (i % 10) * 0.2 if i % 13 else None for i in range(n)],
        "protocol": ["A" if i % 2 else "B" for i in range(n)],
        "implantation_success": [i % 2 for i in range(n)],
        "record_id": [f"id-{i}" for i in range(n)],
    })


def test_quality_report(tmp_path):
    df = sample_data()
    report = data_quality_report(df, "implantation_success", tmp_path)
    assert report["rows"] == 120
    assert report["target"] == "implantation_success"
    assert (tmp_path / "data_quality.json").exists()


def test_model_training(tmp_path):
    result = train_and_evaluate(
        sample_data(), "implantation_success", tmp_path,
        drop_columns=["record_id"], positive_label="1"
    )
    assert result["selected_model_by_training_cv_roc_auc"] in {"logistic_regression", "random_forest"}
    assert (tmp_path / "best_model.joblib").exists()
    assert result["test_rows"] == 24
