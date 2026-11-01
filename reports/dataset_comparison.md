# IVF Insight: Dataset Reconciliation & Data Quality Forensic Audit

**Author:** Senior Biomedical Data Scientist & Research Engineer
**Generated:** 2026-10-31 22:00:11
**Datasets Evaluated:**
- Raw Excel: `data\raw\Dataset Clean.xlsx`
- Normalized CSV: `data\raw\Normalized CSV.csv`

---

## 1. Executive Summary & Core Recommendation

> [!IMPORTANT]
> **CORE VERDICT:** RECOMMENDATION: Use 'data/raw/Dataset Clean.xlsx' (rows 0 to 4999) as the sole authoritative source for subsequent analysis and modeling. Rows 5000 and 5001 must be dropped as they are synthetic min-max boundary rows. 'Normalized CSV.csv' must NOT be used because it has suffered severe information degradation: calendar years were stripped from dates (creating 5 artificial duplicate pairs), character encoding was corrupted (β-HCG -> ?-HCG), 'Non-return of embryos' was silently imputed to 0.0, nominal protocol codes were improperly scaled as continuous metrics, and global min-max scaling was baked in prior to train-test splitting.

### High-Level Metrics Comparison

| Metric | Excel (`Dataset Clean.xlsx`) | CSV (`Normalized CSV.csv`) | Discrepancy / Forensic Status |
|---|---|---|---|
| **Total Rows** | 5002 | 5000 | Exactly +2 rows in Excel (Indices 5000 & 5001) |
| **Patient Record Rows** | 5,000 | 5,000 | Identical (Rows 0 to 4999) |
| **Total Columns** | 21 | 21 | 21 columns in both |
| **Total Missing Cells** | 6 (all in rows 5000–5001) | 0 | Excel patient rows 0..4999 have 0 missing cells |
| **Exact Full Duplicates** | 0 | 5 | CSV has 5 artificial duplicate pairs due to date degradation |
| **Order-Agnostic Record Match** | Yes (100% multiset match) | Yes (100% multiset match) | Verified across all 18 clinical features + target |
| **Date Integrity** | Preserved (Full 2019–2025 dates) | Degraded (Day-of-year fraction) | Calendar years completely stripped in CSV |
| **β-HCG Status** | Preserved (Text + Titers) | Corrupted header + Scaled | Qualitative 'Non-return' encoded as 0.0 in CSV |
| **Target Class Balance** | Class 0: 2508, Class 1: 2492 | Class 0: 2508, Class 1: 2492 | 100% identical row-for-row match |

---

## 2. Forensic Resolution of the Two-Row Excel Discrepancy

Initial inspections noted that Excel contained 5,002 rows, whereas CSV contained 5,000 rows, and Excel reported missing values.

**Findings:**
1. **Rows 0 to 4,999:** Contain 5,000 complete patient treatment records with **0 missing values** across all 21 columns.
2. **Rows 5,000 and 5,001:** Are **synthetic boundary rows** manually or script-appended to the bottom of the worksheet to store dataset minimums and maximums:
   - **Row 5,000:** Every numeric value is identically equal to `min(patient_rows)` (e.g. Female Age = 20, AMH = 0.013, Male Age = 19).
   - **Row 5,001:** Every numeric value is identically equal to `max(patient_rows)` (e.g. Female Age = 49, AMH = 482.1, Male Age = 57).
   - Both boundary rows have null entries (`NaT`/`NaN`) for non-continuous or outcome variables: `Egg retrieval date`, `β-HCG`, and the target outcome.
   - This accounts for 100% of the 6 missing values in Excel (2 dates, 2 β-HCG, 2 outcomes).
3. **Resolution:** When generating the CSV, the author used rows 5000 and 5001 to compute Min-Max normalization bounds, and then dropped those two rows. Rows 5000 and 5001 must be formally filtered out in the research pipeline.

## 3. Duplicate Analysis & The Origin of CSV Duplicates

- **Excel Exact Duplicates:** 0 across all 5,002 rows.
- **CSV Exact Duplicates:** 5 rows (5 duplicate pairs).

**Why does CSV contain exact duplicates when Excel contains none?**
Forensic examination revealed that the CSV normalization transformed `Egg retrieval date` into an intra-year fraction `(day_of_year - 1) / 365`. This removed the year entirely.
When two distinct patient treatment cycles shared identical clinical features (which occurred in 1,474 rows across the dataset) and took place on the **same calendar day in different years** (e.g., May 11, 2019 vs May 11, 2025):
- In Excel, they are distinct records with different retrieval years.
- In CSV, both dates mapped to `0.356164`, collapsing distinct clinical cycles into exact 21-column duplicates.

