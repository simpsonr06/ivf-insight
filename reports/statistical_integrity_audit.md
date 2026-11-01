# IVF Insight — Phase 5.1: Statistical Integrity & Interpretation Audit Technical Report

**Author:** Senior Biomedical Data Scientist & Research Engineer  
**Date:** 2026-11-01  
**Authoritative Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 candidate records; rows 0–4999 retained)  

---

## 1. Executive Summary & Audit Objectives

Phase 5.1 conducts a critical biostatistical audit of Phase 4 and Phase 5 findings. Its objective is to **resolve questionable conclusions, unmask statistical suppression and multicollinearity, audit calibration definitions, clarify variable meanings, and prevent clinical over-interpretation** before consolidating the project into a final research report.

> [!IMPORTANT]
> **Core Principle: Prioritize Statistical Integrity Over Attractive Metrics**
> - The positive regression coefficient for Female Age is explicitly audited as **statistical suppression and case-selection**, not biological benefit.
> - Speculative clinical hypotheses regarding blastocyst adoption and culture media changes are marked as **untestable** within this dataset.
> - The term `frezzing` is clarified as an **integer count of surplus cryopreserved embryos**, not a binary indicator.
> - Calibration-in-the-large is audited using canonical offset formulation rather than interpreting the unconstrained intercept in isolation.

---

## 2. Temporal Drift Interpretation Audit

In Phase 5, we observed a surge in prospective transfer-cohort positive prevalence to **78.7%** (and **82.7%** in 2024). This audit explicitly distinguishes between empirical facts observed in the dataset and speculative hypotheses that cannot be proven:

| Proposed_Hypothesis | Empirical_Evidence_in_Dataset | Variables_Supporting | Testability_Status | Scientific_Validity |
| --- | --- | --- | --- | --- |
| Embryo Transfer Count Policy Shift | Mean embryos transferred dropped from 2.59 (historical) to 2.34 (prospective) (SMD = -0.21, KS p = 1.56e-8). | Number of embryos | Supported by Dataset | Directly observed reduction in embryos transferred per patient cycle. |
| Patient Demographic Case-Mix Shift | Male Age dropped from 36.29 to 34.68 (SMD = -0.26, KS p = 1.27e-5). Female Age and AMH showed no significant shift (p > 0.08). | Male Age | Partially Supported | Male partner age decreased; female demographic and ovarian reserve remained stable. |
| Shift to Blastocyst Culture (Day 5/6) | None. The dataset records no culture day, biopsy timing, or blastocyst stage indicators. | None (Untracked) | Untestable Speculation | Speculative hypothesis; dataset documentation does not record Day 3 vs Day 5 transfer. |
| Laboratory Equipment / Culture Media Changes | None. No incubator type, time-lapse system, or culture medium details are recorded. | None (Untracked) | Untestable Speculation | Speculative hypothesis; laboratory protocols and consumables are unrecorded. |
| Diagnostic Threshold or Outcome Definition Shift | Prospective positive rate jumped to 82.7% (2024) and 70.2% (2025). Clinical definition of class 1 remains unconfirmed by authors. | recorded_cycle_outcome, B-HCG | Partially Supported / Unverified Endpoint | Large prevalence jump observed, but author confirmation is required to determine if criteria shifted. |

### Critical Audit Takeaway:
- **What is empirically supported:** The mean number of embryos transferred dropped from $2.59$ to $2.34$ ($p < 0.0001$), and male partner age dropped by $1.6$ years ($p < 0.0001$).
- **What is untestable:** The dataset records **no culture day (Day 3 vs Day 5)**, no laboratory media brands, and no clinic intake guidelines. Any claim that blastocyst adoption or laboratory improvements caused the temporal shift is **scientifically untestable speculation** and must not be stated as factual causal inference.

---

## 3. Female Age Odds-Ratio Paradox: Suppression, Confounding & Non-Linearity

