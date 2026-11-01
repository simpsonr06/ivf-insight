# IVF Insight: Unresolved Research & Clinical Governance Questions

**Author:** Senior Biomedical Data Scientist & Research Engineer
**Date:** 2026-10-31
**Target Audience:** Original Dataset Authors / Clinical Investigators

---

Before deploying predictive machine learning models or drawing clinical conclusions, the following seven unresolved research design and clinical definitions must be clarified by the dataset authors. In accordance with clinical data science best practices, missing clinical definitions must not be invented.

### 1. Exact Definition of Implantation Success (Target Endpoint)
- **Context:** The original binary target header is `Output(failed implantation or successful implantation)`. In reproductive medicine, implantation success can refer to:
  1. *Biochemical pregnancy:* Serum β-HCG elevation (>10 or >25 mIU/mL) 12-14 days post-transfer.
  2. *Clinical pregnancy:* Ultrasound visualization of an intrauterine gestational sac (with or without yolk sac/fetal pole) at 5-7 weeks of gestation.
  3. *Ongoing pregnancy / Live birth:* Viable intrauterine pregnancy beyond 12 or 20 weeks, or delivery of a living infant.
- **Specific Questions:**
  - What exact clinical milestone constitutes `Output == 1` in this dataset?
  - Was confirmation based solely on serum β-HCG or on subsequent transvaginal ultrasound?

### 2. Clinical Meaning of Class 0 in Cycles Without Embryo Transfer
- **Context:** Exactly 1,250 records (25.0% of the entire 5,000-cycle cohort) have `β-HCG == 'Non-return of embryos'` and are uniformly assigned `Output == 0`.
- **Specific Questions:**
  - Does `Non-return of embryos` denote cycles where no embryo transfer was performed (e.g. cycle cancellation due to poor ovarian response, total fertilization failure, complete embryo developmental arrest, elective freeze-all due to ovarian hyperstimulation syndrome [OHSS] risk, or pre-implantation genetic testing)?
  - If no embryos were transferred into the uterine cavity, implantation was biologically impossible. Why are these cycles grouped into the same target class (`0`) as cycles with completed embryo transfer and negative pregnancy tests?
  - Should prediction models evaluate implantation conditional on transfer occurring, or evaluate cumulative intention-to-treat cycle success?

### 3. Clinical Endpoint and Follow-Up Period
- **Context:** Exactly 8 cycles exhibited positive serum β-HCG titers (35.0 to 2,100.0 mIU/mL) yet are assigned `Output == 0` (Rows 876, 878, 1298, 1846, 1923, 3939, 4040, 4849).
- **Specific Questions:**
  - Do these 8 discordant cycles represent biochemical pregnancy loss (spontaneous decline in β-HCG without gestational sac formation), ectopic pregnancy, miscarriage, or recording discrepancies?
  - What was the formal follow-up duration for each cycle (e.g. 14 days, 6 weeks, or until delivery)?

### 4. AMH Measurement Units and Laboratory Assay Platform
- **Context:** Anti-Müllerian Hormone (`AMH`) values in the clean dataset range from 0.0 to 482.1.
- **Specific Questions:**
  - What are the units of measurement for AMH in this dataset (ng/mL vs pmol/L vs arbitrary laboratory units)?
  - What automated immunoassay platform was utilized (e.g. Roche Elecsys, Beckman Coulter Access, DSL ELISA)?
  - If units are ng/mL, values above 50-100 ng/mL are physiologically extraordinary even in extreme polycystic ovary syndrome (PCOS). What explains values up to 482.1?

### 5. Decryption of the 182 Treatment Protocol Identifiers
- **Context:** The feature `Medicines and treatments` contains 182 distinct integer identifiers (ranging from 1 to 183).
- **Specific Questions:**
  - What is the clinical mapping dictionary linking each integer identifier to specific pharmaceutical protocols?
  - Do these codes represent ovarian stimulation protocols (e.g. GnRH antagonist, long agonist, short flare, progestin-primed, mild IVF), gonadotropin formulations/dosages (rFSH, hMG), ovulation trigger agents (rhCG vs GnRH agonist), or luteal phase support regimens?

### 6. Availability Timing of Sperm Measurements and Treatment Protocols
- **Context:** Predictive scenarios require strict temporal feature availability. Feature availability cannot be assumed based on column names alone.
- **Specific Questions:**
  - Are `Sperm count`, `Sperm motility`, and `Sperm morphology` baseline diagnostic semen analysis parameters obtained during initial fertility workup, or are they measurements from the fresh semen sample produced and processed on the day of oocyte retrieval?
  - What scoring system was applied for `Sperm morphology` (values range strictly from 0.0 to 3.0: strict Kruger criteria percentage, WHO categories, or a 0-3 ordinal tier)?
  - Was `Medicines and treatments` recorded at initial baseline prescription (pre-stimulation), or does it document the actual regimen administered, adjusted, or finalized throughout stimulation?

### 7. Patient Linkage, Repeated Cycles, and Clustered Observations
- **Context:** The dataset contains 5,000 records without patient identifiers. Multi-cycle patients are common in ART clinics.
- **Specific Questions:**
  - Do the 5,000 records represent 5,000 unique patients, or do certain patients contribute multiple treatment cycles?
  - Can an anonymized patient ID or cycle sequence number be provided?
  - In the absence of patient IDs, repeated-cycle data leakage across train and test partitions cannot be completely eliminated, and patient-level generalization cannot be claimed.