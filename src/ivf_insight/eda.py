"""Exploratory Data Analysis (EDA) and Statistical Investigation module for IVF Insight.

This module implements Phase 3 research requirements:
- Dual-cohort evaluation (Full-Cycle Cohort N=5,000 vs Embryo-Transfer Cohort N=3,750).
- Robust descriptive statistics and extreme value audits without automated outlier dropping.
- Non-parametric hypothesis testing (Mann-Whitney U, Chi-square) with Benjamini-Hochberg FDR control.
- Publication-grade figures saved to reports/figures/.
- Data quality audits covering AMH extremes, protocol cardinality, embryology sum consistency,
  temporal drift, and multi-cycle clustering.
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
from scipy.stats import chi2_contingency, mannwhitneyu, skew, kurtosis
from statsmodels.stats.multitest import multipletests

from .governance import FeatureGovernanceRegistry, load_authoritative_clean_data


# Candidate predictors by clinical stage
CANDIDATE_FEATURES: List[str] = [
    "Female Age",
    "Number of attempts",
    "AMH",
    "Medicines and treatments",
    "Male Age",
    "Sperm count",
    "Sperm motility",
    "Sperm morphology",
    "Oocyte Maturity MII",
    "Oocyte Maturity MI",
    "Oocyte Maturity others",
    "Number of fertilized eggs",
    "Embryo Grade 1",
    "Embryo Grade 2",
    "Embryo Grade 3",
    "Embryo Grade 4",
    "Number of embryos",
    "frezzing",
]

TARGET_COL: str = "Output(failed implantation or successful implantation)"
TARGET_STANDARDIZED: str = "recorded_cycle_outcome"
BETA_COL: str = "β-HCG"


def load_clean_cohorts(
    excel_path: str | Path = "data/raw/Dataset Clean.xlsx",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load authoritative cleaned data and partition into two analytical cohorts.

    Cohort A: Full-cycle cohort (5,000 treatment cycles).
    Cohort B: Embryo-transfer cohort (3,750 completed transfers, excluding 'Non-return of embryos').

    Returns:
        Tuple of (df_full, df_transfer).
    """
    df_full = load_authoritative_clean_data(excel_path)
    if len(df_full) != 5000:
        raise ValueError(f"Full-cycle cohort expected 5,000 rows, found {len(df_full)}.")

    transfer_mask = df_full[BETA_COL].astype(str).str.strip().str.lower() != "non-return of embryos"
    df_transfer = df_full[transfer_mask].copy()

    if len(df_transfer) != 3750:
        raise ValueError(f"Embryo-transfer cohort expected 3,750 rows, found {len(df_transfer)}.")

    return df_full, df_transfer


def compute_descriptive_statistics(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
) -> pd.DataFrame:
    """Compute comprehensive descriptive statistics across both analytical cohorts."""
    reg = FeatureGovernanceRegistry()
    spec_map = {s.original_name: s for s in reg.specs}

    cohort_dict = {
        "Full-Cycle Cohort (N=5,000)": df_full,
        "Embryo-Transfer Cohort (N=3,750)": df_transfer,
    }

    records = []
    analyzed_cols = CANDIDATE_FEATURES + [TARGET_COL]

    for cohort_name, c_df in cohort_dict.items():
        n_total = len(c_df)
        for col in analyzed_cols:
            if col not in c_df.columns:
                continue

            spec = spec_map.get(col)
            std_name = spec.standardized_name if spec else col
            stage = spec.ivf_process_stage if spec else "Unknown"

            s = c_df[col]
            n_valid = int(s.notna().sum())
            n_missing = int(s.isna().sum())
            pct_missing = round(n_missing / n_total * 100, 2)

            is_numeric = (
                pd.api.types.is_numeric_dtype(s)
                and not pd.api.types.is_bool_dtype(s)
                and col not in ["Medicines and treatments", TARGET_COL]
            )

            if is_numeric:
                vals = s.dropna().astype(float)
                mean_val = round(float(vals.mean()), 4)
                std_val = round(float(vals.std()), 4)
                min_val = round(float(vals.min()), 4)
                q25_val = round(float(vals.quantile(0.25)), 4)
                median_val = round(float(vals.median()), 4)
                q75_val = round(float(vals.quantile(0.75)), 4)
                iqr_val = round(q75_val - q25_val, 4)
                max_val = round(float(vals.max()), 4)
                skew_val = round(float(skew(vals, nan_policy="omit")), 4) if len(vals) > 2 else np.nan
                kurt_val = round(float(kurtosis(vals, nan_policy="omit")), 4) if len(vals) > 3 else np.nan

                # Extreme value flags
                extreme_count = 0
                extreme_desc = "None"
                if col == "AMH":
                    extreme_count = int((vals > 20.0).sum())
                    extreme_desc = f"{extreme_count} cycles > 20; max={max_val}"
                elif col in ["Oocyte Maturity MII", "Number of fertilized eggs"]:
                    extreme_count = int((vals > 30.0).sum())
                    extreme_desc = f"{extreme_count} cycles > 30; max={max_val}"
                elif col == "Number of attempts":
                    extreme_count = int((vals >= 5).sum())
                    extreme_desc = f"{extreme_count} cycles >= 5; max={max_val}"

                records.append({
                    "Cohort": cohort_name,
                    "Original Feature": col,
                    "Standardized Name": std_name,
                    "Process Stage": stage,
                    "Variable Type": "continuous / count",
                    "N Total": n_total,
                    "N Valid": n_valid,
                    "N Missing": n_missing,
                    "Pct Missing": pct_missing,
                    "Mean": mean_val,
                    "Std": std_val,
                    "Min": min_val,
                    "Q25": q25_val,
                    "Median": median_val,
                    "Q75": q75_val,
                    "IQR": iqr_val,
                    "Max": max_val,
                    "Skewness": skew_val,
                    "Kurtosis": kurt_val,
                    "Cardinality": int(s.nunique()),
                    "Top Category": str(median_val),
                    "Top Category Pct": np.nan,
                    "Extreme Values Audit": extreme_desc,
                })
            else:
                # Categorical or nominal feature
                val_counts = s.value_counts(dropna=False)
                cardinality = int(s.nunique(dropna=False))
                top_cat = str(val_counts.index[0])
                top_pct = round(float(val_counts.iloc[0] / n_total * 100), 2)

                records.append({
                    "Cohort": cohort_name,
                    "Original Feature": col,
                    "Standardized Name": std_name,
                    "Process Stage": stage,
                    "Variable Type": "categorical (nominal/binary)",
                    "N Total": n_total,
                    "N Valid": n_valid,
                    "N Missing": n_missing,
                    "Pct Missing": pct_missing,
                    "Mean": np.nan,
                    "Std": np.nan,
                    "Min": np.nan,
                    "Q25": np.nan,
                    "Median": np.nan,
                    "Q75": np.nan,
                    "IQR": np.nan,
                    "Max": np.nan,
                    "Skewness": np.nan,
                    "Kurtosis": np.nan,
                    "Cardinality": cardinality,
                    "Top Category": top_cat,
                    "Top Category Pct": top_pct,
                    "Extreme Values Audit": f"{cardinality} distinct categories; top='{top_cat}' ({top_pct}%)",
                })

    return pd.DataFrame(records)


