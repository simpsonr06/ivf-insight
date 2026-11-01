# IVF Insight: Exploratory Clinical Data Analysis, Predictive Modelling and Temporal Validation of IVF Treatment-Cycle Outcomes

**Author:** Senior Biomedical Data Scientist & Research Engineer  
**Institutional Affiliation:** Antigravity Biocomputing & Health Informatics Laboratory  
**Document Release:** Version 1.0 (Comprehensive Consolidated Research Report)  
**Publication Date:** November 1, 2026  
**Primary Dataset:** Mendeley Data, Version 1 (Maghdid, Rashid, & Askar, 2026), DOI: [10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1)  
**Licence:** Open Research Portfolio licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)  

---

## 1. Title Page & Administrative Disclosures

### Research Governance & Ethical Non-Claim Statement
> [!IMPORTANT]
> **Clinical Non-Deployment Notice & Research Boundary:**
> This comprehensive research report is an educational, methodological, and data science investigation. It does **not** constitute a clinical decision support tool, a software as a medical device (SaMD), or a basis for patient counseling, diagnostic inference, or altering fertility protocols.
> 
> In accordance with strict biomedical research integrity guidelines:
> 1. The target variable is formally and consistently designated as **`recorded_cycle_outcome`** because the primary dataset authors have not provided definitive clinical verification distinguishing biochemical pregnancy (transient serum $\beta$-HCG), ultrasound-confirmed gestational sac, ongoing clinical pregnancy, or live birth.
> 2. $\beta$-HCG is categorically excluded from all candidate predictor sets across all prediction scenarios to prevent post-outcome biological leakage.
> 3. The dataset contains no master patient identifiers; potential clustering of repeat treatment cycles across historical and prospective chronological partitions cannot be verified.
> 4. All findings reflect internal chronological validation of a single-center cohort and carry **no claim of external clinical generalizability**.
> 5. Statistical associations and regression odds ratios must **never** be interpreted as causal biological efficacy.

---

## 2. Abstract

**Background:** Assisted Reproductive Technology (ART) involves sequential clinical and embryological interventions where clinical decision-making relies on baseline demographics, ovarian stimulation dynamics, and laboratory embryology. Published machine learning models in reproductive medicine frequently suffer from post-outcome data leakage, random-split over-optimism, and reporting bias resulting from the conflation of cancelled cycles with true implantation failures.

**Objectives:** To establish an end-to-end reproducible data science and validation architecture for the authoritative open-access IVF dataset published by Maghdid et al. (2026); reconcile raw discrepancies; establish feature governance across three sequential clinical decision milestones; benchmark interpretable and nonlinear predictive models; quantify distribution drift across a chronological boundary (2024-01-01); and audit statistical anomalies (including the Female Age odds-ratio paradox and multicollinearity).

**Methods:** We analyzed 5,000 authoritative treatment cycles (2019–2025) after excluding two synthetic normalization boundary rows. Two analytical cohorts were established: the **Full-Cycle Cohort** ($N = 5,000$) and the **Embryo-Transfer Cohort** ($N = 3,750$, excluding 1,250 cycle cancellations). Three temporally separated feature scenarios were governed: Baseline (Scenario A, 4 features), Post-Retrieval (Scenario B, 8 features), and Pre-Transfer (Scenario C, 14 features). Validation was strictly enforced chronologically using a chronological holdout cutoff of January 1, 2024 ($N = 1,031$ holdout transfer cycles; $N = 1,458$ full cycles). Preprocessing pipelines (median imputation, standardization) were fitted exclusively on historical training data. Models included Majority Baseline, Logistic Regression, and Random Forest. Diagnostics incorporated 95% bootstrap confidence intervals, Harrell/Cox recalibration, Population Stability Index (PSI), Cook's distance, and restricted cubic splines.

**Results:** In the Full-Cycle Cohort, Pre-Transfer Random Forest demonstrated an apparent out-of-sample ROC-AUC of **0.903** (95% CI: [0.886, 0.918]). However, subcohort auditing revealed that this result is substantially influenced by the inclusion of 1,250 non-transfer cycles where zero embryos were transferred. When restricted to the Embryo-Transfer Cohort (evaluating pregnancy conditional on completed transfer), clinical discrimination was more moderate, reaching an ROC-AUC of **0.728** (95% CI: [0.689, 0.765]), PR-AUC of **0.892** (95% CI: [0.868, 0.915]), Balanced Accuracy of **67.3%**, and Brier score of **0.179**. Sequential milestone gains showed incremental discrimination over Baseline (+0.017 for Post-Retrieval; +0.054 for Pre-Transfer). Standardized multivariable odds ratios identified the dataset variable `frezzing` (integer count 0–25, $\text{OR} = 2.408$, $95\%$ CI: $[2.022, 2.868]$) and fertilization count ($\text{OR} = 1.583$) as primary positive markers, while Male Age was negative ($\text{OR} = 0.753$). A positive multivariable association with Female Age ($\text{OR} = 1.358$, $p < 0.0001$) emerged after adjusting for Male Age ($r = 0.526$), consistent with reciprocal suppression, conditioning on transfer survival, and potential unrecorded donor-oocyte utilization as plausible explanatory hypotheses rather than established biological mechanisms. Chronological holdout transfer prevalence shifted to **78.7%** (82.7% in 2024), resulting in systematic probability underconfidence (Calibration-in-the-Large via offset = **+0.937**).

**Conclusions:** Conflating cancelled cycles with transfer failures creates severe reporting bias in reproductive AI. Clinical predictions in IVF must adhere to strict temporal milestone partitioning and cohort separation. In transfer-conditioned cycles, embryological developmental competence and post-retrieval features yield moderate out-of-sample discrimination, but temporal prevalence shifts require formal recalibration before clinical interpretation across different time periods.

---

## 3. Keywords
Assisted Reproductive Technology (ART); In Vitro Fertilization (IVF); Clinical Prediction Models; Temporal Validation; Data Leakage; Conflation Illusion; Reciprocal Suppression; Calibration-in-the-Large; Algorithmic Governance.

---

## 4. Introduction

Assisted Reproductive Technology (ART) represents one of the most clinically complex, emotionally demanding, and financially intensive domains of contemporary medicine. Since the birth of the first IVF infant in 1978, millions of couples suffering from infertility have undergone controlled ovarian stimulation, ultrasound-guided transvaginal oocyte retrieval, laboratory gamete manipulation, and intrauterine embryo transfer. Despite substantial advances in recombinant gonadotropins, micromanipulation (intracytoplasmic sperm injection, ICSI), and vitrification techniques, treatment failure remains frequent, with overall live birth rates per started cycle rarely exceeding 30–35% in international population registries.

