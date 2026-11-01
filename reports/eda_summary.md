# IVF Insight: Exploratory Data Analysis & Statistical Investigation Report

**Author:** Senior Biomedical Data Scientist & Research Engineer
**Generated:** 2026-10-31 23:27:49
**Source Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 candidate treatment cycles)

---

## 1. Executive Summary & Cohort Framework

This Phase 3 exploratory data analysis provides a comprehensive statistical investigation of the authoritative 5,000-cycle IVF clinical dataset. To ensure clinical validity and prevent conflation of cycle cancellations with biological implantation failure, the analysis strictly preserves two distinct analytical cohorts throughout all evaluations:

- **Cohort A (Full-Cycle Cohort, N = 5,000):** All treatment cycles initiating controlled ovarian stimulation. Recorded positive cycle outcome prevalence is **49.84%** (Class 0 = 2,508, Class 1 = 2,492). Class 0 includes 1,250 cycles with no embryo transfer ('Non-return of embryos') where implantation was impossible.

- **Cohort B (Embryo-Transfer Cohort, N = 3,750):** Restricted strictly to completed intrauterine embryo transfers, excluding the 1,250 non-return cases. In this clinical sub-cohort, recorded positive outcome prevalence is **{target_transfer.get(1.0, 0)/len(df_transfer)*100:.2f}%** (Class 0 = 1,258, Class 1 = 2,492).

> [!IMPORTANT]
> **Non-Interchangeability Warning:** Evaluating predictive models on the full-cycle cohort vs the embryo-transfer cohort yields substantially different statistical distributions, effect sizes, and clinical interpretations. Treating these cohorts as interchangeable introduces severe selection bias.

## 2. Demographic & Baseline Clinical Characteristics

- **Female Age:** Spans 20 to 49 years (Mean: 34.3 ± 4.9; Median: 34, IQR: 7). Distribution is unimodal and approximately symmetric (skewness: 0.22).
- **Male Age:** Spans 19 to 57 years (Mean: 36.3 ± 6.2; Median: 37, IQR: 9; skewness: 0.36).
- **Number of Attempts:** Ranges from 1 to 10 (Median: 1, IQR: 1; 81.3% of cycles are recorded as attempt 1).
- **AMH (Anti-Müllerian Hormone):** Spans 0.0 to 482.1 (Median: 1.59, IQR: 2.36). Distribution is heavily right-skewed (skewness: 38.19). Exactly 16 cycles have AMH > 20, and 3 cycles have an extreme value of 482.1.

## 3. Statistical Association Analysis (Mann–Whitney U & Chi-Square with BH-FDR Correction)

Univariate tests were conducted separately for each analytical cohort against `recorded_cycle_outcome`. All p-values were corrected for multiple testing using the Benjamini–Hochberg False Discovery Rate (FDR) procedure. **Statistical significance reflects observed association, NOT clinical causation.**

### Key Statistical Discrepancies Between Cohorts

1. **Female Age Effect:** In the Full-Cycle Cohort, Female Age is **not significantly associated** with outcome ($p = 0.276, q = 0.283$). However, in the Embryo-Transfer Cohort, Female Age is **highly significant** ($p = 0.00033, q = 0.00049$; rank-biserial $r = 0.072$). This divergence occurs because non-return cycles occur across all age tiers due to ovarian response failure, masking age-dependent implantation rates.

2. **Embryonic Yield Effect Sizes:** In the Full-Cycle Cohort, `Number of embryos` displays an enormous rank-biserial correlation ($r = 0.612, p = 0.0$) because all 1,250 non-return cycles have 0 embryos and outcome 0. In the Embryo-Transfer Cohort, where every cycle yielded transferable embryos, the effect size drops to **$r = 0.234$** ($p = 7.6 \times 10^{-34}$). Conflating cohorts artificially inflates embryonic predictor importance.

