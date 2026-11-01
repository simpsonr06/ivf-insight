# Contributing to IVF Insight

Thank you for your interest in contributing to **IVF Insight**. This repository is an open-science, reproducible clinical data science and machine learning research project. 

To maintain scientific integrity, patient data privacy, and rigorous reproducibility, all contributors must adhere to the protocols outlined below.

---

## 1. Core Research Integrity Principles

All contributions must strictly respect our core research governance rules:

1. **Strict Data Protection:**
   - **NEVER** commit, stage, or share raw clinical data files (`Dataset Clean.xlsx`, `Normalized CSV.csv`, or any other patient records).
   - Ensure `data/raw/` remains excluded by `.gitignore`.
2. **Accurate Clinical Terminology:**
   - Always refer to the prediction endpoint as `recorded_cycle_outcome`.
   - **DO NOT** claim or imply that the outcome represents confirmed ongoing pregnancy or live birth.
   - Maintain the strict distinction between the **Full-Cycle Cohort** ($N=5,000$) and the **Embryo-Transfer Cohort** ($N=3,750$).
3. **No Unjustified Causal Claims:**
   - Observational associations and multivariable regression coefficients reflect statistical correlation, not biological causation.
   - Do not claim that clinical interventions or medication changes "caused" outcome differences without randomized experimental evidence.
4. **No Silent Modification of Empirical Results:**
   - Any modification to data reconciliation, feature governance, or model training must be accompanied by an update to test suites and analytical manifests.

---

## 2. Development Setup

### 2.1 Fork and Clone
```bash
git clone https://github.com/your-username/ivf-insight.git
cd ivf-insight
```

### 2.2 Environment Setup
```bash
python -m venv .venv
# Activate environment:
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux / macOS: source .venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

### 2.3 Verify Setup with Test Suite
```bash
python -m pytest -v
```
All 45 automated tests must pass before beginning new work.

---

## 3. Code Standards & Best Practices

- **Code Formatting:** Adhere to PEP 8 style conventions. Use meaningful variable names reflecting biomedical concepts.
- **Type Annotations:** Provide Python type hints on all public functions and class methods.
- **Docstrings:** Document all modules, classes, and functions using standard docstring formats (specifying parameters, return types, and exceptions).
- **Leakage Prevention:** All data transformations (imputation, scaling, one-hot encoding) must be fitted strictly inside training folds or pipelines (`sklearn.pipeline.Pipeline`).

---

## 4. Pull Request Workflow

1. Create a descriptive feature branch from `master`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Implement your changes with corresponding unit or regression tests under `tests/`.
3. Run the automated test suite and CLI verification:
   ```bash
   python -m pytest -v
   ivf-insight --help
   ```
4. Verify that no raw data or temporary files are staged:
   ```bash
   git status
   ```
5. Commit changes with clear, semantic commit messages:
   ```bash
   git commit -m "feat(validation): add bootstrap calibration confidence intervals"
   ```
6. Push to your fork and submit a Pull Request.

---

## 5. Security & Vulnerability Reporting

If you identify a data privacy vulnerability, potential patient re-identification risk, or security defect, please do not file a public issue. Contact the research repository maintainer directly or email the corresponding authors.