In recent years, machine learning and artificial intelligence algorithms have been enthusiastically proposed to predict IVF implantation, select blastocysts via computer vision, and individualize stimulation dosing. However, recent critical reviews in health informatics have highlighted alarming methodological vulnerabilities across published reproductive AI literature:
1. **Pervasive Post-Outcome Leakage:** Inclusion of post-treatment biomarkers—most egregiously serum $\beta$-HCG measured 14 days after embryo transfer—as predictive inputs.
2. **The Conflation of Cancelled Cycles with Implantation Failures:** Grouping treatment cycles that were cancelled prior to transfer (e.g. poor ovarian response, total fertilization failure, severe OHSS) together with completed transfers that resulted in negative pregnancy tests. This practice inflates apparent model accuracy by allowing algorithms to learn obvious laboratory cancellation markers (such as zero embryos available) rather than predicting biological endometrial-embryo cross-talk.
3. **Over-Optimistic Random-Split Validation:** Over-reliance on non-chronological random train/test splits that hide clinical distribution drift, temporal selection bias, and laboratory protocol modifications.
4. **Neglect of Calibration & Clinical Base Rates:** Highlighting high naive accuracy or area under the ROC curve (ROC-AUC) while completely omitting calibration assessment (reliability curves, calibration-in-the-large, and Brier scores).

To establish an uncompromised, transparent methodological benchmark, the **IVF Insight** research initiative was conducted across six systematic phases. This consolidated report presents the complete empirical findings, statistical audits, diagnostic evaluations, and methodological safeguards developed throughout the project.

---

## 5. Research Motivation and Objectives

The primary research objective of this study is:

> **To rigorously quantify the out-of-sample predictive capability of clinical, demographic, and embryological variables for classifying `recorded_cycle_outcome` across sequential clinical decision milestones, while enforcing strict chronological separation, zero post-outcome leakage, and formal cohort partitioning.**

### Specific Investigation Aims:
1. **Reconciliation & Audit:** Establish an authoritative, immutable data foundation from raw source files, audit normalization artifacts, reconcile missing values, and prevent contaminated datasets from entering the modeling pipeline (Phase 1).
2. **Feature Governance & Temporal Scenarios:** Define three strict, chronologically isolated prediction scenarios (Baseline, Post-Retrieval, Pre-Transfer), standardize the target endpoint as `recorded_cycle_outcome`, and exclude $\beta$-HCG and unverified pre-stimulation variables (Phase 2).
3. **Exploratory & Inferential Statistics:** Characterize distributions, quantify cycle cancellations, and calculate non-parametric univariate associations with False Discovery Rate (FDR) control across separate Full-Cycle and Embryo-Transfer cohorts (Phase 3).
4. **Predictive Modelling & Benchmark:** Train scikit-learn pipelines (Logistic Regression, Random Forest, Majority Baseline) fitted strictly on historical data (< 2024-01-01) and evaluate prospective performance (>= 2024-01-01) using 95% bootstrap confidence intervals (Phase 4).
5. **Robustness & Validation Audit:** Quantify temporal distribution drift, test cutoff sensitivity across multiple calendar boundaries (2023, 2024, 2024-H2), assess calibration (Harrell/Cox recalibration), evaluate feature stability via 100 bootstrap replicates, and analyze clinical threshold trade-offs (Phase 5).
6. **Statistical Integrity Audit:** Deconstruct counter-intuitive statistical anomalies (such as the positive Female Age regression coefficient), diagnose severe multicollinearity (VIFs), audit canonical Calibration-in-the-Large (CITL via offset), and clarify variable semantics (Phase 5.1).

---

## 6. Dataset Description and Provenance

This research is based exclusively on the authoritative release of the public dataset:

> **Maghdid, S., Rashid, T. A., & Askar, S. (2026).** *Comprehensive Dataset Profile of In Vitro Fertilization (IVF) Clinical and Embryological Data.* Mendeley Data, Version 1. DOI: [10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1).  
> **Licence:** Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).

The raw distribution contains two primary files in `data/raw/`:
1. `Dataset Clean.xlsx`: An Excel spreadsheet containing 5,002 rows and 21 columns.
2. `Normalized CSV.csv`: A comma-separated values file containing 5,000 rows and 21 columns.

The 21 original columns span clinical demographics, hormonal assays, sperm parameters, stimulation protocols, embryological yields, pregnancy tests, and the final classification outcome.

---

## 7. Dataset Reconciliation and Quality Assessment

A rigorous comparative audit between `Dataset Clean.xlsx` and `Normalized CSV.csv` was conducted in Phase 1 to establish provenance and audit data integrity.

### 7.1 Identification and Exclusion of Synthetic Normalization Boundaries
The raw Excel spreadsheet contains exactly 5,002 rows, whereas the CSV contains 5,000 rows. Row-level reconciliation revealed that the two extra rows in the Excel file—specifically row indices 5000 and 5001—are **synthetic boundary rows** manually appended to define minimum and maximum values for Min-Max normalization:
- **Row 5000 (Synthetic Min Boundary):** Encodes the absolute minimum possible or observed value across all numeric variables (e.g., `Female Age` = 18, `AMH` = 0.0, `Number of attempts` = 1).
- **Row 5001 (Synthetic Max Boundary):** Encodes the maximum observed or theoretical scale bound across all numeric variables (e.g., `Female Age` = 55, `AMH` = 482.1, `Number of attempts` = 6).

In `Normalized CSV.csv`, these two boundary rows were converted into vectors of exact zeros (`0.000000`) and exact ones (`1.000000`) across all normalized columns. Incorporating these synthetic extremes into statistical analysis or training folds would introduce severe synthetic leverage. Consequently, rows 5000 and 5001 were permanently excluded, leaving exactly **5,000 genuine patient treatment cycles** (row indices 0 to 4999).

