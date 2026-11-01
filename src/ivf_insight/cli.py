import argparse
import json
from pathlib import Path
from .io import load_table
from .analysis import data_quality_report, descriptive_summary
from .modeling import train_and_evaluate
from .statistics import univariate_associations


from .reconciliation import DatasetReconciler
from .governance import run_governance_pipeline
from .eda import run_eda_pipeline
from .experiments import run_predictive_experiments
from .validation import run_robustness_pipeline


def main():
    parser = argparse.ArgumentParser(prog="ivf-insight", description="IVF clinical dataset analysis and baseline modelling")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "analyze", "train"):
        p = sub.add_parser(name)
        p.add_argument("--input", required=True, help="Path to CSV or XLSX")
        if name != "inspect":
            p.add_argument("--target", required=True, help="Exact outcome column name")
            p.add_argument("--output-dir", default="data/processed")
        if name == "train":
            p.add_argument("--positive-label", default=None)
            p.add_argument("--drop-columns", nargs="*", default=[])

    p_rec = sub.add_parser("reconcile", help="Reconcile raw Excel and normalized CSV datasets")
    p_rec.add_argument("--excel", default="data/raw/Dataset Clean.xlsx", help="Path to raw Excel file")
    p_rec.add_argument("--csv", default="data/raw/Normalized CSV.csv", help="Path to normalized CSV file")
    p_rec.add_argument("--output-dir", default="reports", help="Directory for reconciliation reports")

    p_gov = sub.add_parser("governance", help="Generate feature governance registry and research design document")
    p_gov.add_argument("--output-dir", default="reports", help="Directory for governance outputs")

    p_eda = sub.add_parser("eda", help="Run Phase 3 exploratory data analysis and generate reports/figures")
    p_eda.add_argument("--excel", default="data/raw/Dataset Clean.xlsx", help="Path to authoritative Excel dataset")
    p_eda.add_argument("--output-dir", default="reports", help="Directory for reports and figures")

    p_exp = sub.add_parser("experiment", help="Run Phase 4 predictive experiments across scenarios and cohorts")
    p_exp.add_argument("--excel", default="data/raw/Dataset Clean.xlsx", help="Path to authoritative Excel dataset")
    p_exp.add_argument("--output-dir", default="reports", help="Directory for reports and figures")
    p_exp.add_argument("--models-dir", default="models", help="Directory for saved model pipelines")

    p_val = sub.add_parser("validate", help="Run Phase 5 robustness, sensitivity, and calibration audit")
    p_val.add_argument("--excel", default="data/raw/Dataset Clean.xlsx", help="Path to authoritative Excel dataset")
    p_val.add_argument("--output-dir", default="reports", help="Directory for validation reports")
    p_val.add_argument("--figures-dir", default="reports/robustness_figures", help="Directory for diagnostic figures")

    p_aud = sub.add_parser("audit", help="Run Phase 5.1 statistical integrity and interpretation audit")
    p_aud.add_argument("--excel", default="data/raw/Dataset Clean.xlsx", help="Path to authoritative Excel dataset")
    p_aud.add_argument("--output-dir", default="reports", help="Directory for audit reports")
    p_aud.add_argument("--figures-dir", default="reports/robustness_figures", help="Directory for diagnostic figures")

    p_rep = sub.add_parser("report", help="Compile comprehensive academic research report (Markdown, HTML, and PDF)")
    p_rep.add_argument("--output-dir", default="reports", help="Directory containing report templates and output deliverables")

    args = parser.parse_args()

    if args.command == "report":
        from .report import compile_research_report
        res = compile_research_report(args.output_dir)
        print(json.dumps(res, indent=2))
        return

    if args.command in ("audit", "integrity"):
        from .integrity_audit import run_statistical_integrity_pipeline
        results = run_statistical_integrity_pipeline(args.excel, args.output_dir, args.figures_dir)
        print(json.dumps({
            "status": "success",
            "report": str(results["report"]),
            "figures_count": len(results["figures"]),
            "hypotheses_rows": len(results["hypotheses"]),
            "age_progression_rows": len(results["age_progression"]),
            "lr_diagnostics_rows": len(results["lr_diagnostics"]),
            "calibration_audit_rows": len(results["calibration_audit"]),
            "feature_definitions_rows": len(results["feature_definitions"]),
        }, indent=2))
        return

    if args.command in ("validate", "robustness"):
        results = run_robustness_pipeline(args.excel, args.output_dir, args.figures_dir)
        print(json.dumps({
            "status": "success",
            "report": str(results["report"]),
            "figures_count": len(results["figures"]),
            "yearly_drift_rows": len(results["yearly_drift"]),
            "feature_drift_rows": len(results["feature_drift"]),
            "cutoff_sensitivity_rows": len(results["cutoff_sensitivity"]),
            "odds_ratios_rows": len(results["odds_ratios"]),
            "calibration_rows": len(results["calibration"]),
            "feature_stability_rows": len(results["feature_stability"]),
            "sensitivity_rows": len(results["sensitivity"]),
            "thresholds_rows": len(results["thresholds"]),
        }, indent=2))
        return

    if args.command == "experiment":
        results = run_predictive_experiments(args.excel, args.output_dir, args.models_dir)
        print(json.dumps(results, indent=2, default=str))
        return

    if args.command == "eda":
        results = run_eda_pipeline(args.excel, args.output_dir)
        print(json.dumps(results, indent=2, default=str))
        return

    if args.command == "governance":
        results = run_governance_pipeline(args.output_dir)
        print(json.dumps({
            "status": "success",
            "feature_governance_csv": results["feature_governance_csv"],
            "research_design_md": results["research_design_md"],
            "research_questions_md": results["research_questions_md"],
            "total_patient_records": results["total_patient_records"],
        }, indent=2))
        return

    if args.command == "reconcile":
        reconciler = DatasetReconciler(args.excel, args.csv)
        results = reconciler.run_and_save(args.output_dir)
        print(json.dumps(results["summary"], indent=2))
        return


    df = load_table(args.input)
    if args.command == "inspect":
        # Print schema and aggregate quality metadata only. Avoid dumping patient-level
        # rows into terminals, logs, or screenshots that may later be shared.
        print(json.dumps({
            "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "missing_values": {c: int(v) for c, v in df.isna().sum().items()},
            "unique_values": {c: int(df[c].nunique(dropna=True)) for c in df.columns},
        }, indent=2, default=str))
    elif args.command == "analyze":
        out = Path(args.output_dir)
        report = data_quality_report(df, args.target, out)
        descriptive_summary(df, out)
        univariate_associations(df, args.target, out / "univariate_associations.csv")
        print(json.dumps(report, indent=2))
    elif args.command == "train":
        result = train_and_evaluate(df, args.target, args.output_dir, args.drop_columns, args.positive_label)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

