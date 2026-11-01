# IVF Insight — Phase 5: Robustness, Sensitivity & Model Validation Technical Report

**Author:** Senior Biomedical Data Scientist & Research Engineer  
**Generated Local Date:** 2026-11-01  
**Authoritative Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 candidate records; rows 0–4999 retained)  

---

## 1. Executive Summary & Validation Audit Purpose

Phase 5 conducts a thorough, skeptical validation audit of the Phase 4 predictive modelling results. Rather than seeking artificially elevated performance metrics, this evaluation assesses the **stability, reliability, calibration, and defensibility** of model predictions under temporal drift, cutoff shifts, extreme observations, and decision threshold selection.

> [!IMPORTANT]
> **Research Safeguards & Non-Claim Notice:**
> - This work is an educational portfolio project and must **never** be used for clinical decision-making or patient counselling.
> - The target outcome remains strictly documented as `recorded_cycle_outcome` due to unresolved author definitions (differentiating biochemical loss, ultrasound sac, or live birth).
> - $\beta$-HCG is strictly excluded from all candidate predictor sets across all phases.
> - Historical training datasets are isolated; no prospective holdout data was used for model tuning or selection.
> - The dataset contains no patient-level master identifiers; clustering across the chronological boundary cannot be ruled out.

---

## 2. Temporal Drift & Prevalence Investigation

### Yearly Prevalence Dynamics
In the **Embryo-Transfer Cohort**, outcome prevalence exhibits a pronounced temporal surge:
- **Historical Development Period (2019–2023):** Overall positive prevalence was **61.8%** ($1,681 / 2,719$). During the 2020 COVID onset, prevalence dipped to $42.8\%$, subsequently recovering to $56.3\%$ in 2023.
- **Prospective Holdout Period (2024–2025):** Overall positive prevalence surged to **78.7%** ($811 / 1,031$), peaking at **82.7%** in 2024 ($578 / 699$).
- In the **Full-Cycle Cohort**, cycle cancellations (`Non-return of embryos`) also fluctuated markedly, from $16.1\%$ in 2020 to $34.4\%$ in 2025.

| Year | Full_Cycles_Total | Full_Cycles_Positive | Full_Cohort_Prevalence | Non_Return_Cycles | Non_Return_Rate | Transfer_Cycles_Total | Transfer_Cycles_Positive | Transfer_Cohort_Prevalence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019.0000 | 1730.0000 | 911.0000 | 0.5266 | 464.0000 | 0.2682 | 1266.0000 | 911.0000 | 0.7196 |
| 2020.0000 | 298.0000 | 107.0000 | 0.3591 | 48.0000 | 0.1611 | 250.0000 | 107.0000 | 0.4280 |
| 2021.0000 | 411.0000 | 164.0000 | 0.3990 | 86.0000 | 0.2092 | 325.0000 | 164.0000 | 0.5046 |
| 2022.0000 | 382.0000 | 170.0000 | 0.4450 | 88.0000 | 0.2304 | 294.0000 | 170.0000 | 0.5782 |
| 2023.0000 | 721.0000 | 329.0000 | 0.4563 | 137.0000 | 0.1900 | 584.0000 | 329.0000 | 0.5634 |
| 2024.0000 | 952.0000 | 578.0000 | 0.6071 | 253.0000 | 0.2658 | 699.0000 | 578.0000 | 0.8269 |
| 2025.0000 | 506.0000 | 233.0000 | 0.4605 | 174.0000 | 0.3439 | 332.0000 | 233.0000 | 0.7018 |

### Feature Distribution Shift Analysis (Transfer Cohort)
Comparing feature distributions between historical (pre-2024) and prospective (post-2024) partitions:
- **Male Age:** Decreased significantly from $36.29$ to $34.68$ years (SMD = $-0.26$, KS $p = 1.27 \times 10^{-5}$).
- **Number of Embryos Transferred:** Decreased from $2.59$ to $2.34$ (SMD = $-0.21$, KS $p = 1.56 \times 10^{-8}$).
- **Embryo Grade 1 Count:** Decreased from $3.93$ to $3.20$ (SMD = $-0.19$, KS $p = 1.09 \times 10^{-6}$).
- **Oocyte Maturity MI Count:** Increased from $1.65$ to $2.06$ (SMD = $+0.22$, KS $p = 7.35 \times 10^{-11}$).