In standard human reproductive biology, advancing female age is universally recognized as the primary cause of oocyte aneuploidy and implantation failure. However, in this dataset, multivariable logistic regression yielded a positive standardized coefficient ($\beta = +0.3062$, $\text{OR} = 1.358$, $p < 0.0001$).

### Progression of Female Age Association Across Model Specifications
| Model_Specification | Female_Age_Beta_Std | Female_Age_SE | Female_Age_P_Value | Female_Age_OR_Std | Female_Age_OR_95_CI | Male_Age_Beta_Std | Male_Age_P_Value | Male_Age_OR_Std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Transfer Cohort — Unadjusted Female Age | 0.1336 | 0.0397 | 0.0008 | 1.1429 | [1.057, 1.235] | NaN | NaN | NaN |
| Transfer Cohort — Unadjusted Male Age | NaN | NaN | NaN | NaN | N/A | -0.1835 | 0.0000 | 0.8323 |
| Transfer Cohort — Female Age + Male Age | 0.3504 | 0.0510 | 0.0000 | 1.4196 | [1.284, 1.569] | -0.3846 | 0.0000 | 0.6807 |
| Transfer Cohort — Scenario A (Baseline) | 0.3326 | 0.0515 | 0.0000 | 1.3946 | [1.261, 1.543] | -0.3588 | 0.0000 | 0.6985 |
| Transfer Cohort — Scenario B (Post-Retrieval) | 0.2881 | 0.0529 | 0.0000 | 1.3339 | [1.203, 1.480] | -0.2713 | 0.0000 | 0.7624 |
| Transfer Cohort — Scenario C (Pre-Transfer) | 0.3062 | 0.0538 | 0.0000 | 1.3583 | [1.222, 1.509] | -0.2834 | 0.0000 | 0.7532 |
| Full-Cycle Cohort — Unadjusted Female Age | 0.0594 | 0.0337 | 0.0778 | 1.0612 | [0.993, 1.134] | NaN | NaN | NaN |
| Full-Cycle Cohort — Scenario C (Pre-Transfer) | 0.2573 | 0.0488 | 0.0000 | 1.2934 | [1.175, 1.423] | -0.2559 | 0.0000 | 0.7742 |

### Deconstruction of the Paradox:
1. **Reciprocal Suppression with Male Age:**
   Female Age and Male Age are positively correlated ($r = 0.526$). In unadjusted regression, Male Age has a negative association ($\beta = -0.0297$, $p < 0.0001$), while Female Age is mildly positive ($\beta = +0.0268$, $p = 0.001$). When both variables enter the model simultaneously, **reciprocal suppression** occurs: Female Age amplifies to $\beta = +0.0667$ ($p < 0.0001$) while Male Age amplifies to $\beta = -0.0580$ ($p < 0.0001$).
2. **Empirical Age-Bracket Outcome Rates:**
   | Age_Group | Cycle_Count | Positive_Count | Observed_Prevalence | Mean_Embryos_Transferred | Mean_Fertilized_Eggs | Mean_Male_Age |
| --- | --- | --- | --- | --- | --- | --- |
| 18-29 | 501 | 282 | 0.5629 | 2.6400 | 7.0500 | 31.1100 |
| 30-34 | 968 | 594 | 0.6136 | 2.5600 | 6.8200 | 35.4500 |
| 35-38 | 750 | 472 | 0.6293 | 2.6100 | 6.7300 | 38.0100 |
| 39-42 | 382 | 249 | 0.6518 | 2.5500 | 7.3400 | 40.0100 |
| 43-55 | 118 | 84 | 0.7119 | 2.5800 | 7.1400 | 42.3000 |
   In the transfer cohort, observed positive rates paradoxically increase from $56.3\%$ in women aged $18$–$29$ to $71.2\%$ in women aged $43$–$55$.
3. **Plausible Biostatistical Explanations:**
   - **Severe Transfer Conditioning / Berkson's Bias:** Older women who produce blastocysts of sufficient quality to undergo embryo transfer represent an extraordinarily selected subset of high-reserve patients.
   - **Unrecorded Donor Oocytes:** In clinical registries, women aged $>42$ using donor eggs achieve success rates $>50\%$, whereas autologous success rates are $<5\%$. The dataset authors **did not record oocyte origin (autologous vs donor)**. If older women in this private cohort utilized donor oocytes, this would explain the positive association.
