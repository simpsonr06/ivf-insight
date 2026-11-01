# IVF Insight: Clinical Data Analysis, Predictive Modelling and Chronological Holdout Evaluation of IVF Treatment-Cycle Outcomes

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Dataset: Mendeley Data (CC BY 4.0)](https://img.shields.io/badge/Dataset-Mendeley%20Data-orange)](https://doi.org/10.17632/hd8yy6gzc5.1)
[![Tests: 45 passed](https://img.shields.io/badge/tests-45%20passed-brightgreen)](tests/)
[![Report: Academic Monograph](https://img.shields.io/badge/Report-PDF%20Monograph-red)](reports/IVF_Insight_Research_Report.pdf)

> **CRITICAL CLINICAL NOTICE:**  
> **This repository constitutes retrospective, exploratory biomedical data science and machine learning research. It is NOT a medical device, NOT software as a medical device (SaMD), and NOT a clinically validated decision-support tool. It must NOT be utilized for patient counselling, individualized prognosis, clinical gatekeeping, or embryo selection.**

---

## 1. Executive Research Overview

**IVF Insight** is an open-source scientific investigation with pinned dependencies and documented execution procedures supporting reproducibility in retrospective exploratory data analysis and predictive modelling of assisted reproductive technology (ART) treatment-cycle outcomes. Utilizing an authoritative clinical cohort of **5,000 candidate treatment cycles** (verified egg retrieval dates spanning 2019–2025), the study investigates whether clinical, laboratory, and embryological features available at pre-defined clinical milestones provide genuine out-of-sample discriminatory signal for predicting the binary treatment outcome (standardized as `recorded_cycle_outcome`).

### Core Scientific Contributions
1. **Forensic Dataset Reconciliation:** Reconciled discrepancies between raw Excel (`Dataset Clean.xlsx`, 5,002 rows) and Min-Max normalized CSV formats, identifying and excluding two synthetic boundary rows (rows 5000 and 5001) to recover 5,000 clean clinical observations.
2. **Differentiation of Full-Cycle and Post-Transfer Cohorts:** Demonstrated that the high full-cycle discrimination ($\text{ROC-AUC} = 0.903$) is substantially influenced by the inclusion of 1,250 non-transfer cycles (cancellations and zero-embryo outcomes). In the transfer-only cohort ($N=3,750$), where all patients received an embryo transfer, clinical discrimination is more moderate ($\text{ROC-AUC} = 0.728$).
3. **Investigation of the Multivariable Female Age Association:** In multivariable logistic regression on the transfer cohort, Female Age exhibited a counterintuitive positive association ($\text{OR} = 1.358$, $95\%$ CI: $[1.222, 1.509]$). Stepwise modeling revealed that adjusting for correlated male partner age ($r = 0.526$, $\text{OR} = 0.753$) substantially amplified the female age coefficient, consistent with reciprocal statistical suppression. Potential non-causal contributing factors include selection on reaching embryo transfer and unrecorded donor-oocyte utilization in older patients, rather than a genuine biological advantage of advanced maternal age.
4. **Chronological Holdout Evaluation & Calibration Drift:** Evaluated models across a strict chronological holdout cutoff (`2024-01-01`), discovering a substantial temporal prevalence surge ($61.8\% \rightarrow 78.7\%$) that induces systematic underconfidence ($\text{CITL} = +0.9371$, $E/O = 0.7971$).
5. **Standardized Feature Governance:** Clarified that the dataset variable `frezzing` is an **integer count** (values 0–25, median 0). While its exact clinical cryopreservation protocol remains unrecorded in the source dataset, it was the strongest multivariable predictive feature in the exploratory model ($\text{OR} = 2.408$, Gini importance 0.341), while target leakage from $\beta$-HCG was strictly barred.

---

## 2. Research Questions

| ID | Research Question | Analytical Strategy | Primary Finding |
| :--- | :--- | :--- | :--- |
| **$Q_1$** | How do raw Excel and normalized CSV representations diverge, and how can data hygiene be restored? | Order-agnostic hashing, schema reconciliation, and boundary audit. | Excluded 2 synthetic normalization rows; sanitized attempt encoding; barred normalized CSV from predictive modeling. |
| **$Q_2$** | What is the incremental prognostic value across successive clinical decision milestones? | Milestone-based scenario progression: Baseline (4 feats) $\rightarrow$ Post-Retrieval (8 feats) $\rightarrow$ Pre-Transfer (14 feats). | In the Transfer Cohort, ROC-AUC increases incrementally: $0.674 \rightarrow 0.691 \rightarrow 0.728$. |
| **$Q_3$** | Does out-of-sample performance persist under strict chronological holdout evaluation? | Chronological split at `2024-01-01` (Historical Train: 2,719; Holdout Test: 1,031). | Performance remains stable across alternative cutoffs (`2023-01-01` to `2024-07-01`; AUC $0.709$–$0.750$). |
| **$Q_4$** | Does temporal drift distort baseline risk and model calibration across chronological partitions? | Harrell/Cox logistic recalibration, CITL offset derivation, PSI metrics. | Severe baseline calibration drift: $\text{CITL} = +0.9371$; average predicted risk was $62.7\%$ vs $78.7\%$ observed. |
| **$Q_5$** | What multivariable mechanisms explain the counterintuitive associations of age and surplus embryos? | Hierarchically nested regression models, suppression diagnostics, restricted cubic splines, VIF audits. | Adjusting for male partner age ($r = 0.526$) amplifies the female age coefficient (consistent with reciprocal suppression), with transfer selection and potential unrecorded donor oocytes evaluated as non-causal explanatory hypotheses; fertilized eggs has high collinearity ($\text{VIF} = 11.14$). |

---

## 3. Dataset Provenance & Cohort Definitions

### Dataset Provenance
- **Primary Source:** Maghdid, S., Rashid, T. A., & Askar, S. (2026). *Comprehensive Dataset Profile of In Vitro Fertilization (IVF) Clinical and Embryological Data*. Mendeley Data, Version 1. [DOI: 10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1).
- **Licence:** Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
- **Origin:** Single private fertility center in Erbil, Kurdistan Region of Iraq (verified egg retrieval records spanning January 2019 to June 2025).

### Analytical Cohort Definitions
- **Full-Cycle Cohort ($N=5,000$):** All initiated IVF/ICSI cycles. Outcome distribution: 2,508 Class 0 ($50.16\%$) vs 2,492 Class 1 ($49.84\%$). Contains 1,250 cancelled cycles where no embryos were transferred.
- **Embryo-Transfer Cohort ($N=3,750$):** Cycles where embryo transfer took place (`Number of embryos` $\ge 1$). Outcome distribution: 1,258 Class 0 ($33.55\%$) vs 2,492 Class 1 ($66.45\%$).
- **Target Endpoint:** Standardized as `recorded_cycle_outcome` (source header: `Output(failed implantation or successful implantation)`). The source authors do not document the exact clinical definition of the endpoint (whether initial $\beta$-HCG seropositivity, gestational sac presence, clinical pregnancy, or live birth). While the binary outcome strongly correlates with post-transfer serum $\beta$-HCG, eight discordant cases (positive $\beta$-HCG with recorded Class 0) and unrecorded subsequent pregnancy loss mean the clinical endpoint remains explicitly unresolved.

---

## 4. Chronological Holdout Evaluation & Model Performance

### Chronological Holdout Performance (Holdout Cutoff: `2024-01-01`)

Evaluated on unseen chronological holdout cycles ($N=1,031$ in Embryo-Transfer Cohort; $N=1,458$ in Full-Cycle Cohort). Metrics reported with $95\%$ bootstrap confidence intervals:

| Cohort Partition | Prediction Scenario | Model Architecture | ROC-AUC [95% CI] | PR-AUC [95% CI] | Balanced Accuracy | Brier Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Embryo-Transfer** | Scenario A (Baseline) | Majority Class Baseline | 0.500 [0.500, 0.500] | 0.787 [0.760, 0.811] | 50.0% | 0.213 |
| **Embryo-Transfer** | Scenario A (Baseline) | Logistic Regression | 0.655 [0.617, 0.697] | 0.865 [0.838, 0.893] | 63.4% | 0.186 |
| **Embryo-Transfer** | Scenario A (Baseline) | Random Forest | 0.674 [0.635, 0.716] | 0.871 [0.843, 0.897] | 63.2% | 0.172 |
| **Embryo-Transfer** | Scenario B (Post-Retrieval) | Logistic Regression | 0.672 [0.632, 0.710] | 0.873 [0.847, 0.900] | 64.1% | 0.185 |
| **Embryo-Transfer** | Scenario B (Post-Retrieval) | Random Forest | 0.691 [0.648, 0.729] | 0.875 [0.847, 0.900] | 64.9% | 0.176 |
| **Embryo-Transfer** | **Scenario C (Pre-Transfer)** | **Logistic Regression** | **0.712 [0.672, 0.749]** | **0.887 [0.862, 0.912]** | **66.1%** | **0.181** |
| **Embryo-Transfer** | **Scenario C (Pre-Transfer)** | **Random Forest** | **0.728 [0.689, 0.765]** | **0.892 [0.868, 0.915]** | **67.3%** | **0.179** |
| Full-Cycle | Scenario C (Pre-Transfer) | Logistic Regression | 0.852 [0.832, 0.871] | 0.858 [0.836, 0.880] | 78.4% | 0.158 |
| Full-Cycle | Scenario C (Pre-Transfer) | Random Forest | 0.903 [0.886, 0.918]* | 0.914 [0.896, 0.931] | 79.7% | 0.138 |

*\*Note: The Full-Cycle 0.903 ROC-AUC is substantially influenced by the inclusion of non-transfer cycles with zero transferred embryos, whereas transfer-only discrimination is more moderate (ROC-AUC 0.728).*

### Standardized Multivariable Odds Ratios (Transfer Scenario C)
Estimated via `statsmodels.Logit` on standardized historical training data ($N=2,719$):
- **Dataset Variable `frezzing`:** $\text{OR} = 2.408$ ($95\%$ CI: $[2.022, 2.868]$, $p < 0.0001$) — *strongest multivariable predictive feature (integer count 0–25; exact clinical vitrification protocol unverified in source records)*
- **Fertilized Oocytes (`Number of fertilized eggs`):** $\text{OR} = 1.583$ ($95\%$ CI: $[1.159, 2.162]$, $p = 0.0039$)
- **Female Age (`Female Age`):** $\text{OR} = 1.358$ ($95\%$ CI: $[1.222, 1.509]$, $p < 0.0001$) — *positive multivariable association observed after adjusting for male partner age; evaluated as potential statistical suppression, transfer conditioning, or unrecorded donor-oocyte utilization*
- **Transferred Embryos (`Number of embryos`):** $\text{OR} = 1.264$ ($95\%$ CI: $[1.154, 1.384]$, $p < 0.0001$)
- **Male Partner Age (`Male Age`):** $\text{OR} = 0.753$ ($95\%$ CI: $[0.675, 0.841]$, $p < 0.0001$)

---

## 5. Repository Architecture

```text
ivf-insight/
├── data/
│   ├── raw/                           # Downloaded source datasets (git-ignored)
│   │   ├── README.md                  # Dataset acquisition and SHA-256 verification guide
│   │   └── .gitkeep
│   └── processed/                     # Intermediate preprocessed caches (git-ignored)
├── docs/
│   ├── REPRODUCIBILITY.md             # Complete step-by-step reproduction manual
│   ├── DATA_DICTIONARY.md             # 21-variable clinical definitions and registry
│   └── RESEARCH_LIMITATIONS.md        # Methodological constraints and ethical safeguards
├── models/
│   ├── experiment_metadata.json       # Hyperparameters, random seeds, and cohort sizes
│   └── *.joblib                       # 18 serialized model pipelines (git-ignored binaries)
├── notebooks/
│   ├── 01_dataset_audit_and_eda.ipynb # Initial forensic audit and schema validation
│   ├── 02_exploratory_data_analysis.ipynb # Dual-cohort distributions and FDR tests
│   ├── 03_predictive_modelling.ipynb  # Chronological model benchmarks and curves
│   ├── 04_robustness_validation.ipynb # Drift, sensitivity, calibration diagnostics
│   └── 05_statistical_integrity_audit.ipynb # Multicollinearity, CITL, suppression audit
├── reports/
│   ├── IVF_Insight_Research_Report.md # Formal 21-section academic research monograph
│   ├── IVF_Insight_Research_Report.pdf # Typeset academic publication monograph (16 pages)
│   ├── references.bib                 # BibTeX bibliographic database (15 verified citations)
│   ├── report_figure_manifest.csv     # Index of 18 diagnostic research figures
│   ├── report_data_manifest.csv       # Index of 20 structured report tables (21 tracked CSVs: 19 analytical result CSVs, 1 figure manifest, and 1 report-data manifest)
│   ├── figures/                       # EDA and demographic distribution figures
│   ├── model_figures/                 # ROC, PR, calibration, and feature importance plots
│   ├── robustness_figures/            # Temporal drift, cubic splines, and VIF plots
│   └── confusion_matrices/            # 18 cross-tabulated confusion matrices
├── src/ivf_insight/
│   ├── cli.py                         # Unified command-line interface entry point
│   ├── reconciliation.py              # Phase 1 dataset reconciliation and boundary filtering
│   ├── governance.py                  # Phase 2 feature registry and scenario governance
│   ├── eda.py                         # Phase 3 exploratory data analysis and FDR testing
│   ├── experiments.py                 # Phase 4 chronological holdout predictive modeling pipeline
│   ├── validation.py                  # Phase 5 temporal drift and sensitivity audits
│   ├── integrity_audit.py             # Phase 5.1 multicollinearity and suppression audit
│   └── report.py                      # Phase 6 academic report and PDF compiler
├── tests/                             # 8 automated pytest suites (45 passing tests)
├── CITATION.cff                       # Citation File Format metadata
├── CONTRIBUTING.md                    # Open science contribution guidelines
├── LICENSE                            # MIT Open Source Code License
├── pyproject.toml                     # Package build configuration and dependencies
├── requirements.txt                   # Pinned core production requirements
└── README.md                          # Repository overview and documentation
```

---

## 6. Quick Start & Reproduction

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### Installation
```bash
git clone https://github.com/simpsonr06/ivf-insight.git
cd ivf-insight

python -m venv .venv
# Activate virtual environment:
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

### Dataset Acquisition
Download `Dataset Clean.xlsx` from [Mendeley Data](https://doi.org/10.17632/hd8yy6gzc5.1) and place it under `data/raw/`. Verify integrity:
```powershell
Get-FileHash "data/raw/Dataset Clean.xlsx" -Algorithm SHA256
# Expected: 8914bf7a331c01bc1c66eeb81bf405b3476da3d80674536385a166f5d52dbf32
```

### Run Full Analytical Pipeline via CLI
```bash
# Phase 1: Reconcile datasets and exclude synthetic boundaries
ivf-insight reconcile --excel "data/raw/Dataset Clean.xlsx" --csv "data/raw/Normalized CSV.csv" --output-dir reports

# Phase 2: Generate feature governance registry
ivf-insight governance --output-dir reports

# Phase 3: Run dual-cohort exploratory analysis and FDR hypothesis tests
ivf-insight eda --excel "data/raw/Dataset Clean.xlsx" --output-dir reports

# Phase 4: Execute 18 predictive experiments across chronological split
ivf-insight experiment --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --models-dir models

# Phase 5: Run robustness, sensitivity, temporal drift, and threshold validation
ivf-insight validate --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --figures-dir reports/robustness_figures

# Phase 5.1: Run statistical integrity audit (suppression, VIF, canonical CITL)
ivf-insight audit --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --figures-dir reports/robustness_figures

# Phase 6: Compile the 21-section academic monograph (Markdown, HTML, PDF)
ivf-insight report --output-dir reports
```

### Run Automated Test Suite
```bash
python -m pytest -v
```
*Expected: 45 passed in ~30s.*

---

## 7. Key Research Findings & Interpretive Guidelines

1. **Dataset Variable `frezzing` is the Strongest Multivariable Feature:**
   - The dataset variable `frezzing` (integer values 0–25) was the single strongest multivariable predictive feature in the exploratory model ($\text{OR} = 2.408$; Gini importance $0.341$). Because the source dataset does not document the underlying clinical cryopreservation protocol or timing (e.g., Day 3 cleavage vs Day 5 blastocyst vitrification), it must be interpreted strictly as an exploratory predictive feature whose exact clinical meaning remains unverified.
2. **Transfer-Cohort Predictive Discrimination is Moderate:**
   - While pre-transfer discrimination in the transfer cohort reaches $\text{ROC-AUC} = 0.728$, standard routine clinical features alone cannot perfectly determine `recorded_cycle_outcome`. Unmeasured clinical and biological variables may contribute to the remaining unexplained variation.
3. **Temporal Drift Causes Severe Model Underconfidence:**
   - In chronological holdout evaluation, baseline prevalence shifted from $61.8\%$ to $78.7\%$. Models trained on historical data showed underprediction in the chronological holdout (CITL = +0.9371; E/O = 0.7971). Because clinical practice and baseline prevalence can evolve over time, clinical models require ongoing temporal calibration monitoring, with formal recalibration evaluated where appropriate.
4. **Extreme Observations Have Minimal Influence:**
   - Three patient records had extreme $\text{AMH} = 482.1$ (unit not specified in source dataset). Retaining vs winsorizing these records resulted in negligible metric shifts ($\Delta \text{AUC} = -0.0013$), demonstrating tree-based and rank-based robustness.

---

## 8. Limitations & Ethical Safeguards

- **No Longitudinal Identifiers:** The dataset lacks patient/couple IDs; repeat cycles cannot be clustered, which may lead to anticonservative variance estimation.
- **Unresolved Clinical Endpoint:** The source authors do not document whether Class 1 reflects initial $\beta$-HCG seropositivity, gestational sac confirmation, clinical pregnancy, or live birth. While the outcome strongly tracks serum $\beta$-HCG, eight discordant cases and unrecorded subsequent pregnancy attrition mean the clinical endpoint remains unresolved and must not be equated with live birth or confirmed clinical pregnancy.
- **Missing Biological Covariates:** Crucial confounders including oocyte origin (donor vs autologous), embryo stage (Day 3 cleavage vs Day 5 blastocyst), endometrial thickness, and PGT-A aneuploidy status are unrecorded.
- **No External Validation:** Findings reflect a single fertility clinic in Erbil, Iraq. Results must not be assumed generalizable to other patient populations or clinical protocols.

*Read the full disclosure in [docs/RESEARCH_LIMITATIONS.md](docs/RESEARCH_LIMITATIONS.md).*

---

## 9. Citation & Bibliographic Metadata

If you utilize this codebase, analytical methodologies, or findings, please cite both this repository and the primary dataset:

```bibtex
@misc{simpson2026ivfinsight,
  author = {Simpson, R.},
  title = {IVF Insight: Exploratory Clinical Data Analysis, Predictive Modelling and Chronological Holdout Evaluation of IVF Treatment-Cycle Outcomes},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/simpsonr06/ivf-insight}},
  note = {Version 0.1.0}
}

@misc{maghdid2026ivf,
  author = {Maghdid, Shadman and Rashid, Tarik A. and Askar, Sangar},
  title = {Comprehensive Dataset Profile of In Vitro Fertilization (IVF) Clinical and Embryological Data},
  year = {2026},
  month = {January},
  publisher = {Mendeley Data},
  version = {1},
  doi = {10.17632/hd8yy6gzc5.1},
  howpublished = {\url{https://doi.org/10.17632/hd8yy6gzc5.1}},
  note = {Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0)}
}
```

---

## 10. Licence

- **Code & Software:** Licensed under the [MIT License](LICENSE).
- **Dataset:** Mendeley Data, Version 1 is licensed separately under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- **Research Documentation:** Released under Open Access for scientific transparency.