### 7.2 Resolution of Missing Values and String Corruptions
The reconciliation module identified four missing values and one typographical artifact in the raw Excel data:
1. **Row 346 (`Number of attempts`):** Contained a corrupted string value with a leading backtick (`` `1 ``), causing the column to be parsed as mixed object dtype. Sanitization extracted the integer `1`.
2. **Row 3283 (`Sperm count`, `Sperm motility`, `Sperm morphology`):** Contained true missing null values (`NaN`).
3. **Normalized CSV Leakage/Imputation Notice:** In `Normalized CSV.csv`, these nulls were silently replaced with arbitrary zeros (`0.000000`) without clinical justification or documentation. Due to uncontrolled preprocessing and synthetic normalization boundaries, `Normalized CSV.csv` was permanently disqualified from predictive modeling. All subsequent phases use `Dataset Clean.xlsx` (rows 0–4999).

```
Table 1: Authoritative Dataset Reconciliation and Quality Findings
----------------------------------------------------------------------------------------------------
Metric / Dimension                 Raw Excel (Dataset Clean.xlsx)    Normalized CSV (Disqualified)
----------------------------------------------------------------------------------------------------
Raw Row Count                      5,002 rows                        5,000 rows
Clean Patient Cycles Retained      5,000 rows (indices 0–4999)       0 (Excluded from modeling)
Synthetic Boundary Rows Excluded   2 rows (indices 5000 & 5001)      2 rows embedded as 0.0 / 1.0
Internal Missing Nulls             4 nulls (attempts, sperm tests)   0 (Silently zero-filled)
String Formatting Artifacts        1 (Row 346 backtick '`1')         0
Primary Modeling Role              Authoritative Ground Truth        Permanently Disqualified
----------------------------------------------------------------------------------------------------
```

---

## 8. Research Design and Feature Governance

### 8.1 The Target Endpoint: `recorded_cycle_outcome`
The primary outcome column in the raw dataset is titled:  
`Output(failed implantation or successful implantation)`.  
In the clean dataset ($N = 5,000$), the binary distribution is almost perfectly balanced:
- **Class 0:** 2,508 cycles (50.16%)
- **Class 1:** 2,492 cycles (49.84%)

A cross-tabulation audit against serum `B-HCG (mIU/mL)` unmasked critical clinical heterogeneity within Class 0:
1. **Cycles Without Embryo Transfer ($N = 1,250$):** Exactly 1,250 cycles contain the explicit clinical note `Non-return of embryos`. In all 1,250 cases, the outcome is recorded as `0.0`. These represent cycle cancellations (e.g. failed fertilization, developmental arrest, severe OHSS freeze-all, or patient refusal).
2. **Negative Pregnancy Tests ($N = 1,250$):** Exactly 1,250 cycles had embryos transferred, completed the two-week luteal phase, and recorded a negative pregnancy test (`NEGATIVE`, unquantified or titer $< 5$ mIU/mL).
3. **Discordant Positive Tests with Class 0 ($N = 8$):** Exactly 8 cycles recorded a clinically positive $\beta$-HCG titer (range: 35.0 to 2,100.0 mIU/mL; mean: 614.50 mIU/mL; median: 533.00 mIU/mL; individual values: 35.0, 55.0, 324.0, 516.0, 550.0, 612.0, 724.0, and 2,100.0 mIU/mL across Rows 876, 878, 1298, 1846, 1923, 3939, 4040, and 4849) but were nonetheless labeled as `Output = 0.0`. While clinically compatible with early non-progressing biochemical pregnancies prior to ultrasound confirmation, or potential reporting threshold discordance, the underlying clinical etiology cannot be resolved from the source records without inferring unrecorded diagnoses.

Because the dataset authors provided no documentation confirming whether Class 1 represents biochemical implantation, gestational sac presence, fetal heartbeat, or live birth, our research governance protocol strictly mandates:
- The endpoint is referred to exclusively as **`recorded_cycle_outcome`**.
- It is **never** referred to as confirmed implantation, clinical pregnancy, or live birth.

### 8.2 Cohort Partitioning: Full-Cycle vs Embryo-Transfer
To prevent misleading clinical conclusions, two analytical cohorts were established:
- **Cohort A (Full-Cycle Cohort, $N = 5,000$):** Encompasses all candidate cycles. Reflects the macro-level prognosis of an initiated treatment cycle from ovarian stimulation onward.
- **Cohort B (Embryo-Transfer Cohort, $N = 3,750$):** Excludes the 1,250 non-return cancellations. Restricts analysis strictly to cycles where intrauterine embryo transfer was successfully performed.

### 8.3 Three Temporal Prediction Scenarios
Features were mapped to clinical process milestones, strictly barring $\beta$-HCG from all candidate sets:
1. **Scenario A (Baseline Prediction — 4 confirmed features):** Demographics and ovarian reserve available prior to stimulation: `Female Age`, `Male Age`, `AMH`, `Number of attempts`. (Conditional baseline features like semen analysis and stimulation drugs were held out per research design protocol).
2. **Scenario B (Post-Retrieval Prediction — 8 features):** Baseline features plus Day 0 laboratory embryology: `Oocyte Maturity MII`, `Oocyte Maturity MI`, `Oocyte Maturity others`, `Number of fertilized eggs`.
3. **Scenario C (Pre-Transfer Prediction — 14 features):** Post-retrieval features plus Day 3/5 cleavage and embryo cohort metrics: `Embryo Grade 1`, `Embryo Grade 2`, `Embryo Grade 3`, `Embryo Grade 4`, `Number of embryos`, `frezzing`.

```
Table 2: Clinical Process Stages and Feature Governance Registry
----------------------------------------------------------------------------------------------------
Clinical Feature Name      Process Stage / Timing     Scenario A    Scenario B    Scenario C    Governance Decision
----------------------------------------------------------------------------------------------------
Female Age                 Baseline Demographic      Included      Included      Included      Confirmed Baseline
Male Age                   Baseline Demographic      Included      Included      Included      Confirmed Baseline
AMH                        Baseline Ovarian Reserve  Included      Included      Included      Confirmed Baseline
Number of attempts         Baseline Clinical History Included      Included      Included      Confirmed Baseline
Medicines and treatments   Stimulation Protocol      Excluded      Excluded      Excluded      Conditional (Unverified Timing)
Sperm count                Baseline Andrology        Excluded      Excluded      Excluded      Conditional (Unverified Timing)
Sperm motility             Baseline Andrology        Excluded      Excluded      Excluded      Conditional (Unverified Timing)
Sperm morphology           Baseline Andrology        Excluded      Excluded      Excluded      Conditional (Unverified Timing)
Oocyte Maturity MII        Post-Retrieval (Day 0)    Excluded      Included      Included      Nuclear Maturity Count
Oocyte Maturity MI         Post-Retrieval (Day 0)    Excluded      Included      Included      Intermediate Maturity Count
Oocyte Maturity others     Post-Retrieval (Day 0)    Excluded      Included      Included      Degenerated/GV Count
Number of fertilized eggs  Post-Fertilization (D1)   Excluded      Included      Included      Normally Fertilized (2PN)
Embryo Grade 1             Pre-Transfer Embryology   Excluded      Excluded      Included      Top Quality Embryo Count
Embryo Grade 2             Pre-Transfer Embryology   Excluded      Excluded      Included      Good Quality Embryo Count
Embryo Grade 3             Pre-Transfer Embryology   Excluded      Excluded      Included      Fair Quality Embryo Count
Embryo Grade 4             Pre-Transfer Embryology   Excluded      Excluded      Included      Poor Quality Embryo Count
Number of embryos          Transfer Procedure        Excluded      Excluded      Included      Embryos Transferred Count
frezzing                   Laboratory Embryo Metric  Excluded      Excluded      Included      Dataset Variable frezzing (Count 0-25)
B-HCG (mIU/mL)             Post-Outcome (Day 14)     BARRED        BARRED        BARRED        Post-Outcome Leakage
----------------------------------------------------------------------------------------------------
```

---

## 9. Exploratory Data Analysis & Statistical Investigation

Descriptive statistics and univariate associations were computed separately for the Full-Cycle Cohort ($N=5,000$) and the Embryo-Transfer Cohort ($N=3,750$).

### 9.1 Baseline Characteristics & Distributions
- **Female Age:** Full cohort mean $34.13 \pm 5.17$ years (median: 34.0, range: 18–49). Transfer cohort mean $34.15 \pm 5.13$ years.
- **Male Age:** Full cohort mean $35.86 \pm 6.36$ years (median: 35.0, range: 19–57). Transfer cohort mean $35.85 \pm 6.27$ years.
- **Anti-Müllerian Hormone (AMH):** Highly right-skewed. Full cohort median **$1.59$** (IQR: 2.36; mean: $2.54 \pm 12.02$; range: 0.013–482.1; unit not specified in source dataset). Transfer cohort median is **$1.83$** (IQR: 2.46; mean: $2.82 \pm 13.80$). In Phase 3, **three extreme outlier observations with $\text{AMH} = 482.1$** were detected (all other observations $\le 36.3$). These three records were preserved for primary evaluation and evaluated in Phase 5 sensitivity analyses.
- **Transferred Embryos (`Number of embryos`):** In the Full-Cycle Cohort, median is 2.0 (mean: $1.89 \pm 1.22$; 1,250 cycles with 0 embryos). In the Embryo-Transfer Cohort, median is 2.0 (mean: $2.52 \pm 0.77$, range: 1–8).
- **Dataset Variable `frezzing`:** Highly skewed integer count variable (values 0–25; median: 0.0, mean: $1.55 \pm 2.65$). Exactly 3,332 cycles (66.6%) had a value of zero. While unverified whether this denotes Day 3 or Day 5 cryopreservation, it was the strongest multivariable predictor in the exploratory model.

```
Table 3: Cohort Descriptive Statistics and Baseline Distribution Metrics
----------------------------------------------------------------------------------------------------
Feature Variable           Cohort Partition        N      Mean     Std      Median   IQR      Min   Max
----------------------------------------------------------------------------------------------------
Female Age (years)         Full-Cycle Cohort       5,000  34.13    5.17     34.0     7.0      18    49
                           Embryo-Transfer Cohort  3,750  34.15    5.13     34.0     7.0      18    49
Male Age (years)           Full-Cycle Cohort       5,000  35.86    6.36     35.0     8.0      19    57
                           Embryo-Transfer Cohort  3,750  35.85    6.27     35.0     8.0      19    57
AMH (unit unrecorded)      Full-Cycle Cohort       5,000   2.54   12.02      1.59    2.36     0.01  482.1
                           Embryo-Transfer Cohort  3,750   2.82   13.80      1.83    2.46     0.01  482.1
Number of attempts         Full-Cycle Cohort       5,000   1.21    0.54      1.0     0.0      1     6
                           Embryo-Transfer Cohort  3,750   1.21    0.55      1.0     0.0      1     6
Oocyte Maturity MII        Full-Cycle Cohort       5,000   7.74    5.20      7.0     7.0      0     33
                           Embryo-Transfer Cohort  3,750   8.06    5.24      7.0     7.0      0     33
Number of fertilized eggs  Full-Cycle Cohort       5,000   6.47    4.46      5.0     6.0      0     35
                           Embryo-Transfer Cohort  3,750   6.83    4.46      6.0     6.0      0     35
Embryo Grade 1             Full-Cycle Cohort       5,000   3.54    3.49      2.0     4.0      0     32
                           Embryo-Transfer Cohort  3,750   3.73    3.52      3.0     4.0      0     32
Number of embryos          Full-Cycle Cohort       5,000   1.89    1.22      2.0     1.0      0     8
                           Embryo-Transfer Cohort  3,750   2.52    0.77      2.0     1.0      1     8
frezzing (frozen count)    Full-Cycle Cohort       5,000   1.46    2.56      0.0     2.0      0     25
                           Embryo-Transfer Cohort  3,750   1.55    2.65      0.0     2.0      0     25
----------------------------------------------------------------------------------------------------
```

### 9.2 Univariate Statistical Associations
Exploratory non-parametric hypothesis tests (Mann-Whitney U for numeric features, Chi-Square for categorical features) were adjusted using the Benjamini-Hochberg False Discovery Rate (FDR) procedure ($q < 0.05$):
- In the **Full-Cycle Cohort**, `Number of embryos` exhibited the strongest univariate association ($r_{rb} = 0.589, q = 3.25 \times 10^{-255}$), directly driven by the deterministic failure of non-transfer cycles.
- In the **Embryo-Transfer Cohort**, `frezzing` exhibited the strongest association ($r_{rb} = 0.324, q = 1.34 \times 10^{-48}$), followed by `Number of fertilized eggs` ($r_{rb} = 0.222, q = 2.45 \times 10^{-23}$) and `Number of embryos` ($r_{rb} = 0.208, q = 8.12 \times 10^{-21}$).

---

## 10. Predictive Modelling Methodology

### 10.1 Chronological Split Architecture
To prevent temporal data leakage, evaluation was conducted using a strict chronological holdout split:
- **Historical Training Partition:** Egg retrieval date strictly before **January 1, 2024**.
  - Full-Cycle Cohort: $N = 3,542$ cycles (positive prevalence: 47.74%).
  - Embryo-Transfer Cohort: $N = 2,719$ cycles (positive prevalence: 61.82%).
- **Chronological Holdout Partition:** Egg retrieval date on or after **January 1, 2024**.
  - Full-Cycle Cohort: $N = 1,458$ cycles (positive prevalence: 55.62%).
  - Embryo-Transfer Cohort: $N = 1,031$ cycles (positive prevalence: 78.66%).

### 10.2 Leakage-Proof Scikit-Learn Pipelines
All preprocessing was encapsulated inside `sklearn.pipeline.Pipeline`:
- Imputation: `SimpleImputer(strategy='median')` fitted strictly on historical training folds.
- Scaling: `StandardScaler()` fitted strictly on historical training folds.
- Estimators:
  - **Majority-Class Baseline:** `DummyClassifier(strategy='most_frequent')`.
  - **Interpretable Linear Model:** `LogisticRegression(max_iter=1000, random_state=42)`.
  - **Nonlinear Model:** `RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=4, random_state=42)`.

---

## 11. Model Performance, Comparison, and "The Conflation Illusion"

A complete factorial matrix of 18 experiments (2 cohorts $\times$ 3 scenarios $\times$ 3 models) was evaluated on untouched chronological holdout sets. 95% confidence intervals were generated using 500 non-parametric bootstrap iterations.

```
Table 4: Chronological Holdout Model Comparison Matrix (18 Experiments)
---------------------------------------------------------------------------------------------------------------------------------
Cohort Partition        Scenario              Model Architecture    ROC-AUC (95% CI)       PR-AUC (95% CI)        BalAcc  Acc     Brier
---------------------------------------------------------------------------------------------------------------------------------
Full-Cycle Cohort       Scenario A (Baseline) Majority Baseline     0.500 [0.500, 0.500]   0.556 [0.531, 0.583]   0.500   0.444   0.556
                        Scenario A (Baseline) Logistic Regression   0.650 [0.622, 0.677]   0.693 [0.655, 0.728]   0.603   0.596   0.234
                        Scenario A (Baseline) Random Forest         0.732 [0.704, 0.756]   0.753 [0.716, 0.784]   0.659   0.651   0.215
                        Scenario B (Retrieval)Majority Baseline     0.500 [0.500, 0.500]   0.556 [0.531, 0.583]   0.500   0.444   0.556
                        Scenario B (Retrieval)Logistic Regression   0.766 [0.740, 0.785]   0.783 [0.750, 0.810]   0.677   0.664   0.208
                        Scenario B (Retrieval)Random Forest         0.794 [0.770, 0.813]   0.798 [0.765, 0.827]   0.706   0.704   0.188
                        Scenario C (Transfer) Majority Baseline     0.500 [0.500, 0.500]   0.556 [0.531, 0.583]   0.500   0.444   0.556
                        Scenario C (Transfer) Logistic Regression   0.887 [0.869, 0.901]   0.897 [0.875, 0.916]   0.769   0.755   0.158
                        Scenario C (Transfer) Random Forest         0.903 [0.886, 0.918]   0.905 [0.883, 0.921]   0.797   0.790   0.138
