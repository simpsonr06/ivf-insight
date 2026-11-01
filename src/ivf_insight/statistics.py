from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu
from statsmodels.stats.multitest import multipletests


def univariate_associations(df: pd.DataFrame, target: str, output_path: str | Path) -> pd.DataFrame:
    """Exploratory univariate tests against a binary outcome with BH-FDR correction.

    Numeric features: Mann–Whitney U between the two outcome groups.
    Categorical features: chi-square test of independence.
    """
    if target not in df.columns:
        raise ValueError(f"Target '{target}' not found.")
    data = df.dropna(subset=[target]).copy()
    classes = list(pd.unique(data[target]))
    if len(classes) != 2:
        raise ValueError("Univariate association tests require exactly two non-missing target classes.")
    rows = []
    for col in data.columns:
        if col == target:
            continue
        subset = data[[col, target]].dropna()
        if subset[col].nunique() < 2:
            continue
        try:
            if pd.api.types.is_numeric_dtype(subset[col]) and not pd.api.types.is_bool_dtype(subset[col]):
                a = subset.loc[subset[target] == classes[0], col].astype(float)
                b = subset.loc[subset[target] == classes[1], col].astype(float)
                if len(a) and len(b):
                    stat, p = mannwhitneyu(a, b, alternative="two-sided")
                    rows.append({"feature": col, "test": "Mann-Whitney U", "statistic": float(stat), "p_value": float(p), "n": int(len(subset)), "group_0_median": float(a.median()), "group_1_median": float(b.median())})
            else:
                table = pd.crosstab(subset[col].astype(str), subset[target].astype(str))
                if table.shape[0] < 2 or table.shape[1] != 2:
                    continue
                chi2, p, dof, expected = chi2_contingency(table)
                rows.append({"feature": col, "test": "Chi-square", "statistic": float(chi2), "p_value": float(p), "n": int(table.to_numpy().sum()), "degrees_of_freedom": int(dof)})
        except (ValueError, TypeError, FloatingPointError):
            continue
    result = pd.DataFrame(rows)
    if not result.empty:
        result["q_value_bh"] = multipletests(result["p_value"], method="fdr_bh")[1]
        result = result.sort_values("q_value_bh", ascending=True)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result
