# IVF Insight v1.0.0 — Clinical Data Analysis and Predictive Modelling of IVF Treatment-Cycle Outcomes

This is the first formal release of **IVF Insight**, an open-source research project for retrospective exploratory data analysis, statistical investigation and predictive modelling of recorded IVF treatment-cycle outcomes.

The project analyses 5,000 candidate treatment-cycle records from the Version 1 Mendeley Data distribution, with an emphasis on dataset reconciliation, feature governance, leakage prevention, chronological holdout evaluation and statistical integrity.

> **Research status:** This is retrospective exploratory research, not a clinically validated prediction system or clinical decision-support tool. The analytical endpoint is referred to as `recorded_cycle_outcome` because its precise clinical definition and follow-up are not sufficiently established by the source documentation.

## Key capabilities

### 1. Dataset reconciliation and provenance
- Reconciles the original Excel distribution against the separately distributed CSV.
- Identifies 5,000 candidate records and excludes two synthetic boundary rows used for global normalization.
- Documents data-quality problems in the distributed CSV, including target-adjacent data handling concerns and preprocessing leakage.
- Preserves the original Excel records as the downstream analytical source.
- Documents dataset provenance, licensing and unresolved clinical metadata.

### 2. Milestone-based feature governance
Implements three feature scenarios corresponding to different treatment-cycle information milestones:

- **Scenario A — Pre-stimulation:** Female Age, Male Age, AMH and Number of attempts.
- **Scenario B — Post-retrieval:** Adds oocyte maturity and fertilization-related features.
- **Scenario C — Pre-transfer:** Adds embryo-grade counts, number of embryos and the dataset's `frezzing` variable.

The β-HCG measurement is excluded from predictive features because it is recorded after the outcome-generating treatment process and would introduce target leakage.

### 3. Chronological holdout evaluation
Uses a chronological cutoff of 1 January 2024 rather than relying exclusively on a randomly shuffled train/test split.

For the full-cycle cohort:
- Historical development cohort: 3,542 records.
- Chronological holdout cohort: 1,458 records.

For the transfer cohort:
- Historical development cohort: 2,719 records.
- Chronological holdout cohort: 1,031 records.

The chronological holdout is an internal temporal evaluation, not external or prospective clinical validation.

### 4. Predictive modelling findings
The Scenario C Random Forest achieved:

- **Full-cycle cohort:** ROC-AUC 0.903; PR-AUC 0.905.
- **Transfer cohort:** ROC-AUC 0.728; PR-AUC 0.892.

The full-cycle result is influenced by the inclusion of non-transfer cycles, which are recorded as class 0. It should not be interpreted as equivalent to predicting outcomes among cycles that reached embryo transfer.

The transfer-cohort result represents exploratory predictive discrimination conditional on transfer, not confirmed pregnancy prediction or clinical validation.

### 5. Statistical integrity and calibration
The project includes:
- Multivariable logistic regression and odds-ratio analysis.
- Collinearity assessment using variance inflation factors.
- Bootstrap feature-stability analysis.
- Sensitivity analysis for extreme AMH observations.
- Chronological cutoff sensitivity analysis.
- Calibration assessment using Brier score, calibration slope, calibration-in-the-large and observed-to-expected ratio.

The transfer-cohort chronological holdout showed underprediction:
- CITL: +0.9371.
- E/O: 0.7971.

These findings indicate calibration differences in the holdout cohort; their underlying causes cannot be established from this dataset alone.

### 6. Research and reproducibility resources
The repository includes:
- A 21-section research monograph.
- Markdown, HTML and PDF report formats.
- Exploratory analysis and modelling notebooks.
- Dataset reconciliation and feature-governance documentation.
- Statistical and robustness-analysis outputs.
- A command-line interface.
- Pinned dependency versions and automated tests.

The project test suite completed with 45 passing tests in the reported release-preparation audit.

## Important limitations

1. **Retrospective exploratory research:** The analysis is not intended for patient management, treatment selection or clinical decision-making.
2. **Uncertain endpoint:** The source documentation does not adequately establish whether `recorded_cycle_outcome` represents biochemical pregnancy, clinical pregnancy, ongoing pregnancy or live birth. Eight observations have discordant positive β-HCG values and class-0 recorded outcomes.
3. **Unverified feature semantics:** The clinical meaning of `frezzing` is not confirmed by the source documentation. Its statistical association should not be interpreted as an established clinical mechanism.
4. **Single-centre dataset:** The records originate from one fertility centre. Generalisability to other clinics and populations has not been established.
5. **No external validation:** No independent external cohort has been used to validate the models.
6. **No patient identifiers:** Patient-level clustering and repeat-cycle relationships cannot be reliably reconstructed.
7. **Uncertain variable timing:** The timing and definitions of some recorded variables are insufficiently documented.
8. **Unknown AMH units:** The dataset does not establish the assay or measurement units; no unit-specific clinical interpretation is claimed.

## Data and responsible use

The raw clinical dataset and serialized model binaries are not distributed in this repository. Users should consult the original dataset source and its licence before obtaining or using the data.

**IVF Insight is an educational and research portfolio project. Its outputs are not clinically validated and must not be used as a substitute for professional medical judgement.**