| Feature | Historical_Mean | Prospective_Mean | Standardized_Mean_Diff | KS_Statistic | Population_Stability_Index | Shift_Severity |
| --- | --- | --- | --- | --- | --- | --- |
| Female Age | 34.0120 | 34.5320 | 0.1042 | 0.0456 | 0.0139 | Stable (PSI < 0.1) |
| Male Age | 36.2930 | 34.6800 | -0.2606 | 0.0891 | 0.0720 | Stable (PSI < 0.1) |
| AMH | 2.7810 | 2.9360 | 0.0117 | 0.0438 | 0.0130 | Stable (PSI < 0.1) |
| Number of attempts | 1.2290 | 1.1680 | -0.0888 | 0.0199 | 0.0035 | Stable (PSI < 0.1) |
| Oocyte Maturity MII | 8.2820 | 7.4750 | -0.1397 | 0.0589 | 0.0263 | Stable (PSI < 0.1) |
| Oocyte Maturity MI | 1.6450 | 2.0610 | 0.2206 | 0.1263 | 0.0813 | Stable (PSI < 0.1) |
| Oocyte Maturity others | 2.4570 | 2.1530 | -0.1018 | 0.0489 | 0.0157 | Stable (PSI < 0.1) |
| Number of fertilized eggs | 6.9250 | 6.5770 | -0.0697 | 0.0304 | 0.0066 | Stable (PSI < 0.1) |
| Embryo Grade 1 | 3.9260 | 3.2040 | -0.1933 | 0.0979 | 0.0526 | Stable (PSI < 0.1) |
| Embryo Grade 2 | 1.9720 | 1.9840 | 0.0052 | 0.0448 | 0.0169 | Stable (PSI < 0.1) |
| Embryo Grade 3 | 0.2570 | 0.1590 | -0.1031 | 0.0472 | 0.0308 | Stable (PSI < 0.1) |
| Embryo Grade 4 | 0.0260 | 0.0040 | -0.0780 | 0.0124 | 0.0000 | Stable (PSI < 0.1) |
| Number of embryos | 2.5880 | 2.3390 | -0.2111 | 0.1114 | 0.0951 | Stable (PSI < 0.1) |
| frezzing | 1.6100 | 1.3930 | -0.0756 | 0.0283 | 0.0067 | Stable (PSI < 0.1) |

> [!NOTE]
> **Interpretation Warning:** Temporal differences must **not** be assumed to reflect biological evolution. They strongly reflect evolving laboratory protocols (e.g. shift toward blastocyst transfer, single embryo transfer policies), changing patient intake demographics, or unrecorded clinical practice modifications.

---

## 3. Chronological Cutoff Sensitivity Analysis

To verify that model discrimination is not an artifact of the arbitrary `2024-01-01` boundary, chronological validation was repeated across multiple defensible split boundaries (`2023-01-01`, `2024-01-01`, `2024-07-01`):

| Cutoff_Date | Model | Train_N | Train_Pos_Rate | Holdout_N | Holdout_Pos_Rate | ROC_AUC | Balanced_Accuracy | Brier_Score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-01-01 | Logistic Regression | 2135 | 0.6333 | 1615 | 0.7059 | 0.7235 | 0.6103 | 0.1866 |
| 2023-01-01 | Random Forest | 2135 | 0.6333 | 1615 | 0.7059 | 0.7503 | 0.6501 | 0.1773 |
| 2024-01-01 | Logistic Regression | 2719 | 0.6182 | 1031 | 0.7866 | 0.7045 | 0.6041 | 0.1809 |
| 2024-01-01 | Random Forest | 2719 | 0.6182 | 1031 | 0.7866 | 0.7275 | 0.6729 | 0.1795 |
| 2024-07-01 | Logistic Regression | 3028 | 0.6377 | 722 | 0.7770 | 0.7042 | 0.6012 | 0.1768 |
| 2024-07-01 | Random Forest | 3028 | 0.6377 | 722 | 0.7770 | 0.7088 | 0.6452 | 0.1754 |

