# Reproducibility Protocol & Environment Specification

This document provides complete, step-by-step instructions for establishing the computational environment, verifying dataset integrity, and reproducing every analytical finding, statistical test, predictive model, and research report in **IVF Insight**.

---

## 1. Computational Environment & System Requirements

The analytical pipeline is operating-system agnostic and verified on:
- **Operating Systems:** Microsoft Windows 10/11 (PowerShell 5.1+ / 7+), Ubuntu 22.04 LTS, macOS Sonoma.
- **Python Version:** Python 3.10, 3.11, or 3.12 (developed and audited on Python 3.12).
- **RAM:** Minimum 8 GB (16 GB recommended for bootstrap resampling, five-fold stratified cross-validation on training data, and chronological holdout evaluation).
- **Disk Space:** ~500 MB (excluding virtual environment).
- **PDF Compilation Engine (Optional):** Microsoft Edge (`msedge.exe`) or Google Chrome (`chrome.exe`) for headless PDF compilation of the monograph report.

---

## 2. Installation & Environment Setup

### Step 2.1: Clone Repository
```bash
git clone https://github.com/your-username/ivf-insight.git
cd ivf-insight
```

### Step 2.2: Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS (bash / zsh)
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2.3: Install Dependencies and Editable Package
```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

Verify that the CLI entrypoint is available:
```bash
ivf-insight --help
```

---

## 3. Dataset Acquisition & Integrity Verification

Due to patient privacy protections and data governance protocols, raw clinical records are not bundled in this repository.

1. Navigate to the official Mendeley Data record:
   - **Citation:** Maghdid, S., Rashid, T. A., & Askar, S. (2026). *Comprehensive Dataset Profile of In Vitro Fertilization (IVF) Clinical and Embryological Data*. Mendeley Data, Version 1. [DOI: 10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1).
   - **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).
2. Download `Dataset Clean.xlsx` and `Normalized CSV.csv`.
3. Place both files into `data/raw/`:
   ```text
   data/raw/Dataset Clean.xlsx
   data/raw/Normalized CSV.csv
   ```
4. Verify SHA-256 cryptographic checksums:
   - **Windows (PowerShell):**
     ```powershell
     Get-FileHash "data/raw/Dataset Clean.xlsx" -Algorithm SHA256
     Get-FileHash "data/raw/Normalized CSV.csv" -Algorithm SHA256
     ```
   - **Linux / macOS:**
     ```bash
     sha256sum data/raw/Dataset\ Clean.xlsx
     sha256sum data/raw/Normalized\ CSV.csv
     ```
   - **Expected Checksums:**
     - `Dataset Clean.xlsx`: `8914bf7a331c01bc1c66eeb81bf405b3476da3d80674536385a166f5d52dbf32`
     - `Normalized CSV.csv`: `fdda6c56c8ac3f66e8981685fa8732b9aaa57818f39e53325463a5e6c0acabc0`

---

## 4. End-to-End Execution Sequence

Execute the analytical pipeline stages sequentially using the unified CLI:

```bash
# Phase 1: Reconcile authoritative Excel and normalized CSV datasets
# Generates reports/dataset_comparison.md, reports/dataset_comparison.json, data quality summaries
ivf-insight reconcile --excel "data/raw/Dataset Clean.xlsx" --csv "data/raw/Normalized CSV.csv" --output-dir reports

# Phase 2: Feature governance registry and research design document
# Generates reports/feature_governance.csv, reports/research_design.md, reports/research_questions.md
ivf-insight governance --output-dir reports

# Phase 3: Exploratory data analysis, dual-cohort statistics, and figures
# Generates reports/descriptive_statistics.csv, reports/statistical_tests.csv, reports/figures/*.png
ivf-insight eda --excel "data/raw/Dataset Clean.xlsx" --output-dir reports

# Phase 4: Predictive modelling, chronological evaluation, explainability, and diagnostics
# Generates reports/model_metrics.csv, reports/model_comparison.md, reports/model_figures/*.png, models/*.joblib
ivf-insight experiment --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --models-dir models

# Phase 5: Robustness, sensitivity, temporal drift, calibration, and threshold validation
# Generates reports/temporal_drift.csv, reports/cutoff_sensitivity.csv, reports/calibration_diagnostics.csv, reports/robustness_figures/*.png
ivf-insight validate --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --figures-dir reports/robustness_figures