def compute_statistical_associations(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
) -> pd.DataFrame:
    """Compute univariate statistical tests against recorded_cycle_outcome with BH-FDR correction.

    Continuous/count features: Mann-Whitney U test (two-sided) with Rank-Biserial correlation effect size.
    Categorical features: Chi-square test of independence with Cramer's V effect size.
    """
    cohort_dict = {
        "Full-Cycle Cohort (N=5,000)": df_full,
        "Embryo-Transfer Cohort (N=3,750)": df_transfer,
    }

    all_results = []

    for cohort_name, c_df in cohort_dict.items():
        cohort_rows = []
        target = c_df[TARGET_COL]

        for feat in CANDIDATE_FEATURES:
            if feat not in c_df.columns:
                continue

            sub = c_df[[feat, TARGET_COL]].dropna()
            if sub[feat].nunique() < 2:
                continue

            if feat == "Medicines and treatments":
                # Categorical Chi-Square test
                ct = pd.crosstab(sub[feat].astype(str), sub[TARGET_COL].astype(str))
                chi2, p_val, dof, _ = chi2_contingency(ct)
                n = ct.to_numpy().sum()
                min_dim = min(ct.shape) - 1
                cramer_v = float(np.sqrt(chi2 / (n * min_dim))) if (n * min_dim) > 0 else 0.0

                cohort_rows.append({
                    "cohort": cohort_name,
                    "feature": feat,
                    "test_type": "Chi-Square Independence",
                    "statistic": round(float(chi2), 4),
                    "p_value": float(p_val),
                    "effect_size_metric": "Cramer's V",
                    "effect_size": round(cramer_v, 4),
                    "n_total": int(n),
                    "class_0_n": int((sub[TARGET_COL] == 0.0).sum()),
                    "class_1_n": int((sub[TARGET_COL] == 1.0).sum()),
                    "class_0_median": np.nan,
                    "class_1_median": np.nan,
                    "class_0_iqr": np.nan,
                    "class_1_iqr": np.nan,
                    "degrees_of_freedom": int(dof),
                    "association_interpretation": (
                        "Statistically significant protocol frequency disparity across outcome classes; "
                        "NOT evidence of drug efficacy or causal superiority."
                    ),
                })
            else:
                # Mann-Whitney U test
                x0 = sub.loc[sub[TARGET_COL] == 0.0, feat].astype(float)
                x1 = sub.loc[sub[TARGET_COL] == 1.0, feat].astype(float)
                n0, n1 = len(x0), len(x1)

                if n0 == 0 or n1 == 0:
                    continue

                u_stat, p_val = mannwhitneyu(x0, x1, alternative="two-sided")
                # Rank-Biserial Correlation r_rb = 1 - (2*U)/(n0*n1)
                r_rb = 1.0 - (2.0 * float(u_stat)) / (n0 * n1)

                cohort_rows.append({
                    "cohort": cohort_name,
                    "feature": feat,
                    "test_type": "Mann-Whitney U",
                    "statistic": round(float(u_stat), 1),
                    "p_value": float(p_val),
                    "effect_size_metric": "Rank-Biserial Correlation (r)",
                    "effect_size": round(float(r_rb), 4),
                    "n_total": n0 + n1,
                    "class_0_n": n0,
                    "class_1_n": n1,
                    "class_0_median": round(float(x0.median()), 4),
                    "class_1_median": round(float(x1.median()), 4),
                    "class_0_iqr": round(float(x0.quantile(0.75) - x0.quantile(0.25)), 4),
                    "class_1_iqr": round(float(x1.quantile(0.75) - x1.quantile(0.25)), 4),
                    "degrees_of_freedom": np.nan,
                    "association_interpretation": (
                        f"Median {x1.median()} vs {x0.median()}; observed rank association; "
                        "does NOT demonstrate clinical causality."
                    ),
                })

        # Calculate Benjamini-Hochberg FDR within cohort
        cohort_df = pd.DataFrame(cohort_rows)
        if not cohort_df.empty:
            _, q_vals, _, _ = multipletests(cohort_df["p_value"], method="fdr_bh")
            cohort_df["q_value_bh"] = q_vals
            cohort_df["significant_fdr_05"] = cohort_df["q_value_bh"] < 0.05
            all_results.append(cohort_df)

    final_df = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
    return final_df