3. **Top Predictors in Embryo-Transfer Cohort:** Ranked by effect size ($r$ / Cramer's V):
  - `frezzing` (Surplus cryopreserved embryos): $r = 0.355, q = 6.0 \times 10^-90$
  - `Medicines and treatments` (Protocol ID): Cramer's $V = 0.336, q = 1.0 \times 10^-25$
  - `Number of fertilized eggs`: $r = 0.313, q = 9.5 \times 10^-55$
  - `Embryo Grade 1`: $r = 0.275, q = 5.8 \times 10^-43$
  - `Oocyte Maturity MII`: $r = 0.274, q = 1.7 \times 10^-42$
  - `Number of embryos`: $r = 0.234, q = 2.7 \times 10^-33$

## 4. In-Depth Data Quality & Anomaly Audits

### A. AMH Extreme Values & Assay Uncertainty
- Exactly 3 treatment cycles (Rows 443, 2291, 3974) exhibit identical extreme AMH values of **482.1**.
- In Row 2291, the patient yielded 42 mature MII oocytes and 35 fertilized eggs, a massive response consistent with high ovarian response. Because measurement units are not specified in the source dataset, the physical units and assay scale remain unconfirmed without author clarification. In Rows 443 and 3974, only 3 MII oocytes were retrieved, suggesting possible data entry typographical errors or assay artifacts. Observations are preserved intact without automated removal.

### B. Treatment Protocol Cardinality & Distribution
- Feature `Medicines and treatments` exhibits **182 unique integer codes** (spanning 1 to 183).
- The distribution is extremely heavy-tailed: Protocol ID 1 alone accounts for **816 cycles (16.32%)**.
- The top 5 protocols collectively account for **40.18%** of all treatments.
- Exactly **12 protocols are singletons** (prescribed to only 1 patient). Continuous scaling of this feature is strictly prohibited.

### C. Oocyte & Embryo Count Consistency
- In 549 cycles (11.0%), normally fertilized eggs (2PN) exceed Metaphase II (MII) counts. As noted in embryology practice, this reflects in vitro maturation of immature MI oocytes overnight, or conventional IVF insemination.
- In 12 cycles (0.24%), fertilized eggs exceed total retrieved oocytes (an embryological recording anomaly).
- In 3,317 cycles, the sum of Morphological Grades 1–4 exceeds `Number of embryos`. `Number of embryos` reflects viable, transfer-quality embryos, whereas Grades 3–4 denote degenerated/arrested embryos.

### D. Temporal Drift in Cycle Outcomes (2019–2025)
Annual positive outcome prevalence varies markedly across the 7-year timeline:
- **2019:** Full = 52.7%, Transfer = 72.0% (N = 1,730)
- **2020:** Full = 35.9%, Transfer = 42.8% (N = 298) — notable clinical dip coinciding with COVID-19 pandemic service restrictions.
- **2021:** Full = 39.9%, Transfer = 50.5% (N = 411)
- **2022:** Full = 44.5%, Transfer = 57.8% (N = 382)
- **2023:** Full = 45.6%, Transfer = 56.3% (N = 721)
- **2024:** Full = 60.7%, Transfer = 82.7% (N = 952)
- **2025:** Full = 46.0%, Transfer = 70.2% (N = 506)

### E. Potential Repeated-Cycle Clustering
- Exactly **1539 unique baseline demographic triplets** (Female Age, Male Age, AMH) appear more than once, encompassing **3297 cycles (65.94%)**.
- In the absence of patient identifiers, repeated-cycle leakage across validation partitions cannot be completely ruled out.

## 5. Generated Artifacts & Visualizations Index

The following publication-grade figures were generated and saved in `reports/figures/`:

1. `target_distribution.png`: Target outcome comparison between Full-Cycle and Embryo-Transfer cohorts.

2. `age_distributions.png`: Female and Male partner age histograms with KDE and summary statistics.

3. `amh_distribution.png`: Linear zoomed (0-25) and log10-transformed AMH distributions highlighting extreme values.

4. `sperm_parameters.png`: Semen concentration, motility, and morphology distributions.

5. `oocyte_maturity_distribution.png`: Nuclear maturity grading (MII, MI, others) and fertilization dynamics.

6. `embryo_grades_distribution.png`: Morphological embryo grade counts (Grades 1-4), viable counts, and surplus vitrification.

7. `temporal_outcome_trend.png`: Longitudinal positive outcome prevalence from 2019 to 2025.

8. `correlation_heatmap.png`: Spearman rank correlation matrix across treatment features and target.

9. `cohort_comparison_transfer_vs_nonreturn.png`: Baseline parameter comparisons between transferred and cancelled cycles.


## 6. Research Compliance & Non-Claim Notice

- **No ML models were trained** during this exploratory phase.
- **No clinical validity is claimed.**
- **Observed associations must not be interpreted as causal relationships.**
- **All 5,000 candidate observations remain intact without automated outlier filtering.**
