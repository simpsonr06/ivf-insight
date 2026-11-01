# IVF Insight — Repository Architecture & Security Audit Report

**Date of Audit:** 2026-11-01  
**Project Title:** IVF Insight: Exploratory Clinical Data Analysis, Predictive Modelling and Temporal Validation of IVF Treatment-Cycle Outcomes  
**Lead Investigator:** Simpson R.  
**Repository Branch:** `master`  
**Execution Environment:** Python 3.12, Windows 10/11, x86_64  

---

## 1. Executive Summary

This repository audit report documents the formal verification, security scanning, dependency checking, and reproducibility testing conducted prior to public GitHub release of the **IVF Insight** research repository.

All analytical phases (Phases 1 through 6) remain fully intact, reproducible, and internally consistent. The repository has been structured in accordance with best practices for open-science biomedical machine learning research.

---

## 2. Data Protection & Sensitive Information Audit

### 2.1 Raw Clinical Dataset Protection
- **Authoritative Files:**
  - `data/raw/Dataset Clean.xlsx` (586,814 bytes; 5,002 rows $\times$ 21 columns; SHA-256: `8914bf7a331c01bc1c66eeb81bf405b3476da3d80674536385a166f5d52dbf32`)
  - `data/raw/Normalized CSV.csv` (874,985 bytes; 5,001 rows $\times$ 21 columns; SHA-256: `fdda6c56c8ac3f66e8981685fa8732b9aaa57818f39e53325463a5e6c0acabc0`)
- **Version Control Status:**
  - Both raw clinical files are strictly matched and excluded by `.gitignore` (`data/raw/*`, with exemptions only for `.gitkeep` and `README.md`).
  - Neither raw file is tracked or staged in Git.
  - No row-level or patient-level clinical records are committed or distributed anywhere in the repository.

### 2.2 Security, Secrets & PHI Scan
- **Credentials & API Keys:** Scanned all repository files for `.env`, private keys (`*.pem`, `*.key`), API tokens, database connection strings, and passwords. **Zero credentials found.**
- **Protected Health Information (PHI):** Scanned for patient names, phone numbers, national IDs, and direct identifiers. The underlying dataset was de-identified at source by Maghdid et al. (2026), and all reports contain only aggregate summary metrics, odds ratios, and distribution statistics.
- **Licence Separation:** Code is licensed under MIT. The dataset is licensed separately by its authors under CC BY 4.0. Both licenses are explicitly distinguished in `LICENSE`, `README.md`, `CITATION.cff`, and `DATASET_NOTES.md`.

---

## 3. Computational Environment & Reproducibility Audit

### 3.1 Package Packaging & CLI Verification
- Package metadata configured in `pyproject.toml` with `setuptools.build_meta`.
- Dependencies pinned in `requirements.txt` and mirrored in `pyproject.toml`.
- Editable installation tested and verified: `pip install -e ".[dev]"`.
- Unified CLI tool `ivf-insight` registered and operational with 7 subcommands:
  1. `reconcile`: Phase 1 data reconciliation and boundary exclusion.
  2. `governance`: Phase 2 feature registry and scenario definitions.
  3. `eda`: Phase 3 dual-cohort exploratory statistics and FDR hypothesis tests.
  4. `experiment`: Phase 4 18-experiment chronological predictive modeling.
  5. `validate`: Phase 5 temporal drift, multi-cutoff sensitivity, calibration diagnostics.
  6. `audit`: Phase 5.1 multicollinearity (VIF), suppression diagnostics, and canonical CITL.
  7. `report`: Phase 6 compilation of Markdown, styled HTML, and academic PDF monograph.

### 3.2 Automated Test Suite Verification
Executed full automated pytest suite:
```text
tests/test_reconciliation.py ........
tests/test_governance.py .........
tests/test_research_design_validation.py ..
tests/test_eda.py ........
tests/test_modelling.py .......
tests/test_robustness.py .......
tests/test_statistical_integrity.py ......
tests/test_pipeline.py .
tests/test_statistics.py .
============================== 45 passed in 29.18s ==============================
```
**Audit Result:** 100% test pass rate (45/45 passing).