4. **Spline Non-Linearity Test:**
   Restricted cubic splines with 4 knots ($df = 4$) showed no significant non-linearity over a linear logit model (Likelihood Ratio test statistic = $0.6767$, $df = 3$, $p = 0.8787$).
5. **Mandatory Non-Causal Conclusion:**
   The positive coefficient for Female Age is a composite of **statistical suppression with Male Age, conditioning on transfer completion, and potential unrecorded egg donation**. It must **never** be interpreted as biological evidence that older age improves IVF outcomes.

---

## 4. Logistic Regression Diagnostics: Multicollinearity & Influence

Diagnostics were performed on the 14-feature Pre-Transfer Scenario C model:

| Feature | Standardized_Beta_Wald | Wald_SE | Wald_P_Value | Wald_Odds_Ratio | Wald_OR_95_CI | Bootstrap_Beta_Mean | Bootstrap_Beta_95_CI | Bootstrap_Odds_Ratio | Bootstrap_OR_95_CI | Variance_Inflation_Factor | Collinearity_Flag | Box_Tidwell_P_Value | Logit_Linearity_Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Female Age | 0.3062 | 0.0538 | 0.0000 | 1.3583 | [1.222, 1.509] | 0.3064 | [0.213, 0.417] | 1.3585 | [1.237, 1.517] | 1.4400 | Low (VIF < 5) | 0.6623 | Linear (p >= 0.05) |
| Male Age | -0.2834 | 0.0560 | 0.0000 | 0.7532 | [0.675, 0.841] | -0.2839 | [-0.390, -0.179] | 0.7529 | [0.677, 0.836] | 1.5100 | Low (VIF < 5) | 0.0178 | Non-linear in logit |
| AMH | 0.1305 | 0.1948 | 0.5029 | 1.1394 | [0.778, 1.669] | 0.1671 | [-0.108, 0.528] | 1.1818 | [0.898, 1.695] | 1.0200 | Low (VIF < 5) | 0.0001 | Non-linear in logit |
| Number of attempts | -0.0121 | 0.0431 | 0.7792 | 0.9880 | [0.908, 1.075] | -0.0171 | [-0.101, 0.077] | 0.9831 | [0.904, 1.080] | 1.0200 | Low (VIF < 5) | 0.5168 | Linear (p >= 0.05) |
| Oocyte Maturity MII | -0.1719 | 0.1085 | 0.1133 | 0.8421 | [0.681, 1.042] | -0.1681 | [-0.392, 0.025] | 0.8453 | [0.676, 1.025] | 5.9700 | Moderate (VIF > 5) | 0.0000 | Non-linear in logit |
| Oocyte Maturity MI | 0.1176 | 0.0513 | 0.0220 | 1.1248 | [1.017, 1.244] | 0.1173 | [0.033, 0.219] | 1.1245 | [1.034, 1.244] | 1.1500 | Low (VIF < 5) | 0.1278 | Linear (p >= 0.05) |
| Oocyte Maturity others | -0.0135 | 0.0510 | 0.7910 | 0.9866 | [0.893, 1.090] | -0.0116 | [-0.106, 0.079] | 0.9885 | [0.899, 1.082] | 1.1500 | Low (VIF < 5) | 0.0982 | Linear (p >= 0.05) |
| Number of fertilized eggs | 0.4592 | 0.1591 | 0.0039 | 1.5827 | [1.159, 2.162] | 0.4663 | [0.190, 0.793] | 1.5940 | [1.209, 2.209] | 11.1400 | Severe (VIF > 10) | 0.0000 | Non-linear in logit |
| Embryo Grade 1 | -0.1855 | 0.1143 | 0.1046 | 0.8307 | [0.664, 1.039] | -0.1925 | [-0.442, 0.024] | 0.8249 | [0.643, 1.024] | 5.3800 | Moderate (VIF > 5) | 0.0000 | Non-linear in logit |
| Embryo Grade 2 | -0.1076 | 0.0717 | 0.1336 | 0.8980 | [0.780, 1.034] | -0.1078 | [-0.247, 0.020] | 0.8978 | [0.781, 1.020] | 2.2400 | Low (VIF < 5) | 0.0015 | Non-linear in logit |
| Embryo Grade 3 | -0.2349 | 0.0515 | 0.0000 | 0.7906 | [0.715, 0.875] | -0.2392 | [-0.347, -0.131] | 0.7872 | [0.707, 0.877] | 1.3400 | Low (VIF < 5) | 0.5389 | Linear (p >= 0.05) |
| Embryo Grade 4 | 0.0412 | 0.0528 | 0.4349 | 1.0421 | [0.940, 1.156] | 0.0180 | [-0.135, 0.137] | 1.0181 | [0.874, 1.147] | 1.1100 | Low (VIF < 5) | NaN | Discrete / Untestable |
| Number of embryos | 0.2343 | 0.0464 | 0.0000 | 1.2640 | [1.154, 1.384] | 0.2380 | [0.150, 0.335] | 1.2687 | [1.162, 1.397] | 1.1800 | Low (VIF < 5) | 0.0000 | Non-linear in logit |
| frezzing | 0.8789 | 0.0892 | 0.0000 | 2.4082 | [2.022, 2.868] | 0.8909 | [0.681, 1.108] | 2.4372 | [1.975, 3.030] | 2.1600 | Low (VIF < 5) | 0.0001 | Non-linear in logit |

