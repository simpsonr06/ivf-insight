# IVF Insight Clinical Data Dictionary & Feature Governance Registry

This data dictionary formally defines all 21 raw variables in the authoritative Mendeley IVF clinical dataset (`Dataset Clean.xlsx`), specifying clinical concepts, data types, physical units, permissible ranges, empirical summary metrics, and feature governance decisions across analytical scenarios.

---

## 1. Primary Dataset Specifications

- **Authoritative File:** `data/raw/Dataset Clean.xlsx` (Version 1, Mendeley Data, [DOI: 10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1)).
- **Raw File Dimensions:** 5,002 rows $\times$ 21 columns.
- **Excluded Upstream Rows:** Rows 5000 and 5001 were identified in Phase 1 as synthetic Min-Max normalization boundary rows injected upstream.
- **Clean Analytical Sample:** Exactly **5,000 candidate clinical treatment-cycle records** (indices 0 to 4999).
- **Target Variable:** Standardized as `recorded_cycle_outcome`.

---

## 2. Cohort Definitions

| Cohort Name | Sample Size ($N$) | Cohort Definition & Selection Logic | Outcome Class 0 ($N, \%$) | Outcome Class 1 ($N, \%$) |
| :--- | :--- | :--- | :--- | :--- |
| **Full-Cycle Cohort** | 5,000 | All initiated treatment cycles, including cycles cancelled prior to embryo transfer. | 2,508 ($50.16\%$) | 2,492 ($49.84\%$) |
| **Embryo-Transfer Cohort** | 3,750 | Treatment cycles where at least one embryo was transferred (`Number of embryos` $\ge 1$). Excludes the 1,250 cancelled zero-transfer cycles. | 1,258 ($33.55\%$) | 2,492 ($66.45\%$) |

---

## 3. Comprehensive Feature Dictionary (21 Variables)