### 3.3 Interactive Jupyter Notebooks Audit
All 5 narrative notebooks in `notebooks/` were executed end-to-end:
1. `01_dataset_audit_and_eda.ipynb`: Passed (schema, null distribution, checksum generation).
2. `02_exploratory_data_analysis.ipynb`: Passed (Mann-Whitney U, Chi-Square, correlation heatmap).
3. `03_predictive_modelling.ipynb`: Passed (model benchmarks, ROC/PR curves, confusion matrices).
4. `04_robustness_validation.ipynb`: Passed (drift trends, cutoff sensitivity, Harrell/Cox calibration).
5. `05_statistical_integrity_audit.ipynb`: Passed (suppression diagnostics, VIF collinearity, canonical CITL).

---

## 4. Reporting Quality & Numerical Ground Truth Cross-Verification

All quantitative claims in `reports/IVF_Insight_Research_Report.md` and `README.md` were cross-referenced against their source CSV outputs:

| Claimed Metric / Finding | Source CSV File | Source Value | Report Value | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| Full-Cycle Cohort Size | `reports/data_quality_summary.csv` | 5,000 cycles | 5,000 cycles | **Exact Match** |
| Embryo-Transfer Cohort Size | `reports/data_quality_summary.csv` | 3,750 cycles | 3,750 cycles | **Exact Match** |
| Cancelled Cycles (Non-Return) | `reports/data_quality_summary.csv` | 1,250 cycles | 1,250 cycles | **Exact Match** |
| Transfer Holdout Positive Rate | `reports/temporal_drift.csv` | 78.66% ($N=811/1,031$) | 78.7% ($N=811/1,031$) | **Exact Match** |
| Transfer Scen C RF ROC-AUC | `reports/model_metrics.csv` | 0.728 [0.689, 0.765] | 0.728 [0.689, 0.765] | **Exact Match** |
| Transfer Scen C RF PR-AUC | `reports/model_metrics.csv` | 0.892 [0.868, 0.915] | 0.892 [0.868, 0.915] | **Exact Match** |
| Transfer Scen C RF Brier Score | `reports/model_metrics.csv` | 0.179 | 0.179 | **Exact Match** |
| Full-Cycle Scen C RF ROC-AUC | `reports/model_metrics.csv` | 0.903 [0.886, 0.918] | 0.903 [0.886, 0.918] | **Exact Match** |
| `frezzing` Standardized OR | `reports/logistic_regression_odds_ratios.csv` | 2.408 [2.022, 2.868] | 2.408 [2.022, 2.868] | **Exact Match** |
| `Female Age` Standardized OR | `reports/logistic_regression_odds_ratios.csv` | 1.358 [1.222, 1.509] | 1.358 [1.222, 1.509] | **Exact Match** |
| `Male Age` Standardized OR | `reports/logistic_regression_odds_ratios.csv` | 0.753 [0.675, 0.841] | 0.753 [0.675, 0.841] | **Exact Match** |
| Canonical CITL via Offset | `reports/calibration_audit.csv` | +0.9371 [0.777, 1.098] | +0.9371 [0.777, 1.098] | **Exact Match** |
| Expected-to-Observed (E/O) Ratio | `reports/calibration_audit.csv` | 0.7971 | 0.7971 | **Exact Match** |
| `Number of fertilized eggs` VIF | `reports/logistic_regression_diagnostics.csv` | 11.14 | 11.14 | **Exact Match** |
| `Oocyte Maturity MII` VIF | `reports/logistic_regression_diagnostics.csv` | 5.97 | 5.97 | **Exact Match** |

---

## 5. Repository Manifest & File Organization

### 5.1 Source Code (`src/ivf_insight/`)
- `reconciliation.py`: 48.8 KB — Dataset reconciliation, order-agnostic matching, boundary row detection.
- `governance.py`: 58.8 KB — Feature governance, scenario definitions, author query registry.
- `eda.py`: 48.1 KB — Descriptive statistics, FDR-adjusted hypothesis tests, distribution plotting.
- `experiments.py`: 35.7 KB — Chronological splitting, pipeline fitting, bootstrap metric computation.
- `validation.py`: 45.1 KB — Temporal drift, cutoff sensitivity, calibration, feature stability.
- `integrity_audit.py`: 39.6 KB — Suppression effects, VIF calculation, canonical CITL offset derivation.
- `report.py`: 6.5 KB — Academic report markdown to styled HTML and headless PDF compiler.
- `cli.py`: 7.8 KB — Unified CLI entry point for all research workflows.
- `analysis.py`, `statistics.py`, `modeling.py`, `io.py`: Baseline helper utilities.