Specific collapsed row pairs in CSV:
- CSV Rows `[1305, 4847]`: Excel dates `['2019-05-11', '2025-05-11']`
- CSV Rows `[1316, 4853]`: Excel dates `['2019-05-12', '2025-05-12']`
- CSV Rows `[1299, 4846]`: Excel dates `['2019-05-11', '2025-05-11']`
- CSV Rows `[1315, 4852]`: Excel dates `['2019-05-12', '2025-05-12']`
- CSV Rows `[1314, 4851]`: Excel dates `['2019-05-12', '2025-05-12']`


## 4. Date Preservation & Information Loss

- **Excel Representation:** Native `datetime64[ns]` spanning `2019-01-02` to `2025-06-30`, encompassing **1,400 unique calendar dates** across 7 years:
  - 2019: 1730 cycles
  - 2020: 298 cycles
  - 2021: 411 cycles
  - 2022: 382 cycles
  - 2023: 721 cycles
  - 2024: 952 cycles
  - 2025: 506 cycles
- **CSV Representation:** Continuous `float64` with only **665 unique values**.
- **Conversion Mechanism:** Intra-annual fraction formula `(day_of_year - 1) / 365.0` with rounding and leap-year shifts.
- **Clinical/Methodological Implication:** Collapsing dates destroys temporal sequencing, prevents time-series or seasonal analysis, and induces artificial record collisions. CSV date data is irreversibly degraded.

## 5. β-HCG vs ?-HCG Reconciliation

- **Column Header Corruption:** The Greek letter `β` was corrupted into `?` during CSV export, likely due to ASCII/Windows-1252 character conversion without UTF-8 encoding.
- **Qualitative Status Loss:**
  - In Excel, 1250 records have status `'Non-return of embryos'`.
  - In CSV, all 1,250 records were replaced with `0.0`.
  - *Clinical Hazard:* In assisted reproductive technology, 'Non-return of embryos' indicates no transfer occurred (e.g. total fertilization failure, cycle cancellation, or all embryos cryopreserved). Imputing `0.0` equates cycle cancellation with a negative serum biochemical pregnancy test, introducing false biological semantics.
- **Normalization Scaling:** Quantitative β-HCG titers were normalized using a scaling denominator of `6800.0`.
- **Transcription Discrepancies:** 8 records exhibit discrepancies between Excel and CSV:
  - Row 731: Excel raw `POSITIVE(201)` vs CSV `0.288970588` (Transcription error / alternative scaling factor)
  - Row 804: Excel raw `POSITIVE(753)` vs CSV `0.084264706` (Transcription error / alternative scaling factor)
  - Row 3036: Excel raw `NEGATIVE` vs CSV `0.003235294` (Excel contains unquantified 'NEGATIVE'; CSV contains 22/6800)
  - Row 3325: Excel raw `POSITIVE (225)` vs CSV `0.0375` (Transcription error / alternative scaling factor)
  - Row 3949: Excel raw `POSITIVE(753)` vs CSV `0.084264706` (Transcription error / alternative scaling factor)


## 6. Target Variable & Implantation Outcome Distribution

- **Excel Header:** `Output(failed implantation or successful implantation)`
- **CSV Header:** `Output (Output(failed implantation or successful implantation)` (duplicated header syntax)
- **Class Distribution (Rows 0 to 4,999):**
  - **Class 0 (Failed Implantation):** 2508 records (50.16%)
  - **Class 1 (Successful Implantation):** 2492 records (49.84%)
  - **Boundary Rows (5000–5001):** 2 missing entries (NaN)
- **Reconciliation Verdict:** The target labels for all 5,000 patient records match row-for-row with **100% concordance**.

## 7. Categorical Encoding & Typographical Artifacts

### `Number of attempts`

- In Excel, 2 records contained a leading backtick typo: `'`1'`. This caused pandas to read the entire column as `object` dtype.
- In CSV, this typo was corrected to integer `1`, and then min-max normalized by `11.0` (range 0 to 11).
- *Action for Pipeline:* Clean backticks and cast to integer.

### `Medicines and treatments`

- Represents nominal protocol IDs ranging from `1` to `183` (182 unique discrete protocols).
- In CSV, the author applied continuous min-max scaling: `(protocol_id - 1) / 182.0`.
- *Methodological Flaw:* Treatment protocol IDs are nominal categories. Applying continuous scaling treats arbitrary categorical labels as ordered numerical distances (e.g. implying protocol 90 is twice protocol 45). In the modeling pipeline, this must be treated categorically.