| # | Raw Column Name | Sanitized Snake_Case Name | Clinical Concept & Definition | Data Type | Physical Units | Valid Range | Missing Count ($N$) | Cohort Distribution (Median [IQR] / Mean $\pm$ SD) | Feature Governance & Scenario Allocation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Serial number` | `serial_number` | Arbitrary patient/cycle row identifier. | Integer | None | 1 – 5000 | 0 | Sequential sequence. | **Excluded:** Non-predictive metadata identifier. |
| 2 | `Egg retrieval date` | `egg_retrieval_date` | Date of oocyte aspiration pickup procedure. | Date | YYYY-MM-DD | 2010 – 2025 | 0 | 2010 to 2025 chronology. | **Validation Partition:** Excluded from predictive features; used strictly for chronological splitting (`2024-01-01`). |
| 3 | `Female Age` | `female_age` | Chronological age of female patient at cycle initiation. | Integer | Years | 18 – 49 | 0 | Median: 34.0 [7.0]; Mean: $34.13 \pm 5.17$. | **Included:** Scenario A (Baseline), Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 4 | `Male Age` | `male_age` | Chronological age of male partner at cycle initiation. | Integer | Years | 19 – 57 | 0 | Median: 35.0 [8.0]; Mean: $35.86 \pm 6.36$. | **Included:** Scenario A (Baseline), Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 5 | `AMH` | `amh` | Serum Anti-Müllerian Hormone quantifying ovarian reserve. | Float | Unspecified in source dataset | 0.1 – 482.1 | 0 | Median: 1.59 [2.36]; Mean: $2.54 \pm 12.02$; Min: 0.013; Max: 482.1. Note: 3 extreme outliers at 482.1 (unit unrecorded). | **Included:** Scenario A (Baseline), Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 6 | `Number of attempts` | `number_of_attempts` | Cumulative count of initiated IVF/ICSI cycles attempted by patient. | Integer | Count | 1 – 6 | 0 | Median: 1.0 [0.0]; Mean: $1.21 \pm 0.54$. (98.5% between 1–2). | **Included:** Scenario A (Baseline), Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 7 | `Medicines and treatments` | `medicines_and_treatments` | Controlled ovarian stimulation medication regimen. | Categorical | String code | Various | 0 | Textual medication protocols. | **Conditional Baseline:** Excluded from primary scenarios due to lack of protocol standardization. |
| 8 | `Sperm count` | `sperm_count` | Pre-preparation semen analysis sperm concentration. | Float | $10^6$/mL | 0.0 – 120.0 | 2 | Median: 35.0 [28.0]; Mean: $38.45 \pm 22.10$. | **Conditional Baseline:** Excluded from primary scenarios due to incomplete documentation. |
| 9 | `Sperm motility` | `sperm_motility` | Total progressive and non-progressive sperm motility percentage. | Float | % | 0.0 – 90.0 | 1 | Median: 50.0 [25.0]; Mean: $48.21 \pm 18.34$. | **Conditional Baseline:** Excluded from primary scenarios due to incomplete documentation. |
| 10 | `Sperm morphology` | `sperm_morphology` | Strict normal Kruger sperm morphology percentage. | Float | % | 0.0 – 25.0 | 1 | Median: 4.0 [3.0]; Mean: $4.85 \pm 3.12$. | **Conditional Baseline:** Excluded from primary scenarios due to incomplete documentation. |
| 11 | `Oocyte Maturity MII` | `oocyte_maturity_mii` | Count of mature Metaphase II oocytes retrieved. | Integer | Count | 0 – 33 | 0 | Median: 7.0 [7.0]; Mean: $7.74 \pm 5.20$. | **Included:** Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 12 | `Oocyte Maturity MI` | `oocyte_maturity_mi` | Count of intermediate Metaphase I oocytes retrieved. | Integer | Count | 0 – 12 | 0 | Median: 0.0 [1.0]; Mean: $0.94 \pm 1.45$. | **Included:** Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 13 | `Oocyte Maturity others` | `oocyte_maturity_others` | Count of germinal vesicle (GV) and degenerated oocytes. | Integer | Count | 0 – 18 | 0 | Median: 0.0 [1.0]; Mean: $0.92 \pm 1.62$. | **Included:** Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 14 | `Number of fertilized eggs` | `number_of_fertilized_eggs` | Count of successfully fertilized two-pronuclei (2PN) zygotes. | Integer | Count | 0 – 35 | 0 | Median: 5.0 [6.0]; Mean: $6.47 \pm 4.46$. (High VIF = 11.14). | **Included:** Scenario B (Post-Retrieval), Scenario C (Pre-Transfer). |
| 15 | `Embryo Grade 1` | `embryo_grade_1` | Count of top-quality Grade 1 embryos on day of transfer. | Integer | Count | 0 – 20 | 0 | Median: 1.0 [2.0]; Mean: $1.83 \pm 2.08$. | **Included:** Scenario C (Pre-Transfer). |
| 16 | `Embryo Grade 2` | `embryo_grade_2` | Count of good-quality Grade 2 embryos on day of transfer. | Integer | Count | 0 – 17 | 0 | Median: 1.0 [2.0]; Mean: $1.48 \pm 1.83$. | **Included:** Scenario C (Pre-Transfer). |
| 17 | `Embryo Grade 3` | `embryo_grade_3` | Count of fair-quality Grade 3 embryos on day of transfer. | Integer | Count | 0 – 13 | 0 | Median: 0.0 [1.0]; Mean: $0.73 \pm 1.25$. | **Included:** Scenario C (Pre-Transfer). |
| 18 | `Embryo Grade 4` | `embryo_grade_4` | Count of poor-quality Grade 4 embryos on day of transfer. | Integer | Count | 0 – 7 | 0 | Median: 0.0 [0.0]; Mean: $0.08 \pm 0.42$. (95% zero). | **Included:** Scenario C (Pre-Transfer). |
| 19 | `Number of embryos` | `number_of_embryos` | Count of fresh or thawed embryos transferred into uterine cavity. | Integer | Count | 0 – 8 | 0 | Full cohort mean: $1.89 \pm 1.22$ (1,250 zeros). Transfer cohort mean: $2.52 \pm 0.77$. | **Included:** Scenario C (Pre-Transfer). |
| 20 | `frezzing` | `frezzing` | Count of surplus high-quality embryos cryopreserved (vitrified). | Integer | Count | 0 – 25 | 0 | Median: 0.0 [2.0]; Mean: $1.55 \pm 2.65$. (66.6% zero). Note: Integer count, NOT binary. | **Included:** Scenario C (Pre-Transfer). Ranked #1 predictor. |
| 21 | `Output(failed implantation or successful implantation)` | `recorded_cycle_outcome` | Recorded binary outcome status for treatment cycle. | Binary | Code | 0 or 1 | 0 | 2,508 Class 0 (50.16%) vs 2,492 Class 1 (49.84%). | **Target Variable:** Supervised training label. Never used as a feature. |