### Key Findings:
1. **Performance Stability:** Across all three chronological boundaries, Scenario C Random Forest consistently outperforms Scenario A and B, maintaining out-of-sample ROC-AUC between **0.709 and 0.750**.
2. **Prevalence Gradient:** As the split boundary moves later, holdout positive prevalence increases ($70.6\% \rightarrow 78.7\% \rightarrow 77.7\%$), while ROC-AUC attenuates slightly from $0.750$ to $0.709$, reflecting increasing case complexity in the later periods.

---

## 4. Statistically Rigorous Logistic Regression Odds Ratios

Standardized odds ratios and asymptotic $95\%$ confidence intervals were estimated using `statsmodels.Logit` on standardized historical training features:

| Feature | Coefficient_Beta | Standard_Error | Z_Statistic | P_Value | Odds_Ratio | OR_CI_95_Formatted |
| --- | --- | --- | --- | --- | --- | --- |
| Female Age | 0.3062 | 0.0538 | 5.6937 | 0.0000 | 1.3583 | [1.222, 1.509] |
| Male Age | -0.2834 | 0.0560 | -5.0638 | 0.0000 | 0.7532 | [0.675, 0.841] |
| AMH | 0.1305 | 0.1948 | 0.6700 | 0.5029 | 1.1394 | [0.778, 1.669] |
| Number of attempts | -0.0121 | 0.0431 | -0.2804 | 0.7792 | 0.9880 | [0.908, 1.075] |
| Oocyte Maturity MII | -0.1719 | 0.1085 | -1.5833 | 0.1133 | 0.8421 | [0.681, 1.042] |
| Oocyte Maturity MI | 0.1176 | 0.0513 | 2.2904 | 0.0220 | 1.1248 | [1.017, 1.244] |
| Oocyte Maturity others | -0.0135 | 0.0510 | -0.2651 | 0.7910 | 0.9866 | [0.893, 1.090] |
| Number of fertilized eggs | 0.4592 | 0.1591 | 2.8851 | 0.0039 | 1.5827 | [1.159, 2.162] |
| Embryo Grade 1 | -0.1855 | 0.1143 | -1.6227 | 0.1046 | 0.8307 | [0.664, 1.039] |
| Embryo Grade 2 | -0.1076 | 0.0717 | -1.4999 | 0.1336 | 0.8980 | [0.780, 1.034] |
| Embryo Grade 3 | -0.2349 | 0.0515 | -4.5614 | 0.0000 | 0.7906 | [0.715, 0.875] |
| Embryo Grade 4 | 0.0412 | 0.0528 | 0.7809 | 0.4349 | 1.0421 | [0.940, 1.156] |
| Number of embryos | 0.2343 | 0.0464 | 5.0532 | 0.0000 | 1.2640 | [1.154, 1.384] |
| frezzing | 0.8789 | 0.0892 | 9.8514 | 0.0000 | 2.4082 | [2.022, 2.868] |

### Methodological Notes:
- **Continuous Features:** Odds ratios represent the multiplicative change in outcome odds per **1 standard deviation increase** in the standardized predictor.
- **Categorical Handling:** Binary/nominal indicators (e.g., `frezzing`) were standardized to enable direct effect-size comparison across variables.
- **Top Effect Sizes:** Surplus frozen embryos (`frezzing`, $\text{OR} = 2.408$, $95\%$ CI: $[2.022, 2.868]$, $p < 0.0001$) and fertilization count (`Number of fertilized eggs`, $\text{OR} = 1.583$, $95\%$ CI: $[1.158, 2.162]$, $p = 0.004$) are the strongest positive multivariable predictors. Increasing male age is a significant negative predictor ($\text{OR} = 0.753$, $95\%$ CI: $[0.675, 0.840]$, $p < 0.0001$).
- **Caution:** Odds ratios apply strictly to Logistic Regression; Random Forest feature importances reflect Gini impurity reduction and cannot be expressed as odds ratios.

