# Clinical Dataset Acquisition & Integrity Guide

This directory (`data/raw/`) is designated for the local placement of the primary clinical dataset files. In accordance with clinical data governance and licensing protocols, **raw clinical data files are strictly excluded from version control and never committed to this repository**.

---

## 1. Source Provenance & Acquisition

Download the official **Version 1** release of the dataset from Mendeley Data:

- **Reference Citation:** Maghdid, S., Rashid, T. A., & Askar, S. (2026). *Comprehensive Dataset Profile of In Vitro Fertilization (IVF) Clinical and Embryological Data*. Mendeley Data, Version 1. [DOI: 10.17632/hd8yy6gzc5.1](https://doi.org/10.17632/hd8yy6gzc5.1).
- **Direct Repository Link:** [https://data.mendeley.com/datasets/hd8yy6gzc5/1](https://data.mendeley.com/datasets/hd8yy6gzc5/1)
- **Licence:** Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
- **Licence Precaution:** A subsequent Version 2 record was published under CC BY-NC-ND 4.0. This research was developed against **Version 1** (CC BY 4.0). Confirm you are using Version 1.

---

## 2. Expected Files & Placement

Place the downloaded files into this directory:

```text
data/raw/
├── Dataset Clean.xlsx      # Authoritative clinical source (5,002 rows, 21 columns)
├── Normalized CSV.csv      # Min-max normalized derivative (5,000 rows, 21 columns)
└── README.md               # This acquisition guide
```

---

## 3. Cryptographic Verification & File Integrity

Before executing the analytical pipeline, verify the integrity of the downloaded files using SHA-256 checksums:

| File Name | File Size (Bytes) | Exact Row Count | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `Dataset Clean.xlsx` | 586,814 | 5,002 rows | `8914bf7a331c01bc1c66eeb81bf405b3476da3d80674536385a166f5d52dbf32` |
| `Normalized CSV.csv` | 874,985 | 5,001 rows | `fdda6c56c8ac3f66e8981685fa8732b9aaa57818f39e53325463a5e6c0acabc0` |

### Verification Command (PowerShell)
```powershell
Get-FileHash "data/raw/Dataset Clean.xlsx" -Algorithm SHA256
Get-FileHash "data/raw/Normalized CSV.csv" -Algorithm SHA256
```

### Verification Command (Linux / macOS)
```bash
sha256sum "data/raw/Dataset Clean.xlsx"
sha256sum "data/raw/Normalized CSV.csv"
```

---

## 4. Preprocessing & Modelling Governance Note

1. **Authoritative Source:** The analytical pipeline operates exclusively on `Dataset Clean.xlsx`.
2. **Synthetic Boundary Row Exclusion:** In Phase 1 dataset reconciliation, rows 5000 and 5001 of `Dataset Clean.xlsx` were identified as synthetic Min-Max normalization boundary rows injected during upstream preparation. The pipeline automatically filters these two rows, yielding exactly **5,000 clean clinical cycle records** (indices 0 to 4999).
3. **Bar on Normalized CSV:** `Normalized CSV.csv` is used strictly in Phase 1 reconciliation for data audit and is barred from predictive modelling to avoid learning from synthetic extrema.
