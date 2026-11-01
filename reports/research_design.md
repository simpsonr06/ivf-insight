# IVF Insight: Clinical Predictive Modeling Research Design & Feature Governance

**Author:** Senior Biomedical Data Scientist & Research Engineer
**Generated:** 2026-10-31 22:58:04
**Source Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 authoritative patient treatment cycles)

---

## 1. Research Question & Clinical Purpose

**Primary Research Question:** Can baseline clinical, laboratory, and embryological features available at distinct treatment milestones accurately classify IVF cycle outcomes (`recorded_cycle_outcome`) in a published, de-identified patient cohort without relying on post-outcome target leakage?

**Clinical Context & Non-Claim Notice:** Assisted reproductive technology (ART) involves sequential decision points across ovarian stimulation, egg retrieval, and embryo culture. This research formalizes predictive capability at each distinct milestone as an educational portfolio project. It is **not** a clinical decision support tool, medical device, or basis for clinical management. No claim of clinical validity is made.

## 2. Intended Prediction Population & Observation Rules

- **Cohort Size:** Exactly 5,000 complete patient treatment cycles.
- **Authoritative Source:** `data/raw/Dataset Clean.xlsx` (rows 0 to 4,999).
- **Exclusion Rules:** Rows 5,000 and 5,001 are synthetic Min-Max boundary rows and are strictly excluded.
- **Normalization Rule:** Preprocessed `Normalized CSV.csv` is completely barred from model development due to calendar year stripping, encoding corruption, and baked-in leakage.
- **Observation Preservation:** All 5,000 candidate records are retained without automated filtering or record deletion.

## 3. Prediction Scenarios & Temporal Feature Governance

To reflect realistic clinical practice, feature availability is governed strictly by the IVF timeline. No future information is permitted in earlier prediction scenarios. Feature availability is never assumed based solely on column names.

### Scenario A: Baseline Prediction (Pre-Stimulation)
- **Prediction Timepoint:** Consultation prior to the initiation of controlled ovarian hyperstimulation (COH).
- **Clinical Utility:** Initial prognosis estimation, couple counseling, and stimulation protocol personalization.
- **Strictly Confirmed Pre-Stimulation Features (4 features):** `Female Age, Number of attempts, AMH, Male Age`.
- **Candidate Baseline Features Including Conditional (8 features):** `Female Age, Number of attempts, AMH, Medicines and treatments, Male Age, Sperm count, Sperm motility, Sperm morphology`.
  - *Timing Caveat 1 (`Medicines and treatments`):* Included conditionally only under the assumption of **planned stimulation protocol**. If this feature records medications/doses actually administered or adjusted during stimulation, it is not available pre-stimulation and must be deferred to Scenario B.
  - *Timing Caveat 2 (`Sperm count`, `Sperm motility`, `Sperm morphology`):* Included conditionally under the assumption of **baseline diagnostic semen analysis** (pre-treatment workup). If these represent retrieval-day fresh ejaculate/post-wash parameters, they belong strictly in Scenario B.
- **Excluded Predictors:** All retrieval parameters, fertilization metrics, embryo grading scores, and post-transfer tests.

### Scenario B: Post-Retrieval Prediction
- **Prediction Timepoint:** Day 1 post-oocyte pick-up (OPU), following nuclear maturity grading and fertilization check.
- **Clinical Utility:** Mid-cycle assessment to guide decisions regarding extended blastocyst culture vs early Day 3 transfer.
- **Candidate Predictors (12 features):** `Female Age, Number of attempts, AMH, Medicines and treatments, Oocyte Maturity MII, Oocyte Maturity MI, Oocyte Maturity others, Male Age, Sperm count, Sperm motility, Sperm morphology, Number of fertilized eggs`.
- **Additional Features:** `Oocyte Maturity MII`, `Oocyte Maturity MI`, `Oocyte Maturity others`, `Number of fertilized eggs`.
- **Excluded Predictors:** Cleavage / blastocyst morphological scores, embryo counts, freezing count, and post-transfer tests.

### Scenario C: Post-Embryo-Development Prediction
- **Prediction Timepoint:** Immediately prior to embryo transfer (Day 3 or Day 5).
- **Clinical Utility:** Final pre-transfer prognosis estimation, supporting elective single embryo transfer (eSET) vs freezing decisions.
- **Candidate Predictors (18 features):** `Female Age, Number of attempts, AMH, Medicines and treatments, Oocyte Maturity MII, Oocyte Maturity MI, Oocyte Maturity others, Male Age, Sperm count, Sperm motility, Sperm morphology, Number of fertilized eggs, Embryo Grade 1, Embryo Grade 2, Embryo Grade 3, Embryo Grade 4, Number of embryos, frezzing`.
- **Additional Features:** `Embryo Grade 1`, `Embryo Grade 2`, `Embryo Grade 3`, `Embryo Grade 4`, `Number of embryos`, `frezzing`.
- **Excluded Predictors:** Post-transfer tests (`β-HCG`).

## 4. Target Provenance & Biological Validation

- **Standardized Target Name:** `recorded_cycle_outcome` (Dataset Header: `Output(failed implantation or successful implantation)`).
- **Original Binary Values:** Preserved exactly as recorded (`0.0` and `1.0`).
- **Recorded Target Distribution:** Class 0 = 2508 (50.16%); Class 1 = 2492 (49.84%).