### 5.2 Documentation (`docs/`, root)
- `README.md`: Master publication README.
- `docs/REPRODUCIBILITY.md`: End-to-end reproduction manual and CLI instructions.
- `docs/DATA_DICTIONARY.md`: 21-variable clinical data dictionary and governance registry.
- `docs/RESEARCH_LIMITATIONS.md`: Methodological constraints, confounders, and ethical safeguards.
- `CONTRIBUTING.md`: Open-science contribution and research integrity guidelines.
- `CITATION.cff`: CFF 1.2.0 metadata for software and dataset citation.
- `LICENSE`: MIT License with dataset CC BY 4.0 provenance separation.
- `DATASET_NOTES.md`: Dataset versioning and licensing notes.

### 5.3 Research Reports & Deliverables (`reports/`)
- `IVF_Insight_Research_Report.md`: 57.7 KB — 21-section academic research monograph.
- `IVF_Insight_Research_Report.pdf`: 524.8 KB — 16-page publication-grade PDF.
- `references.bib`: 15 verified academic citations.
- `report_figure_manifest.csv`: 18 research figures mapped to sections and captions.
- `report_data_manifest.csv`: 20 research tables mapped to generating modules and CSV files.
- 20 structured analytical CSV files.
- Subdirectories: `figures/` (9 plots), `model_figures/` (8 plots), `robustness_figures/` (10 plots), `confusion_matrices/` (18 plots).

---

## 6. Proposed Git Commit Contents

The following files are proposed for the initial public commit (`feat: initial release of IVF Insight research repository`):

```text
.gitignore
.gitkeep
CITATION.cff
CONTRIBUTING.md
DATASET_NOTES.md
LICENSE
README.md
RESEARCH_LOG_TEMPLATE.md
pyproject.toml
requirements.txt

data/processed/.gitkeep
data/raw/.gitkeep
data/raw/README.md

docs/DATA_DICTIONARY.md
docs/REPRODUCIBILITY.md
docs/RESEARCH_LIMITATIONS.md

models/experiment_metadata.json

notebooks/01_dataset_audit_and_eda.ipynb
notebooks/02_exploratory_data_analysis.ipynb
notebooks/03_predictive_modelling.ipynb
notebooks/04_robustness_validation.ipynb
notebooks/05_statistical_integrity_audit.ipynb

reports/IVF_Insight_Research_Report.html
reports/IVF_Insight_Research_Report.md
reports/IVF_Insight_Research_Report.pdf
reports/references.bib
reports/report_data_manifest.csv
reports/report_figure_manifest.csv
reports/repository_audit_report.md
reports/*.csv (20 structured summary tables)
reports/figures/*.png (9 plots)
reports/model_figures/*.png (8 plots)
reports/robustness_figures/*.png (10 plots)
reports/confusion_matrices/*.png (18 plots)

src/ivf_insight/*.py (13 modules)
tests/*.py (8 test suites)
```

**Excluded from Commit (Protected by `.gitignore`):**
- `data/raw/Dataset Clean.xlsx` (Raw patient cycles)
- `data/raw/Normalized CSV.csv` (Raw normalized cycles)
- `models/*.joblib` (18 MB binary model pipelines)
- `.venv/`, `.pytest_cache/`, `__pycache__/`, `*.egg-info/`

---

## 7. Final Recommendations for Repository Release

1. **Approval Gate:** In accordance with user governance instructions, **do not push to remote GitHub automatically**. Present the proposed commit contents, audit results, and repository status to the user for formal approval.
2. **Post-Approval Action:** Once approved, execute:
   ```bash
   git add .
   git commit -m "feat: complete IVF Insight research repository (Phases 1-6)"
   git branch -M main
   # User specifies remote URL: git remote add origin <URL>
   # git push -u origin main
   ```
3. **Continuous Integration (CI):** A GitHub Actions workflow running `pytest` on Python 3.10, 3.11, and 3.12 can be configured using `pyproject.toml` and `requirements.txt`.