### Diagnostic Findings:
- **Multicollinearity:**
  `Number of fertilized eggs` exhibits severe multicollinearity with a **VIF of 11.14** (due to biological alignment with `Oocyte Maturity MII`, VIF = 5.97, and `Embryo Grade 1`, VIF = 5.38). This severe collinearity inflates standard errors for embryological counts.
  In contrast, `Female Age` ($	ext{VIF} = 1.44$) and `Male Age` ($	ext{VIF} = 1.51$) have low VIFs, proving that their opposite signs are driven by **correlation suppression**, not variance inflation.
- **Linearity in Logit (Box-Tidwell):**
  `Female Age` satisfies linearity in the logit ($p = 0.6623$). However, `AMH` ($p = 0.0001$) and `Male Age` ($p = 0.0178$) violate linearity, reflecting AMH's extreme skewness and threshold effects.
- **Condition Number & Influence:**
  Condition number of scaled predictors is **8.01** (well within the safe range $< 30$). Maximum Cook's distance is **0.3614** (only 1 observation exceeds Cook's $D > 0.05$), confirming absence of toxic leverage points distorting the fit.
- **Bootstrap Validation:**
  $B=500$ non-parametric bootstrap confidence intervals align closely with asymptotic Wald intervals, confirming parameter stability under resampling.

---

## 5. Calibration Audit: Canonical CITL vs Two-Parameter Recalibration

A biostatistical audit of calibration equations was conducted to avoid the common pitfall of interpreting recalibration intercepts in isolation:

| Scenario | Model | Observed_Holdout_Prevalence | Mean_Predicted_Probability | Expected_to_Observed_Ratio_EO | CITL_Offset_Alpha | CITL_95_CI | Calibration_Slope_Beta | Calibration_Slope_95_CI | Unconstrained_Intercept_Alpha | Brier_Score | Calibration_Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scenario A (Baseline) | Logistic Regression | 0.7866 | 0.6440 | 0.8187 | 0.7495 | [0.597, 0.902] | 0.7761 | [0.477, 1.076] | 0.8607 | 0.1862 | Systematic Underconfidence (CITL > 0, E/O < 1; actual success rate exceeds predicted) |
| Scenario A (Baseline) | Random Forest | 0.7866 | 0.6661 | 0.8468 | 0.6437 | [0.492, 0.796] | 1.2842 | [0.918, 1.650] | 0.4838 | 0.1724 | Systematic Underconfidence (CITL > 0, E/O < 1; actual success rate exceeds predicted) |
| Scenario B (Post-Retrieval) | Logistic Regression | 0.7866 | 0.6344 | 0.8065 | 0.8303 | [0.675, 0.985] | 0.8407 | [0.612, 1.069] | 0.8859 | 0.1851 | Systematic Underconfidence (CITL > 0, E/O < 1; actual success rate exceeds predicted) |
| Scenario B (Post-Retrieval) | Random Forest | 0.7866 | 0.6383 | 0.8114 | 0.8045 | [0.650, 0.959] | 1.1399 | [0.887, 1.393] | 0.7523 | 0.1756 | Systematic Underconfidence (CITL > 0, E/O < 1; actual success rate exceeds predicted) |
| Scenario C (Pre-Transfer) | Logistic Regression | 0.7866 | 0.6342 | 0.8062 | 0.8568 | [0.700, 1.014] | 0.9213 | [0.704, 1.139] | 0.8768 | 0.1809 | Systematic Underconfidence (CITL > 0, E/O < 1; actual success rate exceeds predicted) |
| Scenario C (Pre-Transfer) | Random Forest | 0.7866 | 0.6270 | 0.7971 | 0.9371 | [0.776, 1.098] | 0.8664 | [0.692, 1.040] | 0.9589 | 0.1795 | Systematic Underconfidence (CITL > 0, E/O < 1; actual success rate exceeds predicted) |

### Diagnostic Insights:
1. **Canonical Calibration-in-the-Large (CITL):**
   Estimated via $\text{logit}(P(Y=1)) = \alpha + \text{offset}(\text{logit}(p))$, where slope is constrained to $1.0$.
   For Pre-Transfer Random Forest, $\text{CITL} = +0.9371$ ($95\%$ CI: $[0.777, 1.098]$).
   Because $\text{CITL} > 0$ and the Expected-to-Observed ratio ($E/O$) is **$0.7971$**, uncalibrated model probabilities systematically underestimate success in the prospective period by $\approx 20\%$.
2. **Calibration Slope:**
   Estimated via unconstrained $\text{logit}(P(Y=1)) = \alpha + \beta \cdot \text{logit}(p)$.
   Slope is $\beta = 0.8664$ ($95\%$ CI: $[0.692, 1.040]$). The 95% CI includes $1.0$, indicating acceptable refinement spread without statistically significant over-dispersion.
3. **Recalibration Intercept Distinction:**
   The unconstrained intercept ($\alpha = +0.9589$) measures calibration at $\text{logit}(p) = 0$ ($p = 0.5$) and must not be confused with canonical CITL ($+0.9371$). Both metrics consistently reflect baseline probability underconfidence due to the prospective prevalence shift.

---

## 6. Feature Definition & Explainability Audit