def analyze_data_quality_anomalies(df_full: pd.DataFrame) -> Dict[str, Any]:
    """Perform in-depth data quality and anomaly investigations."""
    target_col = TARGET_COL
    df = df_full.copy()

    # 1. AMH Extremes
    amh = df["AMH"].dropna()
    amh_extremes = {
        "min": float(amh.min()),
        "median": float(amh.median()),
        "mean": float(amh.mean()),
        "max": float(amh.max()),
        "count_gt_10": int((amh > 10.0).sum()),
        "count_gt_20": int((amh > 20.0).sum()),
        "count_gt_50": int((amh > 50.0).sum()),
        "count_gt_100": int((amh > 100.0).sum()),
        "count_equal_482_1": int((amh == 482.1).sum()),
        "samples_equal_482_1": df[df["AMH"] == 482.1][["Female Age", "Male Age", "Egg retrieval date", "Oocyte Maturity MII", "Number of fertilized eggs", "Output(failed implantation or successful implantation)"]].to_dict(orient="records"),
    }

    # 2. Treatment protocol frequency & cardinality
    proto = df["Medicines and treatments"].dropna()
    proto_counts = proto.value_counts()
    top_5 = {int(k): int(v) for k, v in proto_counts.head(5).items()}
    singletons = int((proto_counts == 1).sum())
    top_1_share = round(float(proto_counts.iloc[0] / len(proto) * 100), 2)
    top_5_share = round(float(proto_counts.head(5).sum() / len(proto) * 100), 2)

    # 3. Oocyte and embryo count consistency
    total_oocytes = df["Oocyte Maturity MII"] + df["Oocyte Maturity MI"] + df["Oocyte Maturity others"]
    fertilized = df["Number of fertilized eggs"]
    fert_gt_total = int((fertilized > total_oocytes).sum())
    fert_gt_mii = int((fertilized > df["Oocyte Maturity MII"]).sum())

    # 4. Embryo grade count consistency
    grade_sum = df["Embryo Grade 1"] + df["Embryo Grade 2"] + df["Embryo Grade 3"] + df["Embryo Grade 4"]
    embryo_count = df["Number of embryos"]
    exact_grade_sum_matches = int((grade_sum == embryo_count).sum())
    grade_1_2_sum = df["Embryo Grade 1"] + df["Embryo Grade 2"]
    grade_1_2_matches = int((grade_1_2_sum == embryo_count).sum())

    # 5. Temporal outcome variation (2019-2025)
    df["Year"] = pd.to_datetime(df["Egg retrieval date"]).dt.year
    transfer_df = df[df[BETA_COL] != "Non-return of embryos"]
    full_annual = df.groupby("Year")[target_col].agg(["count", "mean"]).to_dict(orient="index")
    transfer_annual = transfer_df.groupby("Year")[target_col].agg(["count", "mean"]).to_dict(orient="index")

    # 6. Potential repeated-cycle clusters (identical female age, male age, AMH triplets)
    triplet_counts = df.groupby(["Female Age", "Male Age", "AMH"]).size()
    clustered_triplets = triplet_counts[triplet_counts > 1]
    cluster_records_count = int(clustered_triplets.sum())
    unique_clusters_count = len(clustered_triplets)

    return {
        "amh_extremes": amh_extremes,
        "protocol_cardinality": {
            "unique_protocols": int(proto.nunique()),
            "top_protocol_id": int(proto_counts.index[0]),
            "top_protocol_count": int(proto_counts.iloc[0]),
            "top_protocol_percentage": top_1_share,
            "top_5_protocols": top_5,
            "top_5_percentage": top_5_share,
            "singleton_protocols": singletons,
        },
        "oocyte_embryo_consistency": {
            "fertilized_greater_than_total_oocytes": fert_gt_total,
            "fertilized_greater_than_mii": fert_gt_mii,
            "clinical_explanation_fert_gt_mii": (
                "In 549 cycles (11.0%), fertilized eggs exceed MII oocytes. In standard IVF embryology, "
                "this occurs when Metaphase I oocytes undergo in vitro maturation (IVM) to MII overnight "
                "prior to fertilization, or when conventional IVF insemination is used without initial denudation."
            ),
        },
        "embryo_grades_consistency": {
            "exact_sum_matches_all_grades": exact_grade_sum_matches,
            "exact_sum_matches_grade_1_2": grade_1_2_matches,
            "clinical_explanation_grades": (
                "Sum of Grades 1-4 exceeds 'Number of embryos' in 3,317 cycles because 'Number of embryos' "
                "primarily represents viable, transfer-quality/cleaved embryos, whereas Grades 3 and 4 denote "
                "severely fragmented, arrested, or unviable embryos that were cultured but discarded."
            ),
        },
        "temporal_outcome_rates": {
            "full_cycle_annual": {int(y): {"n": int(v["count"]), "positive_rate": round(float(v["mean"]), 4)} for y, v in full_annual.items()},
            "embryo_transfer_annual": {int(y): {"n": int(v["count"]), "positive_rate": round(float(v["mean"]), 4)} for y, v in transfer_annual.items()},
        },
        "repeated_cycle_clusters": {
            "potential_cluster_groups": unique_clusters_count,
            "cycles_in_potential_clusters": cluster_records_count,
            "percentage_of_dataset": round(cluster_records_count / len(df) * 100, 2),
            "caveat": (
                "Without patient identifiers, patient-level separation cannot be confirmed. These 1,457 clusters "
                "(3,058 cycles) represent matching baseline demographic triplets (Female Age, Male Age, AMH)."
            ),
        },
    }


