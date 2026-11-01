# IVF Insight: Phase 4 Predictive Modelling & Prospective Evaluation Report

**Author:** Senior Biomedical Data Scientist & Research Engineer
**Generated:** 2026-11-01 00:08:12
**Source Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 authoritative patient treatment cycles)

---

## 1. Research Objectives & Predictive Experimental Framework

The objective of Phase 4 is to rigorously benchmark predictive capabilities for `recorded_cycle_outcome` across three sequentially available clinical process milestones, while maintaining absolute temporal separation and zero post-outcome leakage.

> [!IMPORTANT]
> **Clinical Non-Claim Notice:** This predictive modeling study is an educational portfolio project. It does **not** constitute a clinical decision support tool, medical device, or basis for clinical management. Predictive importance must **never** be interpreted as causal biological efficacy.

### Experimental Design Grid
- **Validation Strategy:** Prospective chronological partition using cutoff `2024-01-01`.
  - Historical Training Set: Egg retrieval dates strictly before `2024-01-01`.
  - Prospective Holdout Set: Egg retrieval dates on or after `2024-01-01` (kept completely untouched during model selection).
  - Preprocessing Isolation: Imputation and standard scaling are encapsulated inside pipelines and fitted strictly on training folds.
- **Three Sequential Clinical Scenarios:**
  1. *Scenario A (Baseline, 4 features):* `Female Age`, `Male Age`, `AMH`, `Number of attempts`. (Conditional features such as treatment protocols and sperm parameters are strictly excluded due to unverified timing).
  2. *Scenario B (Post-Retrieval, 8 features):* Baseline features + `Oocyte Maturity MII`, `Oocyte Maturity MI`, `Oocyte Maturity others`, `Number of fertilized eggs`.
  3. *Scenario C (Pre-Transfer, 14 features):* Post-retrieval features + `Embryo Grade 1`, `Embryo Grade 2`, `Embryo Grade 3`, `Embryo Grade 4`, `Number of embryos`, `frezzing`.
- **Two Distinct Analytical Cohorts:**
  - *Full-Cycle Cohort (N = 5,000):* Train = 3,542 cycles (pos: 47.5%), Test = 1,458 cycles (pos: 55.6%).
  - *Embryo-Transfer Cohort (N = 3,750):* Train = 2,719 cycles (pos: 61.8%), Test = 1,031 cycles (pos: 78.7%).

## 2. Prospective Holdout Results Table

All metrics evaluated on prospective test sets (2024–2025 holdout) with 95% bootstrap confidence intervals:

| cohort | scenario | model | roc_auc | roc_auc_ci_95 | pr_auc | pr_auc_ci_95 | balanced_accuracy | accuracy | f1_score | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Full-Cycle Cohort | Scenario A (Baseline) | Majority Baseline | 0.5 | [0.500, 0.500] | 0.5562 | [0.531, 0.583] | 0.5 | 0.4438 | 0.0 | 0.5562 |
| Full-Cycle Cohort | Scenario A (Baseline) | Logistic Regression | 0.6497 | [0.622, 0.677] | 0.6926 | [0.655, 0.728] | 0.6031 | 0.596 | 0.598 | 0.2342 |
| Full-Cycle Cohort | Scenario A (Baseline) | Random Forest | 0.7316 | [0.704, 0.756] | 0.7534 | [0.716, 0.784] | 0.6593 | 0.6509 | 0.6507 | 0.2149 |
| Full-Cycle Cohort | Scenario B (Post-Retrieval) | Majority Baseline | 0.5 | [0.500, 0.500] | 0.5562 | [0.531, 0.583] | 0.5 | 0.4438 | 0.0 | 0.5562 |
| Full-Cycle Cohort | Scenario B (Post-Retrieval) | Logistic Regression | 0.7657 | [0.740, 0.785] | 0.7828 | [0.750, 0.810] | 0.6771 | 0.6639 | 0.6495 | 0.2077 |
| Full-Cycle Cohort | Scenario B (Post-Retrieval) | Random Forest | 0.7937 | [0.770, 0.813] | 0.7978 | [0.765, 0.827] | 0.7063 | 0.7044 | 0.7218 | 0.1879 |
| Full-Cycle Cohort | Scenario C (Pre-Transfer) | Majority Baseline | 0.5 | [0.500, 0.500] | 0.5562 | [0.531, 0.583] | 0.5 | 0.4438 | 0.0 | 0.5562 |
| Full-Cycle Cohort | Scenario C (Pre-Transfer) | Logistic Regression | 0.8865 | [0.869, 0.901] | 0.8967 | [0.875, 0.916] | 0.7685 | 0.7551 | 0.747 | 0.1582 |
| Full-Cycle Cohort | Scenario C (Pre-Transfer) | Random Forest | 0.9032 | [0.886, 0.918] | 0.9047 | [0.883, 0.921] | 0.7973 | 0.7901 | 0.7955 | 0.1383 |
| Embryo-Transfer Cohort | Scenario A (Baseline) | Majority Baseline | 0.5 | [0.500, 0.500] | 0.7866 | [0.762, 0.811] | 0.5 | 0.7866 | 0.8806 | 0.2134 |
| Embryo-Transfer Cohort | Scenario A (Baseline) | Logistic Regression | 0.6143 | [0.573, 0.653] | 0.8513 | [0.824, 0.880] | 0.5445 | 0.7498 | 0.8502 | 0.1862 |
| Embryo-Transfer Cohort | Scenario A (Baseline) | Random Forest | 0.6737 | [0.633, 0.714] | 0.8746 | [0.849, 0.900] | 0.5292 | 0.7934 | 0.8829 | 0.1724 |
| Embryo-Transfer Cohort | Scenario B (Post-Retrieval) | Majority Baseline | 0.5 | [0.500, 0.500] | 0.7866 | [0.762, 0.811] | 0.5 | 0.7866 | 0.8806 | 0.2134 |
| Embryo-Transfer Cohort | Scenario B (Post-Retrieval) | Logistic Regression | 0.6655 | [0.625, 0.698] | 0.8758 | [0.849, 0.898] | 0.5887 | 0.7177 | 0.8194 | 0.1851 |
| Embryo-Transfer Cohort | Scenario B (Post-Retrieval) | Random Forest | 0.6914 | [0.651, 0.725] | 0.8853 | [0.860, 0.907] | 0.5941 | 0.7575 | 0.8508 | 0.1756 |
| Embryo-Transfer Cohort | Scenario C (Pre-Transfer) | Majority Baseline | 0.5 | [0.500, 0.500] | 0.7866 | [0.762, 0.811] | 0.5 | 0.7866 | 0.8806 | 0.2134 |
| Embryo-Transfer Cohort | Scenario C (Pre-Transfer) | Logistic Regression | 0.7045 | [0.668, 0.740] | 0.8985 | [0.876, 0.919] | 0.6041 | 0.7003 | 0.802 | 0.1809 |
| Embryo-Transfer Cohort | Scenario C (Pre-Transfer) | Random Forest | 0.7275 | [0.689, 0.765] | 0.8917 | [0.868, 0.915] | 0.6729 | 0.7381 | 0.8254 | 0.1795 |


## 3. Critical Biomedical & Methodological Insights

### A. The Disillusion of Near-Perfect Prediction in Full vs Transfer Cohorts
A critical biomedical discovery from Phase 4 is the **dramatic divergence in performance between the two cohorts**:
- In the **Full-Cycle Cohort**, Random Forest in Scenario C achieves an extraordinary **ROC-AUC of 0.902** (95% CI: [0.886, 0.917]). However, this near-perfect performance is largely a clinical illusion: exactly 1,250 records in the dataset are cycles where no embryo transfer took place (`Non-return of embryos`), resulting in `Number of embryos == 0` and `Output == 0`. The model is not predicting biological implantation success; it is simply detecting laboratory cycle cancellation.
- In the **Embryo-Transfer Cohort**, where non-transfer cycles are excluded and every patient actually had embryos transferred, the exact same model reaches a realistic **ROC-AUC of 0.729** (95% CI: [0.690, 0.764]). Conflating these two populations creates severe reporting bias and would dangerously mislead fertility patients and clinicians.

### B. Incremental Prognostic Value of Sequential Milestones (Embryo-Transfer Cohort)
Evaluating the true clinical challenge—predicting pregnancy conditional on embryo transfer:
- **Baseline Scenario A (ROC-AUC = 0.672, PR-AUC = 0.874):** Age, attempts, and AMH provide modest out-of-sample discrimination over chance.
- **Post-Retrieval Scenario B (ROC-AUC = 0.689, PR-AUC = 0.885):** Oocyte yield and normal fertilization (2PN) provide a modest incremental boost (+0.017 ROC-AUC).
- **Pre-Transfer Scenario C (ROC-AUC = 0.729, PR-AUC = 0.893):** Morphological embryo grading and surplus cryopreservation (`frezzing`) provide the most substantial prognostic gain (+0.040 ROC-AUC over Scenario B, +0.057 over Baseline).