# Phase 5.1: Statistical integrity, multicollinearity, Female Age paradox, and canonical calibration audit
# Generates reports/statistical_integrity_audit.md, reports/age_association_analysis.csv, reports/calibration_audit.csv
ivf-insight audit --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --figures-dir reports/robustness_figures

# Phase 6: Monograph report compilation (Markdown, styled HTML, and academic PDF)
# Generates reports/IVF_Insight_Research_Report.md, reports/IVF_Insight_Research_Report.html, reports/IVF_Insight_Research_Report.pdf
ivf-insight report --output-dir reports
```

---

## 5. Automated Test Suite Execution

The automated test suite verifies dataset reconciliation boundaries, feature governance registries, chronological holdout splits, pipeline leakage prevention, statistical integrity audits, and odds ratio derivations.

Run the complete test suite:
```bash
python -m pytest -v
```

Expected result: **45 passed** in ~30 seconds.

---

## 6. Interactive Jupyter Notebooks Sequence

The analytical steps are mirrored in 5 interactive, narrative notebooks under `notebooks/`:

| Notebook | Purpose | Input Sources | Key Visualizations & Outputs |
| :--- | :--- | :--- | :--- |
| `01_dataset_audit_and_eda.ipynb` | Initial reconciliation, schema inspection, duplicate detection | `data/raw/Dataset Clean.xlsx` | Missingness distributions, schema tables |
| `02_exploratory_data_analysis.ipynb` | Full-Cycle vs Embryo-Transfer cohort distributions, Mann-Whitney U & Chi-Square tests | `reports/descriptive_statistics.csv`, `reports/statistical_tests.csv` | Feature histograms, correlation heatmaps |
| `03_predictive_modelling.ipynb` | 18-experiment evaluation, ROC/PR curves, confusion matrices, Gini importance | `reports/model_metrics.csv`, `reports/model_figures/` | ROC curves, PR curves, feature importances |
| `04_robustness_validation.ipynb` | Temporal drift, multi-cutoff sensitivity, calibration diagnostics, bootstrap stability | `reports/temporal_drift.csv`, `reports/cutoff_sensitivity.csv` | Drift trends, calibration curves, threshold tradeoffs |
| `05_statistical_integrity_audit.ipynb` | Female Age suppression audit, VIF collinearity, canonical CITL, hypothesis audit | `reports/age_association_analysis.csv`, `reports/calibration_audit.csv` | Cubic splines, VIF bar charts, CITL diagnostic plots |

To execute notebooks interactively:
```bash
jupyter lab
# or
jupyter notebook
```

---

## 7. Deterministic Seeds & Hyperparameter Configuration

All pseudo-random operations use explicit random seeds to support numerical reproducibility across supported environments:

- **Primary Random Seed:** `42` (used for scikit-learn models, StratifiedKFold cross-validation, and bootstrap resampling).
- **Secondary Sensitivity Seeds:** `100` to `109` (used for multi-seed stability evaluations in Phase 5).
- **Chronological Cutoff Boundary:** `2024-01-01` (primary chronological holdout split).
- **Alternative Chronological Cutoffs:** `2023-01-01` and `2024-07-01` (sensitivity analyses).
- **Random Forest Hyperparameters:** `n_estimators=300`, `max_depth=8`, `min_samples_split=10`, `min_samples_leaf=4`, `class_weight='balanced'`, `random_state=42`.
- **Logistic Regression Hyperparameters:** `C=1.0`, `penalty='l2'`, `solver='lbfgs'`, `class_weight='balanced'`, `max_iter=1000`, `random_state=42`.
- **Multiple Testing Correction:** Benjamini-Hochberg False Discovery Rate at $\alpha = 0.05$.
- **Bootstrap Iterations:** $B = 1,000$ iterations for model metric confidence intervals; $B = 100$ resamples for Gini feature importance stability.

---

## 8. Reproducibility Verification Checklist

- [x] Python 3.10+ installed and virtual environment configured.
- [x] `Dataset Clean.xlsx` placed in `data/raw/` and SHA-256 verified.
- [x] Synthetic boundary rows 5000 and 5001 excluded from analytical cohorts.
- [x] `data/raw/` verified absent from Git staging (`.gitignore` enforced).
- [x] All 7 CLI subcommands execute with zero exit codes.
- [x] All 45 automated pytest cases pass.
- [x] All 5 Jupyter notebooks execute sequentially without exceptions.
- [x] `reports/IVF_Insight_Research_Report.pdf` compiles with full 21 sections and academic typography.