**Clinical Distinction Across Target Sub-Cohorts:**
> [!IMPORTANT]
> **Do NOT call every Class 0 record an 'implantation failure'.** Implantation requires intrauterine embryo transfer. In cycles where no embryos were transferred, implantation was biologically impossible.

1. **Cycles without Embryo Transfer (N = 1250, 25.0% of cohort):** Records with `β-HCG == 'Non-return of embryos'`. All map to **Class 0 (100%)**. These represent cycle cancellations, total fertilization failure, embryo developmental arrest, or freeze-all cycles without fresh transfer. Implantation was never attempted.
2. **Cycles with Completed Transfer & Negative Pregnancy Test (N = 1250, 25.0% of cohort):** Records with qualitative or quantitative negative β-HCG (`NEGATIVE`). All map to **Class 0 (100%)**. These represent true biological negative cycle outcomes.
3. **Cycles with Positive Pregnancy Test & Recorded Class 1 (N = 2,492, 49.84% of cohort):** Records with positive β-HCG titers (14 to 14,589 mIU/mL) mapping to **Class 1 (100%)**.
4. **Discordant Positive β-HCG with Recorded Class 0 (N = 8, 0.16% of cohort):** Exactly 8 treatment cycles (Rows 876, 878, 1298, 1846, 1923, 3939, 4040, 4849) had positive β-HCG titers (35 to 2,100 mIU/mL) yet were classified as **Class 0**.

**Biochemical Pregnancy vs Clinical Pregnancy Uncertainty:**
In reproductive endocrinology, trophoblastic secretion of β-HCG indicates **biochemical pregnancy**, whereas **clinical pregnancy** requires ultrasound visualization of an intrauterine gestational sac with embryonic heartbeat at 5-7 weeks of gestation. Between 10% and 20% of biochemical pregnancies arrest before ultrasound confirmation (biochemical pregnancy loss / non-progressing implantation). The 8 discordant cases in this dataset are clinically consistent with biochemical pregnancy loss. However, because the dataset authors did not document whether Class 1 reflects biochemical pregnancy, clinical pregnancy sac, or live birth, the exact clinical endpoint remains an unresolved research question.

## 5. Potential Leakage Pathways & Prohibited Practices

> [!CAUTION]
> **PROHIBITED FEATURE: β-HCG is strictly banned from all prediction models.**

1. **Post-Outcome Leakage:** Serum β-HCG is measured 10-14 days after embryo transfer. Its inclusion in baseline or pre-transfer models represents catastrophic target leakage.
2. **Global Preprocessing Leakage:** Min-Max scaling or imputation fitted on the entire dataset prior to train/test partitioning leaks distribution statistics. All transformations must be encapsulated inside cross-validation folds.
3. **Protocol Categorical Misuse:** `Medicines and treatments` (182 discrete regimen IDs) must never be scaled continuously; it must be treated as a categorical feature.
4. **Synthetic Boundary Leakage:** Excel rows 5000 and 5001 must be dropped before any processing.

## 6. Validation Strategy: Prospective Chronological vs Random Splitting

### Limitations of Standard Random K-Fold Splitting
1. **Longitudinal Clustered Leakage:** 1,457 potential repeat-cycle clusters (3,058 cycles) exist in the data. Random splitting distributes cycles from the same couple across train and test folds, artificially inflating accuracy.
2. **Temporal Inversion:** Random splitting trains on future cycles (2024-2025) to predict past cycles (2019), violating clinical causality.
3. **Masked Cohort Drift:** Empirical positive rates vary substantially over time (from 35.9% in 2020 to 60.7% in 2024). Random splitting homogenizes these distributions, hiding vulnerability to real practice changes.

### Approved Validation Protocol: Prospective Chronological Partition
- **Partition Cutoff Date:** `2024-01-01`
- **Development Set (Historical):** 3542 cycles (70.8%), spanning `2019-01-02 00:00:00` to `2023-12-31 00:00:00`.
  - **Train Class Distribution:** Class 0 = 1861 (52.5%), Class 1 = 1681 (47.5%).
- **Prospective Test Set (Future):** 1458 cycles (29.2%), spanning `2024-01-03 00:00:00` to `2025-06-30 00:00:00`.
  - **Test Class Distribution:** Class 0 = 647 (44.4%), Class 1 = 811 (55.6%).
- **Inner Cross-Validation:** 5-fold Stratified or Time-Series Split within the historical training partition only.

> [!WARNING]
> **Patient Separation Notice:** NO CLAIM OF PATIENT-LEVEL SEPARATION. Partitions are separated strictly by cycle retrieval timestamp, not verified patient identity, because patient identifiers are omitted from the source dataset.
> **Repeated-Cycle Leakage:** Repeated-cycle data leakage cannot be completely ruled out without patient identifiers. Although prospective chronological splitting prevents future cycles from leaking into past training data, the presence of repeated cycles from the same patient across the cutoff boundary (e.g. initial cycle in 2023, subsequent cycle in 2024) remains possible due to unlinked patient observations.

## 7. Known Dataset Limitations & Unresolved Research Questions

The complete audit of unresolved clinical and technical questions for the dataset authors is documented in `reports/research_questions.md`.