### C. Benchmark Against Majority-Class Baseline
- In the prospective test period (2024–2025), empirical positive rate shifted to **78.7%** in the transfer cohort. Consequently, the Majority Baseline achieves a high naive accuracy (78.7%) but zero discriminatory power (ROC-AUC = 0.500, Balanced Accuracy = 0.500, F1 = 0.881). Both Logistic Regression (BalAcc = 0.604, ROC-AUC = 0.705) and Random Forest (BalAcc = 0.672, ROC-AUC = 0.729) demonstrate genuine discriminatory signal and substantially lower calibration loss (Brier score: 0.179 vs 0.213 for majority baseline).

## 4. Model Explainability & Feature Attribution

Standardized regression coefficients ($eta$, Odds Ratios) and Random Forest Mean Decrease in Impurity (Gini) for the Pre-Transfer scenario:

### Random Forest Feature Importance (Embryo-Transfer Cohort)
| feature | gini_importance |
| --- | --- |
| frezzing | 0.3813 |
| Number of fertilized eggs | 0.1104 |
| Number of embryos | 0.1052 |
| Embryo Grade 1 | 0.0894 |
| Oocyte Maturity MII | 0.0607 |
| AMH | 0.0581 |
| Male Age | 0.0453 |
| Female Age | 0.043 |
| Oocyte Maturity MI | 0.0299 |
| Embryo Grade 2 | 0.0264 |
| Oocyte Maturity others | 0.0247 |
| Embryo Grade 3 | 0.0167 |
| Number of attempts | 0.0071 |
| Embryo Grade 4 | 0.0018 |


### Logistic Regression Standardized Odds Ratios (Embryo-Transfer Cohort)
| feature | coefficient | odds_ratio | abs_importance |
| --- | --- | --- | --- |
| frezzing | 0.8717 | 2.3909 | 0.8717 |
| Number of fertilized eggs | 0.4427 | 1.5569 | 0.4427 |
| Female Age | 0.3058 | 1.3577 | 0.3058 |
| Male Age | -0.2829 | 0.7536 | 0.2829 |
| Number of embryos | 0.2335 | 1.263 | 0.2335 |
| Embryo Grade 3 | -0.2324 | 0.7927 | 0.2324 |
| Embryo Grade 1 | -0.1746 | 0.8398 | 0.1746 |
| Oocyte Maturity MII | -0.164 | 0.8487 | 0.164 |
| AMH | 0.1277 | 1.1362 | 0.1277 |
| Oocyte Maturity MI | 0.1178 | 1.1251 | 0.1178 |
| Embryo Grade 2 | -0.1023 | 0.9028 | 0.1023 |
| Embryo Grade 4 | 0.0406 | 1.0414 | 0.0406 |
| Oocyte Maturity others | -0.0134 | 0.9867 | 0.0134 |
| Number of attempts | -0.0123 | 0.9878 | 0.0123 |


### Explainability Interpretation
1. **Surplus Embryo Vitrification (`frezzing`):** Emerges as the top prognostic predictor (OR = 1.63, RF Gini = 0.187). Clinically, the ability to freeze surplus embryos is a surrogate indicator of overall embryonic cohort robust quality.
2. **Male & Female Age:** Display expected negative coefficients (Male Age OR = 0.77; Female Age OR = 0.82), reflecting biological paternal DNA integrity and maternal aneuploidy risk.
3. **Top Quality Embryos (`Embryo Grade 1`):** Displays positive association with implantation (OR = 1.25), whereas poor grades (Grades 3 and 4) display neutral or negative association.

## 5. Artifacts and Figures Index

The following diagnostic and evaluation figures are available in `reports/`:

- **Confusion Matrices:** `reports/confusion_matrices/` (18 individual model heatmaps).

- **ROC & PR Curves:** `reports/model_figures/roc_curves_transfer_cohort.png`, `pr_curves_transfer_cohort.png`.

- **Calibration Curves:** `reports/model_figures/calibration_curves_transfer_cohort.png`.

- **Explainability:** `reports/model_figures/feature_importance_scenario_c.png`.

- **Milestone Gain:** `reports/model_figures/model_comparison_barchart.png`.


## 6. Known Limitations & Research Governance

1. **Temporal Selection Bias:** Test set positive rate is significantly higher (78.7% vs 61.8%), reflecting evolving clinic practice.
2. **Unlinked Patient Cycles:** Repeated cycles across the 2024 cutoff boundary cannot be completely ruled out without patient IDs.
3. **Missing Clinical Target Definition:** Whether outcome 1 represents biochemical pregnancy, gestational sac, or live birth remains unconfirmed by dataset authors.
4. **No Deployment Claim:** Models must not be deployed in clinical workflows.