| Feature_Name | Dataset_Typo_Notice | Variable_Type | Original_Meaning | Common_Misinterpretation | Model_Explanation_Metric |
| --- | --- | --- | --- | --- | --- |
| frezzing | Misspelled as 'frezzing' in raw Excel/CSV dataset; refers to cryopreservation. | Integer Count (Range: 0–25; Median: 0) | Total count of surplus supernumerary embryos cryopreserved for subsequent frozen cycles. | Binary frozen indicator (0/1). It is an integer count, where 0 = no surplus embryos frozen, and >0 reflects high embryo yield. | Standardized OR (LR) = 2.408 (OR per 1 SD increase). Gini Importance (RF) = 0.341 (Rank 1). |
| Number of embryos | Standard spelling. | Integer Count (Range: 0–8; Median: 2) | Number of embryos transferred into the uterus during the fresh transfer procedure. | Conflating transferred embryos with total embryos created. Non-transfers have count = 0. | Standardized OR (LR) = 1.264. Gini Importance (RF) = 0.100 (Rank 3). |
| Embryo Grade 1 | Standard spelling. | Integer Count (Range: 0–32; Median: 2) | Count of top-quality Grade 1 embryos formed (optimal cleavage rate, even blastomeres, minimal fragmentation). | Treating grade as an ordinal categorical label rather than an integer cohort count. | Standardized OR (LR) = 0.831 (collinear with fertilized eggs). Gini (RF) = 0.090. |
| Embryo Grade 2 | Standard spelling. | Integer Count (Range: 0–32; Median: 1) | Count of good-quality Grade 2 embryos formed (minor blastomere asymmetry, <20% fragmentation). | Treating grade as an ordinal categorical label. | Standardized OR (LR) = 0.898. Gini (RF) = 0.046. |
| Embryo Grade 3 | Standard spelling. | Integer Count (Range: 0–11; Median: 0) | Count of fair-quality Grade 3 embryos formed (moderate fragmentation 20–50%, uneven blastomeres). | Treating grade as an ordinal categorical label. | Standardized OR (LR) = 0.791 (p < 0.0001; negative association). Gini (RF) = 0.015. |
| Embryo Grade 4 | Standard spelling. | Integer Count (Range: 0–9; Median: 0) | Count of poor-quality Grade 4 embryos formed (severe fragmentation >50%, degenerated blastomeres). | Treating grade as an ordinal categorical label. | Standardized OR (LR) = 1.015 (p = 0.435; non-significant due to sparsity). Gini (RF) = 0.003. |
| Number of fertilized eggs | Standard spelling. | Integer Count (Range: 0–35; Median: 5) | Count of normally fertilized oocytes displaying two pronuclei (2PN) post-insemination/ICSI. | Treating as independent predictor without recognizing severe multicollinearity with MII (VIF = 11.14). | Standardized OR (LR) = 1.583. Gini Importance (RF) = 0.101 (Rank 2). |

### Key Clarifications:
- **`frezzing` is an Integer Count:** It records the number of surplus embryos frozen (range 0–25; median 0), **not** a binary indicator.
- **Embryological Variables are Counts:** `Embryo Grade 1` through `Grade 4` are counts of embryos belonging to each grade, not categorical variables.
- **Separation of Explainability Metrics:**
  - Standardized Odds Ratios ($\text{OR} = e^\beta$) apply strictly to Logistic Regression and represent the multiplicative change in odds per **1 standard deviation increase** in the standardized predictor.
  - Random Forest feature importances represent Gini impurity reduction or permutation score drops and cannot be expressed as odds ratios.

---

## 7. Decision Threshold Interpretation Safeguards

1. **Exploratory Character:** The threshold trade-off table generated in Phase 5 is strictly an **exploratory statistical exercise**.
2. **Prevalence is Not a Valid Clinical Cutoff:** The empirical holdout prevalence ($0.787$) is an observational frequency, **not** a clinically validated decision threshold.
3. **Bayes' Theorem Implication:** Because prevalence is high ($78.7\%$), Positive Predictive Value is naturally high ($86.8\%$) while Negative Predictive Value is naturally low ($41.6\%$) at threshold $0.5$.
4. **Clinical Non-Recommendation:** No classification threshold is recommended for clinical management, patient selection, or cycle cancellation. Choosing a threshold requires explicit clinical loss matrices balancing false negatives (denying viable transfer) against false positives (ineffective transfer).

---

## 8. Artifacts Index

- **Report:** `reports/statistical_integrity_audit.md`
- **CSVs:** `reports/logistic_regression_diagnostics.csv`, `reports/age_association_analysis.csv`, `reports/calibration_audit.csv`, `reports/feature_interpretation_audit.csv`
- **Figures:** `reports/robustness_figures/age_association_splines.png`, `reports/robustness_figures/multicollinearity_vif.png`, `reports/robustness_figures/calibration_citl_recalibration.png`
- **Notebook:** `notebooks/05_statistical_integrity_audit.ipynb`
- **Automated Tests:** `tests/test_statistical_integrity.py`