---------------------------------------------------------------------------------------------------------------------------------
Embryo-Transfer Cohort  Scenario A (Baseline) Majority Baseline     0.500 [0.500, 0.500]   0.787 [0.762, 0.811]   0.500   0.787   0.213
                        Scenario A (Baseline) Logistic Regression   0.614 [0.573, 0.653]   0.851 [0.824, 0.880]   0.545   0.750   0.186
                        Scenario A (Baseline) Random Forest         0.674 [0.633, 0.714]   0.875 [0.849, 0.900]   0.529   0.793   0.172
                        Scenario B (Retrieval)Majority Baseline     0.500 [0.500, 0.500]   0.787 [0.762, 0.811]   0.500   0.787   0.213
                        Scenario B (Retrieval)Logistic Regression   0.666 [0.625, 0.698]   0.876 [0.849, 0.898]   0.589   0.718   0.185
                        Scenario B (Retrieval)Random Forest         0.691 [0.651, 0.725]   0.885 [0.860, 0.907]   0.594   0.758   0.176
                        Scenario C (Transfer) Majority Baseline     0.500 [0.500, 0.500]   0.787 [0.762, 0.811]   0.500   0.787   0.213
                        Scenario C (Transfer) Logistic Regression   0.705 [0.668, 0.740]   0.899 [0.876, 0.919]   0.604   0.700   0.181
                        Scenario C (Transfer) Random Forest         0.728 [0.689, 0.765]   0.892 [0.868, 0.915]   0.673   0.738   0.179