## 8. Verification of Numerical Normalization

- **Normalization Formula:** `(value - min) / (max - min)`
- **Bounds Origin:** The exact minimums and maximums used for all 18 clinical features match Excel rows 5000 and 5001.
- **Residual Analysis:** Across all 5,000 patient rows and all 18 numeric features, the maximum absolute residual between CSV and computed normalization is `< 5.0e-8` (pure 32/64-bit float CSV rounding).
- **Data Leakage Alert:** Min-max scaling was fitted across the entire dataset without cross-validation or train-test separation. Downstream modeling must fit all transformers strictly within training splits.

## 9. Order-Agnostic Record Verification

- **Multiset Match:** True across all 5,000 records.
- **Sequential Row Match:** True.
This proves that rows 0..4999 in Excel and rows 0..4999 in CSV are identical record-for-record in both sequential order and multiset feature distribution.

## 10. Patient-Level & Treatment-Cycle Clusters

- **Biological Signature:** Couples grouped by fixed parameters (`Female Age`, `Male Age`, `AMH`, `Sperm count`, `Sperm motility`, `Sperm morphology`).
- **Identified Multi-Cycle Clusters:** 1457 clusters comprising 3058 total treatment cycles.
- **Cluster Sizes:** Up to 4 cycles per biological signature.
- **Ethical / Research Safeguard:** Because the dataset is de-identified and lacks unique patient identifiers, these clusters suggest repeat cycles or shared clinical phenotypes, but **patient identity cannot be confirmed**. These records must NOT be merged or dropped, but potential grouping must be considered during error analysis.

## 11. Feature-by-Feature Data Quality Summary

