import pandas as pd
from ivf_insight.statistics import univariate_associations


def test_univariate_associations_writes_adjusted_results(tmp_path):
    df = pd.DataFrame({
        "age": [25, 26, 27, 38, 39, 40, 28, 29, 41, 42, 30, 43],
        "protocol": ["A", "A", "B", "B", "B", "A", "A", "B", "B", "A", "A", "B"],
        "outcome": [0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1],
    })
    out = tmp_path / "stats.csv"
    result = univariate_associations(df, "outcome", out)
    assert out.exists()
    assert "q_value_bh" in result.columns
    assert set(result["test"]).issubset({"Mann-Whitney U", "Chi-square"})