---

## 4. Target Variable Breakdown & Composition

The recorded outcome label (`recorded_cycle_outcome`) is composite in nature and comprises three distinct clinical subpopulations:

```
Total Clean Sample (N = 5,000)
├── Class 1: Positive Pregnancy Outcome (N = 2,492; 49.84%)
│   └── All 2,492 cycles received embryo transfer (mean 2.68 embryos transferred)
└── Class 0: Negative / Cancelled Outcome (N = 2,508; 50.16%)
    ├── Cancelled Cycles (Non-Return of Embryos): N = 1,250 (49.84% of Class 0)
    │   └── Exactly 0 embryos transferred; no post-transfer pregnancy test possible
    ├── Genuine Negative Pregnancy Tests: N = 1,250 (49.84% of Class 0)
    │   └── Received embryo transfer (mean 2.20 embryos); confirmed negative β-HCG
    └── Discordant Positive β-HCG with Recorded Class 0: N = 8 (0.32% of Class 0)
        └── Recorded β-HCG > 5 mIU/mL but labeled Class 0 by clinic (unresolved endpoint discrepancy consistent with preclinical loss or reporting anomaly)
```

---

## 5. Temporal Scenario Feature Allocations

| Scenario Name | Clinical Decision Milestone | Feature Count | Features Included | Primary Clinical Question Addressed |
| :--- | :--- | :--- | :--- | :--- |
| **Scenario A (Baseline)** | Pre-stimulation couple consultation | 4 | `Female Age`, `Male Age`, `AMH`, `Number of attempts` | Can baseline couple demographics and ovarian reserve predict cycle outcome before ovarian stimulation begins? |
| **Scenario B (Post-Retrieval)** | Post-oocyte pickup and ICSI fertilization | 8 | Scenario A features + `Oocyte Maturity MII`, `Oocyte Maturity MI`, `Oocyte Maturity others`, `Number of fertilized eggs` | Does laboratory fertilization yield provide incremental prognostication beyond baseline parameters? |
| **Scenario C (Pre-Transfer)** | Day of embryo transfer | 14 | Scenario B features + `Embryo Grade 1`, `Embryo Grade 2`, `Embryo Grade 3`, `Embryo Grade 4`, `Number of embryos`, `frezzing` | What is the cumulative prognostic discrimination achievable immediately prior to embryo transfer? |

---

## 6. Target Leakage & Post-Outcome Prohibitions

1. **`beta-HCG` Laboratory Value:** In `Dataset Clean.xlsx`, post-transfer serum $\beta$-HCG testing was performed 10–14 days post-transfer and strongly correlates with the recorded outcome label. Including $\beta$-HCG in any predictive feature matrix represents catastrophic post-outcome target leakage and is strictly prohibited.
2. **`Non-return of embryos` Binary Status:** Indicating cycle cancellation directly determines Class 0 outcome with 100% precision. It must never be included as a predictor in full-cycle models.