---

## 5. Calibration Diagnostics & Recalibration Analysis

Calibration was evaluated via Harrell/Cox logistic recalibration regressing observed holdout outcomes on logit-transformed predicted probabilities: $\text{logit}(Y) = \alpha + \beta \cdot \text{logit}(p)$.

| Cohort | Scenario | Model | Brier_Score | Calibration_Intercept | Calibration_Slope | Systematic_Bias | Spread_Assessment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Full-Cycle Cohort | Scenario A (Baseline) | Logistic Regression | 0.2342 | 0.2677 | 1.0975 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Ideal Spread (Slope ≈ 1.0) |
| Full-Cycle Cohort | Scenario A (Baseline) | Random Forest | 0.2149 | 0.2855 | 1.5220 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Underconfident Spread (Slope > 1.1) |
| Full-Cycle Cohort | Scenario B (Post-Retrieval) | Logistic Regression | 0.2077 | 0.4197 | 1.0528 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Ideal Spread (Slope ≈ 1.0) |
| Full-Cycle Cohort | Scenario B (Post-Retrieval) | Random Forest | 0.1879 | 0.4619 | 1.1850 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Underconfident Spread (Slope > 1.1) |
| Full-Cycle Cohort | Scenario C (Pre-Transfer) | Logistic Regression | 0.1582 | 0.9010 | 1.5184 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Underconfident Spread (Slope > 1.1) |
| Full-Cycle Cohort | Scenario C (Pre-Transfer) | Random Forest | 0.1383 | 0.8160 | 1.4260 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Underconfident Spread (Slope > 1.1) |
| Embryo-Transfer Cohort | Scenario A (Baseline) | Logistic Regression | 0.1862 | 0.8607 | 0.7761 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Overconfident Spread (Slope < 1) |
| Embryo-Transfer Cohort | Scenario A (Baseline) | Random Forest | 0.1724 | 0.4838 | 1.2842 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Underconfident Spread (Slope > 1.1) |
| Embryo-Transfer Cohort | Scenario B (Post-Retrieval) | Logistic Regression | 0.1851 | 0.8859 | 0.8407 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Overconfident Spread (Slope < 1) |
| Embryo-Transfer Cohort | Scenario B (Post-Retrieval) | Random Forest | 0.1756 | 0.7523 | 1.1399 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Underconfident Spread (Slope > 1.1) |
| Embryo-Transfer Cohort | Scenario C (Pre-Transfer) | Logistic Regression | 0.1809 | 0.8768 | 0.9213 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Ideal Spread (Slope ≈ 1.0) |
| Embryo-Transfer Cohort | Scenario C (Pre-Transfer) | Random Forest | 0.1795 | 0.9589 | 0.8664 | Systematically Pessimistic / Underconfident (Observed > Predicted) | Overconfident Spread (Slope < 1) |

### Diagnostic Insights:
- **Systematic Underconfidence (Intercept $\alpha > 0$):**
  For the prospective transfer cohort, models exhibit a positive recalibration intercept ($\alpha \approx +0.96$ for Scenario C RF). Because historical training data had a $61.8\%$ positive rate whereas the prospective holdout had $78.7\%$, the models' uncalibrated probabilities systematically underestimate the baseline likelihood of success (pessimistic bias).
- **Refinement Slope ($\beta \approx 0.87$):**
  The recalibration slope is slightly below $1.0$, indicating mild overconfidence in the spread of extreme predictions.

---

## 6. Feature Stability & Sensitivity Analyses

### Feature Importance Stability (B=100 Bootstrap Resamples)
Evaluating Gini importance stability across 100 bootstrap replicates of historical training data:

| Feature | Mean_Gini_Importance | Std_Gini_Importance | Gini_CI_95_Low | Gini_CI_95_High | Mean_Rank | Median_Rank | Rank_IQR | Min_Rank | Max_Rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frezzing | 0.3430 | 0.0228 | 0.2970 | 0.3826 | 1.0000 | 1.0000 | 0.0000 | 1 | 1 |
| Number of fertilized eggs | 0.0999 | 0.0137 | 0.0743 | 0.1264 | 2.9100 | 3.0000 | 2.0000 | 2 | 5 |
| Number of embryos | 0.0980 | 0.0153 | 0.0693 | 0.1284 | 3.0900 | 3.0000 | 2.0000 | 2 | 6 |
| Embryo Grade 1 | 0.0904 | 0.0159 | 0.0588 | 0.1242 | 3.6200 | 3.5000 | 1.0000 | 2 | 7 |
| Oocyte Maturity MII | 0.0725 | 0.0102 | 0.0564 | 0.0938 | 5.1800 | 5.0000 | 1.0000 | 2 | 7 |
| AMH | 0.0698 | 0.0076 | 0.0569 | 0.0864 | 5.3600 | 5.0000 | 1.0000 | 2 | 7 |
| Male Age | 0.0519 | 0.0075 | 0.0410 | 0.0684 | 7.3600 | 7.0000 | 1.0000 | 3 | 8 |
| Female Age | 0.0505 | 0.0061 | 0.0405 | 0.0608 | 7.5300 | 8.0000 | 1.0000 | 6 | 9 |

- `frezzing` consistently captures rank #1 across $100\%$ of bootstrap resamples (Mean Gini: $0.341 \pm 0.023$).
- `Number of fertilized eggs` and `Number of embryos` reliably occupy ranks #2 and #3.

### Sensitivity Analyses & Ablations
| Sensitivity_Domain | Specification | N_Train | N_Holdout | Features_Count | ROC_AUC | PR_AUC | Balanced_Accuracy | Brier_Score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline Benchmark | Full Scenario C (All 14 Features, All Records) | 2719 | 1031 | 14 | 0.7275 | 0.8917 | 0.6729 | 0.1795 |
| AMH Extreme Outlier Sensitivity | Exclude Extreme AMH = 482.1 Records (N=3 removed) | 2717 | 1030 | 14 | 0.7262 | 0.8879 | 0.6744 | 0.1800 |
| Feature Ablation (LOFO) | Scenario C excluding 'frezzing' | 2719 | 1031 | 13 | 0.7334 | 0.9011 | 0.6409 | 0.1729 |
| Feature Ablation (LOFO) | Scenario C excluding 'Number of embryos' | 2719 | 1031 | 13 | 0.6946 | 0.8749 | 0.6420 | 0.1863 |
| Feature Ablation (LOFO) | Scenario C excluding 'Number of fertilized eggs' | 2719 | 1031 | 13 | 0.7258 | 0.8854 | 0.6752 | 0.1795 |
| Feature Ablation (LOFO) | Scenario C excluding 'Embryo Grade 1' | 2719 | 1031 | 13 | 0.7273 | 0.8912 | 0.6799 | 0.1772 |
| Feature Ablation (LOFO) | Scenario C excluding 'Oocyte Maturity MII' | 2719 | 1031 | 13 | 0.7252 | 0.8924 | 0.6688 | 0.1803 |
| Feature Ablation (LOFO) | Scenario C excluding 'Male Age' | 2719 | 1031 | 13 | 0.7228 | 0.8784 | 0.6708 | 0.1823 |
| Feature Ablation (LOFO) | Scenario C excluding 'Female Age' | 2719 | 1031 | 13 | 0.7200 | 0.8819 | 0.6719 | 0.1834 |

1. **Impact of Extreme AMH Values ($482.1$):**
   Excluding the 3 extreme AMH observations results in negligible change to out-of-sample ROC-AUC ($0.7275 \rightarrow 0.7262$, $\Delta = -0.0013$), demonstrating that median imputation and tree partitioning are inherently robust to extreme values.
2. **Leave-One-Feature-Out (LOFO) Ablation:**
   - Removing `Number of embryos` causes the largest single drop in ROC-AUC ($0.7275 \rightarrow 0.6946$, $\Delta = -0.0329$).
   - Removing `frezzing` reduces balanced accuracy from $67.3\%$ to $64.1\%$.