| excel_feature | csv_feature | excel_dtype | csv_dtype | excel_missing_all_5002 | excel_missing_patient_5000 | csv_missing_5000 | excel_unique_count | csv_unique_count | normalization_applied | norm_min_bound | norm_max_bound | max_residual | clinical_variable_type | reconciliation_notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Female Age | Female Age | int64 | float64 | 0 | 0 | 0 | 30 | 30 | Min-Max [0, 1] | 20.0 | 49.0 | 4.83e-10 | Baseline Demographic (Continuous/Integer) | Min 20, Max 49; scaled as (age - 20) / 29. |
| Number of attempts | Number of attempts | object | float64 | 0 | 0 | 0 | 11 | 10 | Min-Max [0, 1] | 0.0 | 11.0 | 4.55e-10 | Treatment History (Discrete Count) | Typo '`1' in 2 rows; scaled as attempts / 11. |
| AMH | AMH | float64 | float64 | 0 | 0 | 0 | 849 | 849 | Min-Max [0, 1] | 0.013 | 482.1 | 4.96e-08 | Endocrine Biomarker (Continuous) | Anti-Müllerian Hormone (unit not specified in source dataset); min 0.013, max 482.1. |
| Medicines and treatments | Medicines and treatments | int64 | float64 | 0 | 0 | 0 | 182 | 182 | Min-Max [0, 1] | 1.0 | 183.0 | 4.95e-10 | Clinical Regimen (Nominal Protocol ID) | 182 discrete regimen IDs inappropriately scaled as continuous metric. |
| Egg retrieval date | Egg retrieval date | datetime64[ns] | float64 | 2 | 0 | 0 | 1400 | 665 | Custom (day/365) |  |  |  | Temporal Timestamp (Date) | Year stripped; reduced to (day-of-year - 1)/365; created 5 duplicate pairs. |
| Oocyte Maturity MII | Oocyte Maturity MII | int64 | float64 | 0 | 0 | 0 | 36 | 36 | Min-Max [0, 1] | 0.0 | 52.0 | 4.62e-10 | Embryology Lab (Discrete Count) | Maturity grading counts (MII, MI, others). |
| Oocyte Maturity MI | Oocyte Maturity MI | int64 | float64 | 0 | 0 | 0 | 18 | 18 | Min-Max [0, 1] | 0.0 | 32.0 | 0.00e+00 | Embryology Lab (Discrete Count) | Maturity grading counts (MII, MI, others). |
| Oocyte Maturity others | Oocyte Maturity others | int64 | float64 | 0 | 0 | 0 | 22 | 22 | Min-Max [0, 1] | 0.0 | 65.0 | 4.62e-10 | Embryology Lab (Discrete Count) | Maturity grading counts (MII, MI, others). |
| Male Age | Male Age | int64 | float64 | 0 | 0 | 0 | 39 | 39 | Min-Max [0, 1] | 19.0 | 57.0 | 4.74e-10 | Baseline Demographic (Continuous/Integer) | Min 19, Max 57; scaled as (age - 19) / 38. |
| Sperm count | Sperm count | float64 | float64 | 0 | 0 | 0 | 110 | 110 | Min-Max [0, 1] | 0.0 | 115.0 | 4.35e-08 | Andrology Lab (Continuous/Discrete) | Semen analysis parameter: Sperm count. |
| Sperm motility | Sperm motility | float64 | float64 | 0 | 0 | 0 | 154 | 154 | Min-Max [0, 1] | 0.0 | 89.0 | 4.83e-08 | Andrology Lab (Continuous/Discrete) | Semen analysis parameter: Sperm motility. |
| Sperm morphology | Sperm morphology | float64 | float64 | 0 | 0 | 0 | 27 | 27 | Min-Max [0, 1] | 0.0 | 3.0 | 3.33e-10 | Andrology Lab (Continuous/Discrete) | Semen analysis parameter: Sperm morphology. |
| Number of fertilized eggs | Number of fertilized eggs | int64 | float64 | 0 | 0 | 0 | 34 | 34 | Min-Max [0, 1] | 0.0 | 35.0 | 4.29e-10 | Embryology Metric (Count) | Fertilized oocyte count; min 0, max 35. |
| Embryo Grade 1 | Embryo Grade 1 | int64 | float64 | 0 | 0 | 0 | 28 | 28 | Min-Max [0, 1] | 0.0 | 32.0 | 0.00e+00 | Embryology Morphological Score (Count) | Graded embryo count: Embryo Grade 1. |
| Embryo Grade 2 | Embryo Grade 2 | int64 | float64 | 0 | 0 | 0 | 16 | 16 | Min-Max [0, 1] | 0.0 | 32.0 | 0.00e+00 | Embryology Morphological Score (Count) | Graded embryo count: Embryo Grade 2. |
| Embryo Grade 3 | Embryo Grade 3 | int64 | float64 | 0 | 0 | 0 | 12 | 12 | Min-Max [0, 1] | 0.0 | 11.0 | 4.55e-10 | Embryology Morphological Score (Count) | Graded embryo count: Embryo Grade 3. |
| Embryo Grade 4 | Embryo Grade 4 | int64 | float64 | 0 | 0 | 0 | 7 | 7 | Min-Max [0, 1] | 0.0 | 9.0 | 4.44e-10 | Embryology Morphological Score (Count) | Graded embryo count: Embryo Grade 4. |
| Number of embryos | Number of embryos | int64 | float64 | 0 | 0 | 0 | 9 | 9 | Min-Max [0, 1] | 0.0 | 8.0 | 0.00e+00 | Embryology Metric (Count) | Total embryos available; min 0, max 8. |
| frezzing | frezzing | int64 | float64 | 0 | 0 | 0 | 22 | 22 | Min-Max [0, 1] | 0.0 | 25.0 | 0.00e+00 | Embryology Cryopreservation (Count) | Cryopreserved (frozen) embryo count; min 0, max 25. |
| β-HCG | ?-HCG | object | float64 | 2 | 0 | 0 | 1276 | 1018 | Ratio / 6800 |  |  |  | Post-Treatment Biomarker (Qualitative/Quantitative) | Header corrupted to '?-HCG'; scaled by /6800; 'Non-return' encoded as 0.0. |
| Output(failed implantation or successful implantation) | Output (Output(failed implantation or successful implantation) | float64 | int64 | 2 | 0 | 0 | 2 | 2 | None |  |  |  | Clinical Outcome (Binary Classification Target) | 100% agreement on rows 0..4999 (0: 2508, 1: 2492); CSV has duplicate header syntax. |

---

## 12. Final Recommendation & Modeling Guidelines

1. **Data Source:** Exclusively use `data/raw/Dataset Clean.xlsx`, dropping rows 5000 and 5001 (`df.iloc[:5000]`).
2. **Disregard CSV:** Exclude `Normalized CSV.csv` from modeling pipelines to prevent temporal and clinical information loss.
3. **Target Leakage Safeguard:** Drop `β-HCG` from predictive feature sets for implantation prediction, as β-HCG is measured after embryo transfer and constitutes direct target leakage.
4. **Categorical Handling:** One-hot encode or group rare levels for `Medicines and treatments` inside cross-validation folds.
5. **Typo Sanitization:** Strip backticks from `Number of attempts` (`'`1' -> 1`).
6. **Date Exploitation:** Retain full datetime stamps for longitudinal and chronological splitting.