---------------------------------------------------------------------------------------------------------------------------------
```

### 11.1 Deconstruction of "The Conflation Illusion"
The most critical methodological finding of Phase 4 is the **dramatic divergence in performance between the Full-Cycle and Embryo-Transfer cohorts**:
- In the Full-Cycle Cohort, Scenario C Random Forest achieves an apparent **ROC-AUC of 0.903** (PR-AUC = 0.905, Balanced Accuracy = 79.7%).
- In the Embryo-Transfer Cohort, the exact same model reaches a realistic **ROC-AUC of 0.728** (PR-AUC = 0.892, Balanced Accuracy = 67.3%).

This 0.175 AUC gap illustrates that the 0.903 full-cycle ROC-AUC is substantially influenced by the inclusion of 1,250 non-transfer cycles (cancellations and zero-embryo outcomes where `Number of embryos == 0` and `Output == 0`). When evaluated strictly on cycles with completed embryo transfer, discrimination is more moderate (ROC-AUC 0.728). Presenting full-cycle discrimination without cohort separation conflates cycle cancellations with transfer-specific implantation failure.

### 11.2 Milestone Prognostic Gains (Transfer Cohort)
Evaluating genuine implantation prediction conditional on embryo transfer:
1. **Baseline (Scenario A, ROC-AUC = 0.674):** Demographics and ovarian reserve provide modest prognostic signal.
2. **Post-Retrieval (Scenario B, ROC-AUC = 0.691):** Day 0 maturity yield and fertilization count add +0.017 AUC.
3. **Pre-Transfer (Scenario C, ROC-AUC = 0.728):** Cleavage morphology and cryopreservation yield the most substantial gain (+0.037 over Scenario B; +0.054 over Baseline), elevating Balanced Accuracy to 67.3%.

---

## 12. Temporal Validation and Distribution Drift

In Phase 5, temporal dynamics were scrutinized across all seven calendar years (2019 to 2025).

### 12.1 Annual Outcome Prevalence Shift
- **Historical Development Period (2019–2023):** Overall positive prevalence in the transfer cohort was **61.8%** ($1,681 / 2,719$). In 2020 (COVID-19 onset), annual cycle volume dropped precipitously to 250 cycles and prevalence dipped to 42.8%, recovering to 56.3% in 2023.
- **Chronological Holdout Period (2024?2025):** Overall positive prevalence surged to **78.7%** ($811 / 1,031$), peaking at **82.7%** in 2024 ($578 / 699$).
- **Cycle Cancellations:** The proportion of cycles with `Non-return of embryos` also fluctuated dramatically, from 16.1% in 2020 to **34.4% in 2025**.

```
Table 5: Annual Outcome Prevalence and Cycle Cancellation Trajectories
----------------------------------------------------------------------------------------------------
Year    Full Cycles Total    Non-Return Cancellations    Non-Return Rate    Transfer Cycles    Transfer Prevalence
----------------------------------------------------------------------------------------------------
2019    1,730                464                         26.8%              1,266              72.0%
2020      298                 48                         16.1%                250              42.8%
2021      411                 86                         20.9%                325              50.5%
2022      382                 88                         23.0%                294              57.8%
2023      721                137                         19.0%                584              56.3%
2024      952                253                         26.6%                699              82.7%
2025      506                174                         34.4%                332              70.2%
----------------------------------------------------------------------------------------------------
```

### 12.2 Quantifying Feature Distribution Shifts
Comparing historical (< 2024) with prospective (>= 2024) transfer partitions:
- `Male Age`: Decreased from $36.29$ to $34.68$ years (SMD = $-0.26$, KS $p = 1.27 \times 10^{-5}$, PSI = 0.081).
- `Number of embryos`: Decreased from $2.59$ to $2.34$ (SMD = $-0.21$, KS $p = 1.56 \times 10^{-8}$, PSI = 0.076).
- `Embryo Grade 1`: Decreased from $3.93$ to $3.20$ (SMD = $-0.19$, KS $p = 1.09 \times 10^{-6}$, PSI = 0.052).
- `Oocyte Maturity MI`: Increased from $1.65$ to $2.06$ (SMD = $+0.22$, KS $p = 7.35 \times 10^{-11}$, PSI = 0.098).

---

## 13. Robustness and Sensitivity Analysis

### 13.1 Cutoff Sensitivity Across Multiple Chronological Boundaries
To confirm that model discrimination was not an idiosyncratic artifact of the January 1, 2024 split date, chronological validation was repeated across multiple boundaries:
- **Cutoff 2023-01-01:** Historical Train $N = 2,135$ (63.3% pos) $
ightarrow$ Holdout $N = 1,615$ (70.6% pos):  
  Scenario C Random Forest out-of-sample **ROC-AUC = 0.7503** (95% CI: [0.725, 0.774]), Balanced Accuracy = 65.0%.
- **Cutoff 2024-01-01:** Historical Train $N = 2,719$ (61.8% pos) $
ightarrow$ Holdout $N = 1,031$ (78.7% pos):  
  Scenario C Random Forest out-of-sample **ROC-AUC = 0.7275** (95% CI: [0.689, 0.765]), Balanced Accuracy = 67.3%.
- **Cutoff 2024-07-01:** Historical Train $N = 3,028$ (63.8% pos) $
ightarrow$ Holdout $N = 722$ (77.7% pos):  
  Scenario C Random Forest out-of-sample **ROC-AUC = 0.7088** (95% CI: [0.665, 0.751]), Balanced Accuracy = 64.5%.

Random Forest consistently maintained out-of-sample discrimination between 0.709 and 0.750, confirming architectural stability.

### 13.2 Sensitivity to Extreme AMH Outliers ($482.1$, Unit Not Specified)
Excluding the three records with $\text{AMH} = 482.1$ (2 in train, 1 in holdout) resulted in negligible change to holdout ROC-AUC ($0.7275 \rightarrow 0.7262$, $\Delta = -0.0013$), proving that median imputation and tree partitioning are robust to extreme values.

### 13.3 Leave-One-Feature-Out (LOFO) Ablation
- Removing `Number of embryos` transferred caused the largest single collapse in ROC-AUC ($0.7275 \rightarrow 0.6946$, $\Delta = -0.0329$).
- Removing `frezzing` reduced Balanced Accuracy from 67.3% to 64.1%.
- Removing `Female Age` or `Male Age` caused modest drops in AUC to 0.7200 and 0.7228.

### 13.4 Feature Importance Stability (100 Bootstrap Resamples)
Evaluating Random Forest Gini importance stability across 100 bootstrap replicates of historical training data:
- `frezzing` captured **Rank #1 across 100% of replicates** (Mean Gini: $0.341 \pm 0.023$, 95% CI: [0.297, 0.386]).
- `Number of fertilized eggs` reliably occupied Rank #2 (Mean Gini: $0.101 \pm 0.014$).
- `Number of embryos` occupied Rank #3 (Mean Gini: $0.100 \pm 0.015$).

---

## 14. Statistical Integrity & Interpretation Audit

Phase 5.1 resolved critical statistical anomalies, multicollinearity, calibration formulations, and causal misinterpretations.

### 14.1 Deconstruction of the Female Age Odds-Ratio Paradox
In multivariable Logistic Regression, Female Age displayed a positive standardized coefficient ($\beta = +0.3062$, $\text{OR} = 1.358$, $p < 0.0001$). This contradicts general biological reality and was thoroughly investigated:

```
Table 6: Progression of Female Age Association Across Model Specifications
----------------------------------------------------------------------------------------------------
Model Specification                            Female Age Beta (Std)    SE       p-value     Standardized OR (95% CI)
----------------------------------------------------------------------------------------------------
Transfer Cohort — Unadjusted Female Age        +0.0268                  0.0080   0.0008      1.148 [1.059, 1.244]
Transfer Cohort — Unadjusted Male Age          [Male Beta: -0.0297]     0.0065   < 0.0001    [Male OR: 0.830]
Transfer Cohort — Female Age + Male Age        +0.0667                  0.0103   < 0.0001    1.408 [1.272, 1.558]
Transfer Cohort — Scenario A (Baseline)        +0.0667                  0.0103   < 0.0001    1.409 [1.273, 1.559]
Transfer Cohort — Scenario B (Post-Retrieval)  +0.0578                  0.0106   < 0.0001    1.347 [1.215, 1.494]
Transfer Cohort — Scenario C (Pre-Transfer)    +0.0614                  0.0108   < 0.0001    1.358 [1.222, 1.509]
Full-Cycle Cohort — Unadjusted Female Age      +0.0120                  0.0068   0.0778      1.064 [0.993, 1.140]
Full-Cycle Cohort — Scenario C (Pre-Transfer)  +0.0428                  0.0094   < 0.0001    1.246 [1.144, 1.357]
----------------------------------------------------------------------------------------------------
```

### Explanatory Mechanisms:
1. **Reciprocal Statistical Suppression:** Female Age and Male Age are positively correlated ($r = 0.526$). In univariable models, Male Age is negative ($\beta = -0.030$), while Female Age is mildly positive ($\beta = +0.027$). When modeled together, the adjustment for male partner age shifts the female age coefficient to positive statistical significance ($\beta = +0.067$ and $\beta = -0.058$). This is consistent with reciprocal statistical suppression, where correlated predictors mutually clarify non-shared variance, though it represents a statistical phenomenon rather than an established biological mechanism.
2. **Empirical Age-Bracket Conditioning:** In this transfer cohort, observed positive prevalence increased across age groups: $56.3\%$ (ages 18–29), $61.4\%$ (ages 30–34), $62.9\%$ (ages 35–38), $65.2\%$ (ages 39–42), and **$71.2\%$ (ages 43–55)**. Conditioning on completed embryo transfer may introduce substantial selection bias, while the underlying biological or clinical mechanisms cannot be established from this dataset.
3. **Potential Unrecorded Oocyte Donation:** In clinical practice, patients aged $>42$ using donor oocytes achieve success rates substantially higher than autologous cycles. Because the dataset authors **did not record oocyte origin (autologous vs. donor)**, unrecorded donor-oocyte utilization remains a plausible alternative explanatory hypothesis for the observed trend in older transfer patients, rather than an established clinical fact.
4. **Spline Non-Linearity Test:** Restricted cubic splines with 4 knots showed no significant non-linearity over a linear logit model ($\text{LR stat} = 0.6767, \text{df} = 3, p = 0.8787$).
5. **Non-Causal Mandate:** The positive multivariable association is best understood through potential statistical suppression, transfer conditioning, and unrecorded donor-oocyte utilization as plausible explanatory hypotheses. It must **never** be cited as clinical evidence that advanced maternal age improves IVF outcomes.

### 14.2 Multicollinearity Diagnostics (VIF)
- `Number of fertilized eggs` exhibits severe multicollinearity with a **VIF of 11.14** (due to biological alignment with `Oocyte Maturity MII`, VIF = 5.97, and `Embryo Grade 1`, VIF = 5.38).
- `Female Age` ($\text{VIF} = 1.44$) and `Male Age` ($\text{VIF} = 1.51$) exhibit low VIFs, proving that their opposite signs are driven by **correlation suppression**, not variance inflation.
- Condition number of scaled predictors is **8.01** (well within the safe range $< 30$). Maximum Cook's distance is **0.3614**, with only 1 observation exceeding Cook's $D > 0.05$.

```
Table 7: Multicollinearity Diagnostics and Regression Diagnostics (Scenario C)
----------------------------------------------------------------------------------------------------
Feature Variable           Standardized Beta (Wald)  Wald SE   Wald p-value  Std OR (95% CI)       VIF    Collinearity Flag
----------------------------------------------------------------------------------------------------
Female Age                 +0.3062                   0.0538    < 0.0001      1.358 [1.222, 1.509]   1.44  Low Collinearity
Male Age                   -0.2834                   0.0560    < 0.0001      0.753 [0.675, 0.840]   1.51  Low Collinearity
AMH                        +0.1305                   0.1947    0.5031        1.139 [0.778, 1.668]   1.02  Low Collinearity
Number of attempts         -0.0121                   0.0431    0.7794        0.988 [0.908, 1.075]   1.02  Low Collinearity
Oocyte Maturity MII        -0.1719                   0.1086    0.1134        0.842 [0.680, 1.042]   5.97  Moderate Collinearity
Oocyte Maturity MI         +0.1176                   0.0513    0.0220        1.125 [1.017, 1.244]   1.15  Low Collinearity
Oocyte Maturity others     -0.0135                   0.0509    0.7912        0.987 [0.893, 1.090]   1.15  Low Collinearity
Number of fertilized eggs  +0.4592                   0.1592    0.0039        1.583 [1.158, 2.162]  11.14  Severe Collinearity
Embryo Grade 1             -0.1855                   0.1143    0.1045        0.831 [0.664, 1.039]   5.38  Moderate Collinearity
Embryo Grade 2             -0.1076                   0.0717    0.1336        0.898 [0.780, 1.033]   2.24  Low Collinearity
Embryo Grade 3             -0.2349                   0.0515    < 0.0001      0.791 [0.715, 0.875]   1.34  Low Collinearity
Embryo Grade 4             +0.0412                   0.0528    0.4351        1.042 [0.939, 1.156]   1.11  Low Collinearity
Number of embryos          +0.2343                   0.0464    < 0.0001      1.264 [1.154, 1.384]   1.18  Low Collinearity
frezzing                   +0.8789                   0.0892    < 0.0001      2.408 [2.022, 2.868]   2.16  Low Collinearity
----------------------------------------------------------------------------------------------------
```

### 14.3 Canonical Calibration-in-the-Large (CITL) Audit
Calibration was audited to distinguish canonical CITL from unconstrained recalibration intercepts:
1. **Canonical CITL (via Offset):** Fitting $\text{logit}(P(Y=1)) = \alpha + \text{offset}(\text{logit}(p))$ yields **$\text{CITL} = +0.9371$** ($95\%$ CI: $[0.777, 1.098]$) for Scenario C Random Forest.
   Because $\text{CITL} > 0$ and the Expected-to-Observed ratio ($E/O$) is **$0.7971$** (mean predicted probability = $62.7\%$ vs observed prevalence = $78.7\%$), uncalibrated model probabilities systematically underestimate success in the chronological holdout period by $\approx 20\%$.
2. **Calibration Slope:** In the unconstrained recalibration model, slope is **$\beta = 0.8664$** ($95\%$ CI: $[0.692, 1.040]$). The 95% CI encompasses $1.0$, confirming acceptable refinement spread without statistically significant over-dispersion.
3. **Intercept Distinction:** The unconstrained intercept ($\alpha = +0.9589$) measures calibration at $\text{logit}(p) = 0$ ($p = 0.5$) and must not be confused with canonical CITL ($+0.9371$). Both reflect baseline probability underconfidence due to the temporal prevalence shift across chronological partitions.

### 14.4 Feature Definition Semantics
- **Dataset Variable `frezzing`:** It contains integer count values from 0 to 25 (median: 0), **not** a binary indicator. Although its exact clinical cryopreservation protocol remains unverified in the source records, it served as the strongest multivariable predictive feature in the exploratory model.
- **Embryo Grades are Counts:** `Embryo Grade 1` through `Grade 4` are counts of embryos belonging to each grade, not categorical variables.
- **Explainability Separation:** Standardized Odds Ratios ($\text{OR} = e^\beta$) apply strictly to Logistic Regression; Random Forest feature importances reflect Gini impurity reductions and cannot be expressed as odds ratios.

---

## 15. Decision Threshold Analysis & Clinical Risk-Utility Governance

Evaluating decision thresholds on the chronological holdout transfer set ($N = 1,031$; prevalence = $78.7\%$):

```
Table 8: Decision Threshold Trade-Offs and Predictive Values (Transfer Cohort Holdout)
----------------------------------------------------------------------------------------------------
Threshold    True Pos    False Pos    True Neg    False Neg    Sensitivity    Specificity    PPV      NPV      BalAcc
----------------------------------------------------------------------------------------------------
0.100        811         220            0           0          100.0%           0.0%         78.7%     0.0%    50.0%
0.300        766         168           52          45           94.5%          23.6%         82.0%    53.6%    59.0%
0.400        741         142           78          70           91.4%          35.5%         83.9%    52.7%    63.4%
0.500        638          97          123         173           78.7%          55.9%         86.8%    41.6%    67.3%
0.600        481          62          158         330           59.3%          71.8%         88.6%    32.4%    65.6%
0.700        371          48          172         440           45.7%          78.2%         88.5%    28.1%    62.0%
0.787 (Prev) 329          38          182         482           40.6%          82.7%         89.6%    27.4%    61.6%
0.900         32           2          218         779            3.9%          99.1%         94.1%    21.9%    51.5%
----------------------------------------------------------------------------------------------------
```

### Methodological Principles:
1. **Bayes' Theorem Base-Rate Dynamics:** In a high-prevalence setting ($78.7\%$), Positive Predictive Value (PPV) is naturally elevated to $86.8\%$ at threshold $0.5$, while Negative Predictive Value (NPV) is depressed to $41.6\%$.
2. **Empirical Prevalence is Not a Valid Clinical Cutoff:** Shifting the cutoff to the empirical prevalence ($0.787$) raises specificity to $82.7\%$ and PPV to $89.6\%$, but drops sensitivity to $40.6\%$, misclassifying $59.4\%$ of successful transfers.
3. **Clinical Non-Recommendation:** No classification threshold is recommended for clinical management or patient counseling. In reproductive medicine, denying a couple an embryo transfer based on an arbitrary probabilistic cutoff carries severe emotional and ethical consequences. Setting a cutoff requires explicit clinical loss matrices.

---

## 16. Discussion

The findings of this comprehensive research initiative provide critical insights into clinical prediction modeling for assisted reproduction:

### 16.1 The Fallacy of Conflating Cancelled Cycles
Published machine learning studies in IVF frequently claim extraordinary prediction accuracy ($\text{AUC} > 0.90$) using complete cycle records. Our Phase 4 evaluation proves that this is a reporting illusion. When cycles cancelled prior to transfer are pooled with transfer cycles, the model simply learns that having zero embryos transferred guarantees non-pregnancy. When evaluated on the true clinical challenge—predicting pregnancy conditional on embryo transfer—the genuine discriminatory ceiling of these features drops to **0.728 ROC-AUC**. Separating these cohorts is essential for scientific honesty.

### 16.2 Incremental Value of Clinical Milestones
Prognostic discrimination improves sequentially as treatment progresses from baseline ovarian reserve ($\text{AUC} = 0.674$) to oocyte retrieval ($\text{AUC} = 0.691$) and pre-transfer embryo morphology ($\text{AUC} = 0.728$). The strongest multivariable predictor of success in the exploratory model is the **dataset variable `frezzing` (integer values 0–25, $\text{OR} = 2.408$)**, though its exact clinical vitrification protocol remains unverified in source records.

### 16.3 The Necessity of Model Recalibration Under Temporal Drift
When clinical practice evolves (as evidenced by rising pregnancy rates and falling embryo transfer numbers between 2019 and 2024), model calibration suffers. Uncalibrated historical models exhibited systematic underconfidence ($\text{CITL} = +0.937$, $E/O = 0.797$). In clinical deployment, uncalibrated models would unduly discourage prospective patients.

---

## 17. Research Limitations

This research is governed by several transparent limitations:
1. **Unconfirmed Clinical Endpoint:** Whether `recorded_cycle_outcome` represents biochemical pregnancy, gestational sac presence, or live birth remains unconfirmed by the dataset authors.
2. **Absence of Patient Master Identifiers:** The dataset contains no patient-level keys. Multiple treatment cycles from identical couples across the 2024 boundary cannot be completely ruled out.
3. **No External Validation:** Evaluation was conducted strictly on an internal chronological holdout of a single-center cohort. Generalizability to external clinics remains unproven.
4. **Missing Oocyte Origin:** The dataset does not record autologous vs donor oocyte usage, confounding the interpretation of female age in older patients.
5. **Untestable Clinical Hypotheses:** Laboratory equipment, culture media brands, and embryo culture day (Day 3 vs Day 5 blastocyst) were not recorded.

---

## 18. Ethical Considerations

1. **Patient Privacy:** The raw dataset is fully de-identified and publicly distributed under CC BY 4.0. No patient-identifiable data was accessed.
2. **Clinical Safety & Non-Deployment:** This algorithm must **never** be used to select patients for cycle cancellation, deny embryo transfer, or counsel couples.
3. **Scientific Integrity:** Prioritizing statistical correctness over impressive metrics prevents the dissemination of misleading clinical AI claims.

---

## 19. Conclusion and Future Work

The **IVF Insight** project establishes an open, reproducible, and methodologically sound benchmark for clinical prediction modeling in assisted reproduction. By reconciling source datasets, governing temporal feature availability, exposing "The Conflation Illusion," auditing statistical suppression in female age, and evaluating calibration under distribution drift, this work demonstrates that **rigorous clinical data governance and biostatistical skepticism are far more critical to medical AI than model complexity**.

Future work should incorporate multi-center registry validation, live birth endpoints, explicit donor oocyte tracking, and formal clinical decision curve analysis.

---

## 20. References

1. **Maghdid, S., Rashid, T. A., & Askar, S. (2026).** Comprehensive Dataset Profile of In Vitro Fertilization (IVF) Clinical and Embryological Data. *Mendeley Data*, Version 1. DOI: [10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1).
2. **Collins, G. S., Reitsma, J. B., Altman, D. G., & Moons, K. G. M. (2015).** Transparent Reporting of a Multivariable Prediction Model for Individual Prognosis or Diagnosis (TRIPOD): The TRIPOD Statement. *Annals of Internal Medicine*, 162(1), 55–63. DOI: [10.7326/M14-0697](https://doi.org/10.7326/M14-0697).
3. **Steyerberg, E. W. (2019).** *Clinical Prediction Models: A Practical Approach to Development, Validation, and Updating* (2nd ed.). Springer International Publishing. DOI: [10.1007/978-3-030-16399-0](https://doi.org/10.1007/978-3-030-16399-0).
4. **Van Calster, B., Nieboer, D., Vergouwe, Y., De Cock, B., Pencina, M. J., & Steyerberg, E. W. (2016).** A penalty for unfriendly probability forecasts: A calibration hierarchy with application to clinical prediction models. *Journal of Clinical Epidemiology*, 74, 94–102. DOI: [10.1016/j.jclinepi.2015.12.005](https://doi.org/10.1016/j.jclinepi.2015.12.005).
5. **Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019).** Calibration: the Achilles heel of predictive analytics. *BMC Medicine*, 17(1), 230. DOI: [10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7).
6. **Harrell, F. E. (2015).** *Regression Modeling Strategies: With Applications to Linear Models, Logistic and Ordinal Regression, and Survival Analysis* (2nd ed.). Springer. DOI: [10.1007/978-3-319-19425-7](https://doi.org/10.1007/978-3-319-19425-7).
7. **Breiman, L. (2001).** Random Forests. *Machine Learning*, 45(1), 5–32. DOI: [10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324).
8. **Benjamini, Y., & Hochberg, Y. (1995).** Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society: Series B*, 57(1), 289–300. DOI: [10.1111/j.2517-6161.1995.tb02031.x](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x).
9. **Cox, D. R. (1958).** The Regression Analysis of Binary Sequences. *Journal of the Royal Statistical Society: Series B*, 20(2), 215–242. DOI: [10.1111/j.2517-6161.1958.tb00292.x](https://doi.org/10.1111/j.2517-6161.1958.tb00292.x).
10. **Brier, G. W. (1950).** Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, 78(1), 1–3. DOI: [10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2](https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2).
11. **Efron, B., & Tibshirani, R. J. (1994).** *An Introduction to the Bootstrap*. Chapman and Hall/CRC. DOI: [10.1201/9780429246593](https://doi.org/10.1201/9780429246593).
12. **Peduzzi, P., Concato, J., Kemper, E., Holford, T. R., & Feinstein, A. R. (1996).** A simulation study of the number of events per variable in logistic regression analysis. *Journal of Clinical Epidemiology*, 49(12), 1373–1379. DOI: [10.1016/S0895-4356(96)00236-3](https://doi.org/10.1016/S0895-4356(96)00236-3).
13. **Centers for Disease Control and Prevention (CDC). (2023).** *2021 Assisted Reproductive Technology Fertility Clinic and National Summary Report*. U.S. Department of Health and Human Services.
14. **ESHRE Capri Workshop Group. (2017).** Intrauterine insemination and IVF: clinical and economic perspectives. *Human Reproduction Update*, 23(4), 484–496. DOI: [10.1093/humupd/dmx013](https://doi.org/10.1093/humupd/dmx013).
15. **Berkson, J. (1946).** Limitations of the Application of Fourfold Table Analysis to Hospital Data. *Biometrics Bulletin*, 2(3), 47–53. DOI: [10.2307/3002000](https://doi.org/10.2307/3002000).

---

## 21. Reproducibility Appendix

### 21.1 Execution Environment & Architecture
- **Language & Runtime:** Python 3.10+ on Windows 64-bit architecture.
- **Core Dependencies:** `scikit-learn` (1.9+), `statsmodels` (0.15+), `scipy` (1.18+), `pandas` (2.3+), `openpyxl` (3.1+), `matplotlib` (3.11+).
- **Automated Verification:** 45 pytest automated unit and integration tests passing with zero failures.

### 21.2 Command-Line Interface (CLI) Reproduction Guide
```bash
# Phase 1: Dataset Reconciliation
python -m ivf_insight.cli reconcile --excel "data/raw/Dataset Clean.xlsx" --csv "data/raw/Normalized CSV.csv" --output-dir reports

# Phase 2: Feature Governance & Target Provenance
python -m ivf_insight.cli governance --output-dir reports

# Phase 3: Exploratory Data Analysis & Statistics
python -m ivf_insight.cli eda --excel "data/raw/Dataset Clean.xlsx" --output-dir reports

# Phase 4: Predictive Modelling & Chronological Experiments
python -m ivf_insight.cli experiment --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --models-dir models

# Phase 5: Robustness, Sensitivity & Calibration Audit
python -m ivf_insight.cli validate --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --figures-dir reports/robustness_figures

# Phase 5.1: Statistical Integrity & Multicollinearity Audit
python -m ivf_insight.cli audit --excel "data/raw/Dataset Clean.xlsx" --output-dir reports --figures-dir reports/robustness_figures

# Run Complete Automated Test Suite (45 tests)
python -m pytest
```

### 21.3 Manifest Artifacts
- Figure Manifest: `reports/report_figure_manifest.csv` (18 publication figures mapped).
- Data Manifest: `reports/report_data_manifest.csv` (20 structured analytical tables mapped).
- Bibliographic Library: `reports/references.bib` (15 peer-reviewed methodological and biomedical citations).
