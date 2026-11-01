from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt


def data_quality_report(df: pd.DataFrame, target: str, output_dir: str | Path) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if target not in df.columns:
        raise ValueError(f"Target '{target}' not found. Available columns: {list(df.columns)}")

    missing = df.isna().sum().sort_values(ascending=False)
    report = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "target": target,
        "target_missing": int(df[target].isna().sum()),
        "target_distribution": {str(k): int(v) for k, v in df[target].value_counts(dropna=False).items()},
        "missing_values": {str(k): int(v) for k, v in missing.items()},
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
    }
    (output_dir / "data_quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    missing.rename("missing_count").to_csv(output_dir / "missingness.csv", header=True)

    plt.figure(figsize=(10, 5))
    plt.bar(missing.index.astype(str), missing.values)
    plt.xticks(rotation=70, ha="right")
    plt.ylabel("Missing values")
    plt.title("Missing values by feature")
    plt.tight_layout()
    plt.savefig(output_dir / "missingness.png", dpi=160)
    plt.close()

    plt.figure(figsize=(6, 4))
    df[target].astype("string").value_counts(dropna=False).plot(kind="bar")
    plt.title(f"Outcome distribution: {target}")
    plt.ylabel("Records")
    plt.tight_layout()
    plt.savefig(output_dir / "target_distribution.png", dpi=160)
    plt.close()
    return report


def descriptive_summary(df: pd.DataFrame, output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df.describe(include="all").transpose().to_csv(output_dir / "descriptive_summary.csv")