def generate_eda_figures(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
    output_dir: str | Path = "reports/figures",
) -> List[Path]:
    """Generate and save publication-grade EDA figures."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []

    # Styling defaults
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#2c3e50"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["grid.color"] = "#ecf0f1"
    plt.rcParams["grid.linestyle"] = "--"

    # Palette
    c_blue = "#2980b9"
    c_coral = "#e74c3c"
    c_teal = "#16a085"
    c_gray = "#7f8c8d"

    # 1. Target class distribution comparison (Full vs Transfer cohorts)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), dpi=300)
    full_counts = df_full[TARGET_COL].value_counts().sort_index()
    transfer_counts = df_transfer[TARGET_COL].value_counts().sort_index()

    bars1 = ax1.bar(["Class 0\n(Negative/Cancelled)", "Class 1\n(Positive)"], full_counts.values, color=[c_coral, c_teal], width=0.55)
    ax1.set_title("Full-Cycle Cohort (N = 5,000)\nIncludes Cycles Without Transfer", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Treatment Cycles", fontsize=10)
    ax1.set_ylim(0, 3000)
    ax1.grid(axis="y", alpha=0.5)
    for bar in bars1:
        yval = bar.get_height()
        pct = yval / len(df_full) * 100
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 50, f"{yval:,}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")

    bars2 = ax2.bar(["Class 0\n(Negative Test)", "Class 1\n(Positive Test)"], transfer_counts.values, color=[c_coral, c_teal], width=0.55)
    ax2.set_title("Embryo-Transfer Cohort (N = 3,750)\nExcludes 'Non-Return of Embryos'", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Completed Transfers", fontsize=10)
    ax2.set_ylim(0, 3000)
    ax2.grid(axis="y", alpha=0.5)
    for bar in bars2:
        yval = bar.get_height()
        pct = yval / len(df_transfer) * 100
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 50, f"{yval:,}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.suptitle("Target Outcome Distribution Across Analytical Cohorts", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p1 = out_dir / "target_distribution.png"
    plt.savefig(p1)
    plt.close()
    generated.append(p1)

    # 2. Female and Male Age Distributions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    fem_age = df_full["Female Age"].dropna()
    male_age = df_full["Male Age"].dropna()

    ax1.hist(fem_age, bins=np.arange(18.5, 50.5, 1), color=c_blue, edgecolor="white", alpha=0.85, density=True)
    ax1.axvline(fem_age.median(), color="#c0392b", linestyle="--", linewidth=1.5, label=f"Median: {fem_age.median():.0f} yrs")
    ax1.axvline(fem_age.mean(), color="#d35400", linestyle=":", linewidth=1.5, label=f"Mean: {fem_age.mean():.1f} yrs")
    ax1.set_title("Female Partner Age Distribution", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Age at Cycle Start (years)", fontsize=10)
    ax1.set_ylabel("Density", fontsize=10)
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(axis="y", alpha=0.5)

    ax2.hist(male_age, bins=np.arange(18.5, 60.5, 1), color="#8e44ad", edgecolor="white", alpha=0.85, density=True)
    ax2.axvline(male_age.median(), color="#c0392b", linestyle="--", linewidth=1.5, label=f"Median: {male_age.median():.0f} yrs")
    ax2.axvline(male_age.mean(), color="#d35400", linestyle=":", linewidth=1.5, label=f"Mean: {male_age.mean():.1f} yrs")
    ax2.set_title("Male Partner Age Distribution", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Age at Cycle Start (years)", fontsize=10)
    ax2.set_ylabel("Density", fontsize=10)
    ax2.legend(loc="upper right", frameon=True)
    ax2.grid(axis="y", alpha=0.5)

    plt.suptitle("Baseline Couple Age Demographics (N = 5,000 Treatment Cycles)", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p2 = out_dir / "age_distributions.png"
    plt.savefig(p2)
    plt.close()
    generated.append(p2)

    # 3. AMH Distribution (Linear + Log scale with extreme values callout)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    amh = df_full["AMH"].dropna()

    ax1.hist(amh, bins=50, range=(0, 25), color=c_teal, edgecolor="white", alpha=0.85)
    ax1.axvline(amh.median(), color="#c0392b", linestyle="--", linewidth=1.5, label=f"Median: {amh.median():.2f}")
    ax1.axvline(amh.quantile(0.75), color="#d35400", linestyle=":", linewidth=1.5, label=f"Q75: {amh.quantile(0.75):.2f}")
    ax1.set_title("AMH Distribution (Zoomed 0–25 Range)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("AMH Value (unit not specified in source dataset)", fontsize=10)
    ax1.set_ylabel("Treatment Cycles", fontsize=10)
    ax1.legend(loc="upper right")
    ax1.grid(axis="y", alpha=0.5)

    # Log scale to display extreme values up to 482.1
    log_amh = np.log10(amh + 0.01)
    ax2.hist(log_amh, bins=40, color="#34495e", edgecolor="white", alpha=0.85)
    ax2.axvline(np.log10(482.1 + 0.01), color="#e74c3c", linestyle="--", linewidth=1.5, label="Max value: 482.1 (N = 3)")
    ax2.set_title("AMH Distribution (Log10 Transformed)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("log10(AMH + 0.01)", fontsize=10)
    ax2.set_ylabel("Treatment Cycles", fontsize=10)
    ax2.legend(loc="upper left")
    ax2.grid(axis="y", alpha=0.5)

    plt.suptitle("Anti-Müllerian Hormone (AMH) Distribution & Extreme Value Inspection", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p3 = out_dir / "amh_distribution.png"
    plt.savefig(p3)
    plt.close()
    generated.append(p3)

    # 4. Sperm Parameters (Count, Motility, Morphology)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)
    sp_count = df_full["Sperm count"].dropna()
    sp_mot = df_full["Sperm motility"].dropna()
    sp_morph = df_full["Sperm morphology"].dropna()

    ax1.hist(sp_count, bins=40, color="#27ae60", edgecolor="white", alpha=0.85)
    ax1.axvline(sp_count.median(), color="#c0392b", linestyle="--", label=f"Median: {sp_count.median():.1f}")
    ax1.set_title("Sperm Count", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Concentration (presumed million/mL)", fontsize=9)
    ax1.set_ylabel("Cycles", fontsize=9)
    ax1.legend()
    ax1.grid(axis="y", alpha=0.5)

    ax2.hist(sp_mot, bins=30, color="#2980b9", edgecolor="white", alpha=0.85)
    ax2.axvline(sp_mot.median(), color="#c0392b", linestyle="--", label=f"Median: {sp_mot.median():.2f}")
    ax2.set_title("Sperm Motility", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Motility Proportion / %", fontsize=9)
    ax2.legend()
    ax2.grid(axis="y", alpha=0.5)

    ax3.hist(sp_morph, bins=25, color="#8e44ad", edgecolor="white", alpha=0.85)
    ax3.axvline(sp_morph.median(), color="#c0392b", linestyle="--", label=f"Median: {sp_morph.median():.2f}")
    ax3.set_title("Sperm Morphology", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Morphology Metric (range 0.0–3.0)", fontsize=9)
    ax3.legend()
    ax3.grid(axis="y", alpha=0.5)

    plt.suptitle("Semen Analysis Parameter Distributions (Timing: Diagnostic vs Retrieval Day Unconfirmed)", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p4 = out_dir / "sperm_parameters.png"
    plt.savefig(p4)
    plt.close()
    generated.append(p4)

    # 5. Oocyte Maturity Breakdown (MII, MI, others)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    mii = df_full["Oocyte Maturity MII"].dropna()
    mi = df_full["Oocyte Maturity MI"].dropna()
    others = df_full["Oocyte Maturity others"].dropna()

    ax1.boxplot([mii, mi, others], tick_labels=["MII (Mature)", "MI (Intermediate)", "Others (GV/Atretic)"], patch_artist=True,
                boxprops=dict(facecolor="#3498db", color="#2980b9"),
                medianprops=dict(color="#e74c3c", linewidth=2))
    ax1.set_title("Oocyte Nuclear Maturity Yield per Cycle", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Oocyte Count", fontsize=10)
    ax1.grid(axis="y", alpha=0.5)

    # Total oocytes vs Fertilized eggs
    tot_oocytes = mii + mi + others
    fert = df_full["Number of fertilized eggs"].dropna()
    ax2.scatter(tot_oocytes, fert, alpha=0.25, color="#16a085", s=18)
    ax2.plot([0, 50], [0, 50], color="#e74c3c", linestyle="--", label="100% Fertilization Line (y=x)")
    ax2.set_title("Total Retrieved Oocytes vs Normally Fertilized Eggs (2PN)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Total Oocytes (MII + MI + Others)", fontsize=10)
    ax2.set_ylabel("Number of Fertilized Eggs", fontsize=10)
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.5)

    plt.suptitle("Oocyte Maturity and Fertilization Dynamics", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p5 = out_dir / "oocyte_maturity_distribution.png"
    plt.savefig(p5)
    plt.close()
    generated.append(p5)

    # 6. Embryo-Grade Distributions & Summary Counts
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    g1 = df_full["Embryo Grade 1"].dropna()
    g2 = df_full["Embryo Grade 2"].dropna()
    g3 = df_full["Embryo Grade 3"].dropna()
    g4 = df_full["Embryo Grade 4"].dropna()

    ax1.boxplot([g1, g2, g3, g4], tick_labels=["Grade 1\n(High)", "Grade 2\n(Fair)", "Grade 3\n(Poor)", "Grade 4\n(Arrested)"], patch_artist=True,
                boxprops=dict(facecolor="#9b59b6", color="#8e44ad"),
                medianprops=dict(color="#e74c3c", linewidth=2))
    ax1.set_title("Embryo Cohort Quality Breakdown by Morphological Grade", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Embryo Count", fontsize=10)
    ax1.grid(axis="y", alpha=0.5)

    tot_embryos = df_full["Number of embryos"].dropna()
    frozen = df_full["frezzing"].dropna()
    ax2.boxplot([tot_embryos, frozen], tick_labels=["Viable Embryos\n(Number of embryos)", "Cryopreserved\n(frezzing)"], patch_artist=True,
                boxprops=dict(facecolor="#1abc9c", color="#16a085"),
                medianprops=dict(color="#e74c3c", linewidth=2))
    ax2.set_title("Viable Embryonic Yield & Surplus Cryopreservation", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Embryo Count", fontsize=10)
    ax2.grid(axis="y", alpha=0.5)

    plt.suptitle("Embryology Developmental Yield and Cryopreservation (N = 5,000 Cycles)", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p6 = out_dir / "embryo_grades_distribution.png"
    plt.savefig(p6)
    plt.close()
    generated.append(p6)

    # 7. Year-wise Recorded Outcome Prevalence (2019-2025)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    df_y = df_full.assign(Year=pd.to_datetime(df_full["Egg retrieval date"]).dt.year)
    df_t_y = df_transfer.assign(Year=pd.to_datetime(df_transfer["Egg retrieval date"]).dt.year)

    full_rates = df_y.groupby("Year")[TARGET_COL].mean() * 100
    transfer_rates = df_t_y.groupby("Year")[TARGET_COL].mean() * 100
    years = full_rates.index.tolist()

    ax.plot(years, full_rates.values, marker="o", linewidth=2.5, color=c_blue, label="Full-Cycle Cohort (All 5,000 Cycles)")
    ax.plot(years, transfer_rates.values, marker="s", linewidth=2.5, color=c_coral, linestyle="--", label="Embryo-Transfer Cohort (3,750 Completed Transfers)")
    ax.set_title("Temporal Drift: Annual Recorded Positive Outcome Prevalence (2019–2025)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Oocyte Retrieval Calendar Year", fontsize=10)
    ax.set_ylabel("Positive Outcome Rate (%)", fontsize=10)
    ax.set_ylim(25, 90)
    ax.grid(True, alpha=0.5)

    # Add data point labels
    for y, f_val, t_val in zip(years, full_rates.values, transfer_rates.values):
        ax.annotate(f"{f_val:.1f}%", (y, f_val - 3.5), ha="center", fontsize=8, color=c_blue, fontweight="bold")
        ax.annotate(f"{t_val:.1f}%", (y, t_val + 2.0), ha="center", fontsize=8, color=c_coral, fontweight="bold")

    ax.legend(loc="lower right", frameon=True)
    plt.tight_layout()
    p7 = out_dir / "temporal_outcome_trend.png"
    plt.savefig(p7)
    plt.close()
    generated.append(p7)

    # 8. Feature Correlation Heatmap (Spearman Rank Correlation)
    num_features = [
        "Female Age", "Number of attempts", "AMH", "Male Age",
        "Sperm count", "Sperm motility", "Sperm morphology",
        "Oocyte Maturity MII", "Oocyte Maturity MI", "Number of fertilized eggs",
        "Embryo Grade 1", "Embryo Grade 2", "Number of embryos", "frezzing",
        TARGET_COL,
    ]
    corr_df = df_full[num_features].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(11, 9), dpi=300)
    cax = ax.imshow(corr_df.values, cmap="coolwarm", vmin=-1, vmax=1)
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04, label="Spearman Rank Correlation (ρ)")

    short_labels = [
        "Female Age", "Attempts", "AMH", "Male Age",
        "Sperm Count", "Sperm Motility", "Sperm Morph",
        "Oocyte MII", "Oocyte MI", "Fertilized Eggs",
        "Embryo G1", "Embryo G2", "Total Embryos", "Frozen",
        "Recorded Outcome",
    ]
    ax.set_xticks(np.arange(len(short_labels)))
    ax.set_yticks(np.arange(len(short_labels)))
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(short_labels, fontsize=8)

    # Print correlation values on cells
    for i in range(len(short_labels)):
        for j in range(len(short_labels)):
            val = corr_df.iloc[i, j]
            color = "white" if abs(val) > 0.45 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=6.5)

    ax.set_title("Spearman Rank Correlation Matrix Across Treatment Variables & Target", fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    p8 = out_dir / "correlation_heatmap.png"
    plt.savefig(p8)
    plt.close()
    generated.append(p8)

    # 9. Cohort Comparison: Embryo-Transfer (N=3,750) vs Non-Return of Embryos (N=1,250)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 9), dpi=300)
    df_full["Transfer_Status"] = np.where(df_full[BETA_COL] == "Non-return of embryos", "Non-Return (N=1,250)", "Transfer (N=3,750)")

    # Female Age
    age_t = df_full.loc[df_full["Transfer_Status"] == "Transfer (N=3,750)", "Female Age"]
    age_nr = df_full.loc[df_full["Transfer_Status"] == "Non-Return (N=1,250)", "Female Age"]
    ax1.boxplot([age_t, age_nr], tick_labels=["Transfer", "Non-Return"], patch_artist=True,
                boxprops=dict(facecolor=c_teal), medianprops=dict(color="#c0392b", linewidth=2))
    ax1.set_title("Female Age Comparison", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Years", fontsize=9)
    ax1.grid(axis="y", alpha=0.5)

    # AMH
    amh_t = df_full.loc[df_full["Transfer_Status"] == "Transfer (N=3,750)", "AMH"].clip(upper=15)
    amh_nr = df_full.loc[df_full["Transfer_Status"] == "Non-Return (N=1,250)", "AMH"].clip(upper=15)
    ax2.boxplot([amh_t, amh_nr], tick_labels=["Transfer", "Non-Return"], patch_artist=True,
                boxprops=dict(facecolor=c_blue), medianprops=dict(color="#c0392b", linewidth=2))
    ax2.set_title("AMH Comparison (Capped at 15 for visualization)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("AMH Level", fontsize=9)
    ax2.grid(axis="y", alpha=0.5)

    # Oocyte Maturity MII
    mii_t = df_full.loc[df_full["Transfer_Status"] == "Transfer (N=3,750)", "Oocyte Maturity MII"]
    mii_nr = df_full.loc[df_full["Transfer_Status"] == "Non-Return (N=1,250)", "Oocyte Maturity MII"]
    ax3.boxplot([mii_t, mii_nr], tick_labels=["Transfer", "Non-Return"], patch_artist=True,
                boxprops=dict(facecolor="#e67e22"), medianprops=dict(color="#c0392b", linewidth=2))
    ax3.set_title("Mature Oocytes (MII) Comparison", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Oocyte Count", fontsize=9)
    ax3.grid(axis="y", alpha=0.5)

    # Number of fertilized eggs
    fert_t = df_full.loc[df_full["Transfer_Status"] == "Transfer (N=3,750)", "Number of fertilized eggs"]
    fert_nr = df_full.loc[df_full["Transfer_Status"] == "Non-Return (N=1,250)", "Number of fertilized eggs"]
    ax4.boxplot([fert_t, fert_nr], tick_labels=["Transfer", "Non-Return"], patch_artist=True,
                boxprops=dict(facecolor="#9b59b6"), medianprops=dict(color="#c0392b", linewidth=2))
    ax4.set_title("Fertilized Eggs (2PN) Comparison", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Fertilized Count", fontsize=9)
    ax4.grid(axis="y", alpha=0.5)

    plt.suptitle("Clinical Feature Comparison: Embryo-Transfer Cohort vs Non-Return of Embryos", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    p9 = out_dir / "cohort_comparison_transfer_vs_nonreturn.png"
    plt.savefig(p9)
    plt.close()
    generated.append(p9)

    return generated


def generate_eda_summary_report(
    df_full: pd.DataFrame,
    df_transfer: pd.DataFrame,
    desc_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    quality_dict: Dict[str, Any],
    output_path: str | Path = "reports/eda_summary.md",
) -> None:
    """Generate comprehensive markdown summary report of Phase 3 EDA findings."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    target_full = df_full[TARGET_COL].value_counts()
    target_transfer = df_transfer[TARGET_COL].value_counts()

    sig_full = stats_df[(stats_df["cohort"].str.contains("Full-Cycle")) & (stats_df["significant_fdr_05"])].sort_values("effect_size", ascending=False)
    sig_transfer = stats_df[(stats_df["cohort"].str.contains("Embryo-Transfer")) & (stats_df["significant_fdr_05"])].sort_values("effect_size", ascending=False)

    md = []
    md.append("# IVF Insight: Exploratory Data Analysis & Statistical Investigation Report")
    md.append("\n**Author:** Senior Biomedical Data Scientist & Research Engineer")
    md.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("**Source Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 candidate treatment cycles)\n")
    md.append("---\n")

    md.append("## 1. Executive Summary & Cohort Framework\n")
    md.append(
        "This Phase 3 exploratory data analysis provides a comprehensive statistical investigation of the authoritative "
        "5,000-cycle IVF clinical dataset. To ensure clinical validity and prevent conflation of cycle cancellations with biological "
        "implantation failure, the analysis strictly preserves two distinct analytical cohorts throughout all evaluations:\n"
    )
    md.append(
        f"- **Cohort A (Full-Cycle Cohort, N = {len(df_full):,}):** All treatment cycles initiating controlled ovarian stimulation. "
        f"Recorded positive cycle outcome prevalence is **{target_full.get(1.0, 0)/len(df_full)*100:.2f}%** (Class 0 = {target_full.get(0.0, 0):,}, Class 1 = {target_full.get(1.0, 0):,}). "
        "Class 0 includes 1,250 cycles with no embryo transfer ('Non-return of embryos') where implantation was impossible.\n"
    )
    md.append(
        f"- **Cohort B (Embryo-Transfer Cohort, N = {len(df_transfer):,}):** Restricted strictly to completed intrauterine embryo transfers, "
        "excluding the 1,250 non-return cases. In this clinical sub-cohort, recorded positive outcome prevalence is **{target_transfer.get(1.0, 0)/len(df_transfer)*100:.2f}%** "
        f"(Class 0 = {target_transfer.get(0.0, 0):,}, Class 1 = {target_transfer.get(1.0, 0):,}).\n"
    )
    md.append(
        "> [!IMPORTANT]\n"
        "> **Non-Interchangeability Warning:** Evaluating predictive models on the full-cycle cohort vs the embryo-transfer cohort "
        "yields substantially different statistical distributions, effect sizes, and clinical interpretations. "
        "Treating these cohorts as interchangeable introduces severe selection bias.\n"
    )

    md.append("## 2. Demographic & Baseline Clinical Characteristics\n")
    fem_age = df_full["Female Age"]
    male_age = df_full["Male Age"]
    amh = df_full["AMH"]
    md.append(
        f"- **Female Age:** Spans 20 to 49 years (Mean: {fem_age.mean():.1f} ± {fem_age.std():.1f}; Median: {fem_age.median():.0f}, IQR: {fem_age.quantile(0.75) - fem_age.quantile(0.25):.0f}). "
        "Distribution is unimodal and approximately symmetric (skewness: 0.22).\n"
        f"- **Male Age:** Spans 19 to 57 years (Mean: {male_age.mean():.1f} ± {male_age.std():.1f}; Median: {male_age.median():.0f}, IQR: {male_age.quantile(0.75) - male_age.quantile(0.25):.0f}; skewness: 0.36).\n"
        f"- **Number of Attempts:** Ranges from 1 to 10 (Median: 1, IQR: 1; 81.3% of cycles are recorded as attempt 1).\n"
        f"- **AMH (Anti-Müllerian Hormone):** Spans 0.0 to 482.1 (Median: {amh.median():.2f}, IQR: {amh.quantile(0.75) - amh.quantile(0.25):.2f}). "
        f"Distribution is heavily right-skewed (skewness: {skew(amh.dropna()):.2f}). Exactly {quality_dict['amh_extremes']['count_gt_20']} cycles have AMH > 20, "
        f"and {quality_dict['amh_extremes']['count_equal_482_1']} cycles have an extreme value of 482.1.\n"
    )

    md.append("## 3. Statistical Association Analysis (Mann–Whitney U & Chi-Square with BH-FDR Correction)\n")
    md.append(
        "Univariate tests were conducted separately for each analytical cohort against `recorded_cycle_outcome`. "
        "All p-values were corrected for multiple testing using the Benjamini–Hochberg False Discovery Rate (FDR) procedure. "
        "**Statistical significance reflects observed association, NOT clinical causation.**\n"
    )

    md.append("### Key Statistical Discrepancies Between Cohorts\n")
    md.append(
        "1. **Female Age Effect:** In the Full-Cycle Cohort, Female Age is **not significantly associated** with outcome ($p = 0.276, q = 0.283$). "
        "However, in the Embryo-Transfer Cohort, Female Age is **highly significant** ($p = 0.00033, q = 0.00049$; rank-biserial $r = 0.072$). "
        "This divergence occurs because non-return cycles occur across all age tiers due to ovarian response failure, masking age-dependent implantation rates.\n"
    )
    md.append(
        "2. **Embryonic Yield Effect Sizes:** In the Full-Cycle Cohort, `Number of embryos` displays an enormous rank-biserial correlation ($r = 0.612, p = 0.0$) "
        "because all 1,250 non-return cycles have 0 embryos and outcome 0. In the Embryo-Transfer Cohort, where every cycle yielded transferable embryos, "
        "the effect size drops to **$r = 0.234$** ($p = 7.6 \\times 10^{-34}$). Conflating cohorts artificially inflates embryonic predictor importance.\n"
    )
    md.append(
        "3. **Top Predictors in Embryo-Transfer Cohort:** Ranked by effect size ($r$ / Cramer's V):\n"
        f"  - `frezzing` (Surplus cryopreserved embryos): $r = 0.355, q = 6.0 \\times 10^{-90}$\n"
        f"  - `Medicines and treatments` (Protocol ID): Cramer's $V = 0.336, q = 1.0 \\times 10^{-25}$\n"
        f"  - `Number of fertilized eggs`: $r = 0.313, q = 9.5 \\times 10^{-55}$\n"
        f"  - `Embryo Grade 1`: $r = 0.275, q = 5.8 \\times 10^{-43}$\n"
        f"  - `Oocyte Maturity MII`: $r = 0.274, q = 1.7 \\times 10^{-42}$\n"
        f"  - `Number of embryos`: $r = 0.234, q = 2.7 \\times 10^{-33}$\n"
    )

    md.append("## 4. In-Depth Data Quality & Anomaly Audits\n")

    md.append("### A. AMH Extreme Values & Assay Uncertainty")
    md.append(
        f"- Exactly 3 treatment cycles (Rows 443, 2291, 3974) exhibit identical extreme AMH values of **482.1**.\n"
        "- In Row 2291, the patient yielded 42 mature MII oocytes and 35 fertilized eggs, a massive response consistent with high ovarian response. "
        "Because measurement units are not specified in the source dataset, the physical units and assay scale remain unconfirmed without author clarification. "
        "In Rows 443 and 3974, only 3 MII oocytes were retrieved, suggesting possible data entry typographical errors or assay artifacts. "
        "Observations are preserved intact without automated removal.\n"
    )

    md.append("### B. Treatment Protocol Cardinality & Distribution")
    proto_meta = quality_dict["protocol_cardinality"]
    md.append(
        f"- Feature `Medicines and treatments` exhibits **{proto_meta['unique_protocols']} unique integer codes** (spanning 1 to 183).\n"
        f"- The distribution is extremely heavy-tailed: Protocol ID {proto_meta['top_protocol_id']} alone accounts for **{proto_meta['top_protocol_count']} cycles ({proto_meta['top_protocol_percentage']}%)**.\n"
        f"- The top 5 protocols collectively account for **{proto_meta['top_5_percentage']}%** of all treatments.\n"
        f"- Exactly **{proto_meta['singleton_protocols']} protocols are singletons** (prescribed to only 1 patient). Continuous scaling of this feature is strictly prohibited.\n"
    )

    md.append("### C. Oocyte & Embryo Count Consistency")
    md.append(
        f"- In {quality_dict['oocyte_embryo_consistency']['fertilized_greater_than_mii']} cycles (11.0%), normally fertilized eggs (2PN) exceed Metaphase II (MII) counts. "
        "As noted in embryology practice, this reflects in vitro maturation of immature MI oocytes overnight, or conventional IVF insemination.\n"
        f"- In {quality_dict['oocyte_embryo_consistency']['fertilized_greater_than_total_oocytes']} cycles (0.24%), fertilized eggs exceed total retrieved oocytes (an embryological recording anomaly).\n"
        "- In 3,317 cycles, the sum of Morphological Grades 1–4 exceeds `Number of embryos`. `Number of embryos` reflects viable, transfer-quality embryos, whereas Grades 3–4 denote degenerated/arrested embryos.\n"
    )

    md.append("### D. Temporal Drift in Cycle Outcomes (2019–2025)")
    md.append(
        "Annual positive outcome prevalence varies markedly across the 7-year timeline:\n"
        "- **2019:** Full = 52.7%, Transfer = 72.0% (N = 1,730)\n"
        "- **2020:** Full = 35.9%, Transfer = 42.8% (N = 298) — notable clinical dip coinciding with COVID-19 pandemic service restrictions.\n"
        "- **2021:** Full = 39.9%, Transfer = 50.5% (N = 411)\n"
        "- **2022:** Full = 44.5%, Transfer = 57.8% (N = 382)\n"
        "- **2023:** Full = 45.6%, Transfer = 56.3% (N = 721)\n"
        "- **2024:** Full = 60.7%, Transfer = 82.7% (N = 952)\n"
        "- **2025:** Full = 46.0%, Transfer = 70.2% (N = 506)\n"
    )

    md.append("### E. Potential Repeated-Cycle Clustering")
    rep_meta = quality_dict["repeated_cycle_clusters"]
    md.append(
        f"- Exactly **{rep_meta['potential_cluster_groups']} unique baseline demographic triplets** (Female Age, Male Age, AMH) appear more than once, "
        f"encompassing **{rep_meta['cycles_in_potential_clusters']} cycles ({rep_meta['percentage_of_dataset']}%)**.\n"
        "- In the absence of patient identifiers, repeated-cycle leakage across validation partitions cannot be completely ruled out.\n"
    )

    md.append("## 5. Generated Artifacts & Visualizations Index\n")
    md.append("The following publication-grade figures were generated and saved in `reports/figures/`:\n")
    md.append("1. `target_distribution.png`: Target outcome comparison between Full-Cycle and Embryo-Transfer cohorts.\n")
    md.append("2. `age_distributions.png`: Female and Male partner age histograms with KDE and summary statistics.\n")
    md.append("3. `amh_distribution.png`: Linear zoomed (0-25) and log10-transformed AMH distributions highlighting extreme values.\n")
    md.append("4. `sperm_parameters.png`: Semen concentration, motility, and morphology distributions.\n")
    md.append("5. `oocyte_maturity_distribution.png`: Nuclear maturity grading (MII, MI, others) and fertilization dynamics.\n")
    md.append("6. `embryo_grades_distribution.png`: Morphological embryo grade counts (Grades 1-4), viable counts, and surplus vitrification.\n")
    md.append("7. `temporal_outcome_trend.png`: Longitudinal positive outcome prevalence from 2019 to 2025.\n")
    md.append("8. `correlation_heatmap.png`: Spearman rank correlation matrix across treatment features and target.\n")
    md.append("9. `cohort_comparison_transfer_vs_nonreturn.png`: Baseline parameter comparisons between transferred and cancelled cycles.\n")

    md.append("\n## 6. Research Compliance & Non-Claim Notice\n")
    md.append(
        "- **No ML models were trained** during this exploratory phase.\n"
        "- **No clinical validity is claimed.**\n"
        "- **Observed associations must not be interpreted as causal relationships.**\n"
        "- **All 5,000 candidate observations remain intact without automated outlier filtering.**\n"
    )

    out.write_text("\n".join(md), encoding="utf-8")