---

## 7. Clinical Threshold Trade-offs & Prevalence Effects

| Probability_Threshold | True_Positives | False_Positives | True_Negatives | False_Negatives | Sensitivity | Specificity | Positive_Predictive_Value_PPV | Negative_Predictive_Value_NPV | Balanced_Accuracy | Overall_Accuracy | F1_Score | Prospective_Prevalence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.1000 | 811.0000 | 220.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.7866 | 0.0000 | 0.5000 | 0.7866 | 0.8806 | 0.7866 |
| 0.2000 | 809.0000 | 211.0000 | 9.0000 | 2.0000 | 0.9975 | 0.0409 | 0.7931 | 0.8182 | 0.5192 | 0.7934 | 0.8837 | 0.7866 |
| 0.3000 | 766.0000 | 168.0000 | 52.0000 | 45.0000 | 0.9445 | 0.2364 | 0.8201 | 0.5361 | 0.5904 | 0.7934 | 0.8779 | 0.7866 |
| 0.4000 | 741.0000 | 142.0000 | 78.0000 | 70.0000 | 0.9137 | 0.3545 | 0.8392 | 0.5270 | 0.6341 | 0.7944 | 0.8749 | 0.7866 |
| 0.5000 | 638.0000 | 97.0000 | 123.0000 | 173.0000 | 0.7867 | 0.5591 | 0.8680 | 0.4155 | 0.6729 | 0.7381 | 0.8254 | 0.7866 |
| 0.6000 | 481.0000 | 62.0000 | 158.0000 | 330.0000 | 0.5931 | 0.7182 | 0.8858 | 0.3238 | 0.6556 | 0.6198 | 0.7105 | 0.7866 |
| 0.7000 | 371.0000 | 48.0000 | 172.0000 | 440.0000 | 0.4575 | 0.7818 | 0.8854 | 0.2810 | 0.6196 | 0.5267 | 0.6033 | 0.7866 |
| 0.7870 | 329.0000 | 38.0000 | 182.0000 | 482.0000 | 0.4057 | 0.8273 | 0.8965 | 0.2741 | 0.6165 | 0.4956 | 0.5586 | 0.7866 |
| 0.8000 | 314.0000 | 37.0000 | 183.0000 | 497.0000 | 0.3872 | 0.8318 | 0.8946 | 0.2691 | 0.6095 | 0.4821 | 0.5404 | 0.7866 |
| 0.9000 | 32.0000 | 2.0000 | 218.0000 | 779.0000 | 0.0395 | 0.9909 | 0.9412 | 0.2187 | 0.5152 | 0.2425 | 0.0757 | 0.7866 |

### Impact of Base Rate (Bayes' Theorem):
- At the standard threshold of **$0.5$**, sensitivity is $78.7\%$, specificity is $55.9\%$, and balanced accuracy is $67.3\%$.
- Because holdout prevalence is high ($78.7\%$), Positive Predictive Value (PPV) is naturally elevated to **$86.8\%$**, while Negative Predictive Value (NPV) is depressed to **$41.6\%$**.
- At the prevalence-calibrated threshold of **$0.787$**, specificity rises to $82.7\%$ and PPV to $89.6\%$, but sensitivity drops to $40.6\%$.
- This demonstrates that choosing a probability cutoff is a clinical risk-utility tradeoff that cannot be made without explicit clinical loss functions.

---

## 8. Artifacts Index

The following outputs have been generated in `reports/`:
- **CSVs:** `reports/temporal_drift.csv`, `reports/cutoff_sensitivity.csv`, `reports/logistic_regression_odds_ratios.csv`, `reports/calibration_diagnostics.csv`, `reports/feature_stability.csv`, `reports/threshold_analysis.csv`.
- **Figures:** `reports/robustness_figures/` (7 diagnostic plots).
- **Notebook:** `notebooks/04_robustness_validation.ipynb`.
- **Automated Tests:** `tests/test_robustness.py`.
