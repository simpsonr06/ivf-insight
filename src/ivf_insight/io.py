from pathlib import Path
import pandas as pd


def load_table(path: str | Path) -> pd.DataFrame:
    """Load CSV or Excel data without silently changing source column names."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix}. Use CSV or XLSX.")