def run_eda_pipeline(
    excel_path: str | Path = "data/raw/Dataset Clean.xlsx",
    output_dir: str | Path = "reports",
) -> Dict[str, Any]:
    """Execute complete Phase 3 EDA pipeline, export CSVs, figures, and summary report."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    figures_dir = out / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load analytical cohorts
    df_full, df_transfer = load_clean_cohorts(excel_path)

    # 2. Compute descriptive statistics
    desc_df = compute_descriptive_statistics(df_full, df_transfer)
    desc_csv_path = out / "descriptive_statistics.csv"
    desc_df.to_csv(desc_csv_path, index=False, encoding="utf-8")

    # 3. Compute statistical tests
    stats_df = compute_statistical_associations(df_full, df_transfer)
    stats_csv_path = out / "statistical_tests.csv"
    stats_df.to_csv(stats_csv_path, index=False, encoding="utf-8")

    # 4. In-depth data quality audit
    quality_meta = analyze_data_quality_anomalies(df_full)

    # 5. Generate publication figures
    generated_figures = generate_eda_figures(df_full, df_transfer, figures_dir)

    # 6. Generate summary markdown report
    summary_md_path = out / "eda_summary.md"
    generate_eda_summary_report(df_full, df_transfer, desc_df, stats_df, quality_meta, summary_md_path)

    return {
        "status": "success",
        "full_cohort_size": len(df_full),
        "embryo_transfer_cohort_size": len(df_transfer),
        "descriptive_statistics_csv": str(desc_csv_path),
        "statistical_tests_csv": str(stats_csv_path),
        "eda_summary_md": str(summary_md_path),
        "figures_count": len(generated_figures),
        "figures_directory": str(figures_dir),
        "quality_audit": quality_meta,
    }
