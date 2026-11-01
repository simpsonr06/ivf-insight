"""Feature governance, prediction scenario definitions, and research design layer for IVF Insight.

This module enforces strict clinical and temporal separation of predictors,
prevents target leakage (e.g. β-HCG), manages chronological validation splitting,
and generates the authoritative feature governance registry and research design document.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .io import load_table


class PredictionScenario(str, Enum):
    """IVF Prediction scenarios based on clinical process stages."""
    SCENARIO_A = "baseline"  # Pre-stimulation
    SCENARIO_B = "post_retrieval"  # Post-retrieval / Fertilization
    SCENARIO_C = "post_embryo_development"  # Post-embryo development (pre-transfer)


@dataclass(frozen=True)
class FeatureSpecification:
    """Governance record for an individual feature."""
    original_name: str
    standardized_name: str
    data_type: str
    clinical_interpretation: str
    ivf_process_stage: str
    potential_availability_at_prediction_time: str
    scenario_a_decision: str  # Included / Excluded
    scenario_b_decision: str  # Included / Excluded
    scenario_c_decision: str  # Included / Excluded
    reason_for_decision: str
    unresolved_documentation_requirements: str


# Authoritative feature specifications registry
FEATURE_SPECIFICATIONS: List[FeatureSpecification] = [
    FeatureSpecification(
        original_name="Female Age",
        standardized_name="female_age",
        data_type="integer",
        clinical_interpretation="Age of female partner at initiation of treatment cycle (years).",
        ivf_process_stage="Baseline (Pre-stimulation)",
        potential_availability_at_prediction_time="Available at all prediction timepoints.",
        scenario_a_decision="Included",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Primary known biological determinant of oocyte quality and aneuploidy risk; available pre-stimulation.",
        unresolved_documentation_requirements="None; standard demographic variable in years (range: 20-49).",
    ),
    FeatureSpecification(
        original_name="Number of attempts",
        standardized_name="number_of_attempts",
        data_type="integer",
        clinical_interpretation="Historical count of previous or current assisted reproductive treatment attempts.",
        ivf_process_stage="Baseline (Pre-stimulation)",
        potential_availability_at_prediction_time="Available at all prediction timepoints.",
        scenario_a_decision="Included",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Clinical prognostic marker of past cycle failure or success; available at baseline.",
        unresolved_documentation_requirements="Author clarification needed on whether '1' denotes first cycle (0 prior) or 1 prior failed cycle. Typographical artifact '`1' must be sanitized to 1.",
    ),
    FeatureSpecification(
        original_name="AMH",
        standardized_name="amh",
        data_type="float",
        clinical_interpretation="Anti-Müllerian Hormone; endocrine biomarker of ovarian functional reserve.",
        ivf_process_stage="Baseline (Pre-stimulation)",
        potential_availability_at_prediction_time="Available at all prediction timepoints.",
        scenario_a_decision="Included",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Standard clinical biomarker reflecting follicular pool and stimulation responsiveness.",
        unresolved_documentation_requirements="Measurement unit and assay method require author confirmation (typical ng/mL vs pmol/L; extreme values up to 482.1 require clinical contextualization).",
    ),
    FeatureSpecification(
        original_name="Medicines and treatments",
        standardized_name="treatment_protocol_id",
        data_type="categorical (integer ID)",
        clinical_interpretation="Nominal identifier representing clinical ovarian stimulation regimen and medication protocol.",
        ivf_process_stage="Baseline / Protocol Selection (Pre-stimulation)",
        potential_availability_at_prediction_time="Presumed available pre-stimulation IF representing planned protocol; UNCERTAIN if recording actual administered medications, adjustments, or trigger protocol.",
        scenario_a_decision="Conditional / Presumed Planned Protocol (Categorical)",
        scenario_b_decision="Included (Categorical)",
        scenario_c_decision="Included (Categorical)",
        reason_for_decision="Clinical protocol prescribes stimulation strategy, but actual administered medications/adjustments occur throughout stimulation. Included conditionally in Scenario A only under the assumption of planned protocol; if author confirms it reflects post-stimulation administered treatment, it must be deferred to Scenario B.",
        unresolved_documentation_requirements="High-priority author clarification needed: Does this code record the initial planned protocol prescribed before stimulation, or actual medications/doses administered throughout the cycle? Missing mapping dictionary for the 182 integer codes (1-183).",
    ),
    FeatureSpecification(
        original_name="Egg retrieval date",
        standardized_name="egg_retrieval_date",
        data_type="datetime",
        clinical_interpretation="Calendar timestamp when oocyte pick-up (OPU) aspiration procedure was performed.",
        ivf_process_stage="Retrieval (Procedure Date)",
        potential_availability_at_prediction_time="Available post-retrieval; procedure schedule known shortly before.",
        scenario_a_decision="Excluded (Reserved for Validation)",
        scenario_b_decision="Excluded (Reserved for Validation)",
        scenario_c_decision="Excluded (Reserved for Validation)",
        reason_for_decision="Procedure date should not be a direct predictor to prevent overfitting to calendar artifacts. Reserved for prospective chronological train/test splitting.",
        unresolved_documentation_requirements="Time-of-day information not recorded; date format spans 2019-01-02 to 2025-06-30 across 1,400 distinct dates.",
    ),
    FeatureSpecification(
        original_name="Oocyte Maturity MII",
        standardized_name="oocyte_maturity_mii",
        data_type="integer",
        clinical_interpretation="Count of Metaphase II oocytes (extruded first polar body; nuclear mature and fertilizable).",
        ivf_process_stage="Post-Retrieval (Oocyte Morphology)",
        potential_availability_at_prediction_time="Available post-retrieval on Day 0.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Only observable after oocyte denudation and laboratory microscopic grading; unavailable prior to stimulation.",
        unresolved_documentation_requirements="Confirmation needed whether denudation was performed for ICSI alone or also for conventional IVF cycles.",
    ),
    FeatureSpecification(
        original_name="Oocyte Maturity MI",
        standardized_name="oocyte_maturity_mi",
        data_type="integer",
        clinical_interpretation="Count of Metaphase I oocytes (intermediate nuclear maturity, no polar body, no germinal vesicle).",
        ivf_process_stage="Post-Retrieval (Oocyte Morphology)",
        potential_availability_at_prediction_time="Available post-retrieval on Day 0.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Laboratory embryology finding post-retrieval; represents cycle cohort maturation efficiency.",
        unresolved_documentation_requirements="None; integer count (range: 0-32).",
    ),
    FeatureSpecification(
        original_name="Oocyte Maturity others",
        standardized_name="oocyte_maturity_others",
        data_type="integer",
        clinical_interpretation="Count of other retrieved oocytes (germinal vesicle [GV], atretic, degenerated, or fractured zona).",
        ivf_process_stage="Post-Retrieval (Oocyte Morphology)",
        potential_availability_at_prediction_time="Available post-retrieval on Day 0.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Laboratory post-retrieval metric reflecting oocyte dysmaturity or degeneration.",
        unresolved_documentation_requirements="Author clarification needed on the proportion of GV vs degenerated oocytes grouped in this category.",
    ),
    FeatureSpecification(
        original_name="Male Age",
        standardized_name="male_age",
        data_type="integer",
        clinical_interpretation="Age of male partner / sperm provider at treatment cycle (years).",
        ivf_process_stage="Baseline (Pre-stimulation)",
        potential_availability_at_prediction_time="Available at all prediction timepoints.",
        scenario_a_decision="Included",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Biological factor influencing sperm DNA fragmentation, blastocyst formation, and paternal contribution.",
        unresolved_documentation_requirements="None; integer demographic variable (range: 19-57).",
    ),
    FeatureSpecification(
        original_name="Sperm count",
        standardized_name="sperm_count",
        data_type="float",
        clinical_interpretation="Sperm concentration from diagnostic / semen analysis.",
        ivf_process_stage="Baseline / Andrology (Pre-stimulation vs Retrieval Day)",
        potential_availability_at_prediction_time="Presumed available pre-stimulation IF diagnostic baseline; UNCERTAIN if retrieval-day post-wash sample.",
        scenario_a_decision="Conditional / Presumed Baseline Diagnostic",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Standard male factor evaluation occurs at baseline, but semen is also collected and processed on oocyte retrieval day. Included conditionally in Scenario A under diagnostic assumption; if retrieval-day sample, belongs in Scenario B.",
        unresolved_documentation_requirements="High-priority author clarification needed: Does this represent pre-cycle diagnostic semen analysis or retrieval-day fresh sample? Units assumed million/mL.",
    ),
    FeatureSpecification(
        original_name="Sperm motility",
        standardized_name="sperm_motility",
        data_type="float",
        clinical_interpretation="Percentage of motile spermatozoa in semen sample (%).",
        ivf_process_stage="Baseline / Andrology (Pre-stimulation vs Retrieval Day)",
        potential_availability_at_prediction_time="Presumed available pre-stimulation IF diagnostic baseline; UNCERTAIN if retrieval-day post-wash sample.",
        scenario_a_decision="Conditional / Presumed Baseline Diagnostic",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Functional sperm parameter reflecting sample vitality. Included conditionally in Scenario A under diagnostic assumption; if measured on retrieval day, belongs in Scenario B.",
        unresolved_documentation_requirements="High-priority author clarification needed: Diagnostic baseline vs retrieval day; total motility (PR + NP) vs progressive motility (PR) alone.",
    ),
    FeatureSpecification(
        original_name="Sperm morphology",
        standardized_name="sperm_morphology",
        data_type="float",
        clinical_interpretation="Normal sperm morphology assessment score or percentage.",
        ivf_process_stage="Baseline / Andrology (Pre-stimulation vs Retrieval Day)",
        potential_availability_at_prediction_time="Presumed available pre-stimulation IF diagnostic baseline; UNCERTAIN if retrieval-day sample.",
        scenario_a_decision="Conditional / Presumed Baseline Diagnostic",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="Standard diagnostic morphological indicator of teratozoospermia. Included conditionally in Scenario A under diagnostic assumption; if retrieval day, belongs in Scenario B.",
        unresolved_documentation_requirements="High-priority author clarification needed: Diagnostic baseline vs retrieval day; values strictly range 0.0 to 3.0 (strict Kruger % vs ordinal 0-3 grading scale).",
    ),
    FeatureSpecification(
        original_name="Number of fertilized eggs",
        standardized_name="number_of_fertilized_eggs",
        data_type="integer",
        clinical_interpretation="Count of normally fertilized oocytes displaying two pronuclei (2PN) 16-18 hours post-insemination.",
        ivf_process_stage="Post-Retrieval (Fertilization Check Day 1)",
        potential_availability_at_prediction_time="Available on Day 1 post-retrieval.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Included",
        scenario_c_decision="Included",
        reason_for_decision="First developmental milestone indicating fertilization success; unavailable prior to retrieval.",
        unresolved_documentation_requirements="Confirmation whether 1PN or multipronuclear (>=3PN) abnormal zygotes are excluded (standard 2PN assumed).",
    ),
    FeatureSpecification(
        original_name="Embryo Grade 1",
        standardized_name="embryo_grade_1_count",
        data_type="integer",
        clinical_interpretation="Count of high-quality (Grade 1) embryos during developmental culture.",
        ivf_process_stage="Post-Embryo-Development (Embryo Culture)",
        potential_availability_at_prediction_time="Available on Day 3 or Day 5 post-retrieval.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Excluded",
        scenario_c_decision="Included",
        reason_for_decision="Reflects cleavage / blastocyst morphological top quality; unavailable at baseline or Day 1.",
        unresolved_documentation_requirements="Exact laboratory morphological scoring system (Gardner vs Veeck / Istanbul consensus cleavage criteria) requires author documentation.",
    ),
    FeatureSpecification(
        original_name="Embryo Grade 2",
        standardized_name="embryo_grade_2_count",
        data_type="integer",
        clinical_interpretation="Count of fair-quality (Grade 2) embryos during developmental culture.",
        ivf_process_stage="Post-Embryo-Development (Embryo Culture)",
        potential_availability_at_prediction_time="Available on Day 3 or Day 5 post-retrieval.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Excluded",
        scenario_c_decision="Included",
        reason_for_decision="Embryology culture morphological metric; unavailable earlier.",
        unresolved_documentation_requirements="Laboratory scoring tier definitions require documentation.",
    ),
    FeatureSpecification(
        original_name="Embryo Grade 3",
        standardized_name="embryo_grade_3_count",
        data_type="integer",
        clinical_interpretation="Count of poor-quality (Grade 3) embryos during developmental culture.",
        ivf_process_stage="Post-Embryo-Development (Embryo Culture)",
        potential_availability_at_prediction_time="Available on Day 3 or Day 5 post-retrieval.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Excluded",
        scenario_c_decision="Included",
        reason_for_decision="Embryology culture morphological metric; unavailable earlier.",
        unresolved_documentation_requirements="Laboratory scoring tier definitions require documentation.",
    ),
    FeatureSpecification(
        original_name="Embryo Grade 4",
        standardized_name="embryo_grade_4_count",
        data_type="integer",
        clinical_interpretation="Count of severely fragmented / arrested (Grade 4) embryos.",
        ivf_process_stage="Post-Embryo-Development (Embryo Culture)",
        potential_availability_at_prediction_time="Available on Day 3 or Day 5 post-retrieval.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Excluded",
        scenario_c_decision="Included",
        reason_for_decision="Embryology culture morphological metric; unavailable earlier.",
        unresolved_documentation_requirements="Laboratory scoring tier definitions require documentation.",
    ),
    FeatureSpecification(
        original_name="Number of embryos",
        standardized_name="number_of_embryos",
        data_type="integer",
        clinical_interpretation="Total count of viable cleaved embryos / blastocysts obtained in the cycle.",
        ivf_process_stage="Post-Embryo-Development (Embryo Culture Summary)",
        potential_availability_at_prediction_time="Available on day of planned embryo transfer.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Excluded",
        scenario_c_decision="Included",
        reason_for_decision="Summary measure of embryonic yield available immediately prior to transfer decision.",
        unresolved_documentation_requirements="Relationship with sum of individual grades requires documentation (in 1,250 cases with non-return, value is 0).",
    ),
    FeatureSpecification(
        original_name="frezzing",
        standardized_name="cryopreserved_embryos_count",
        data_type="integer",
        clinical_interpretation="Count of surplus or electively cryopreserved (vitrified) embryos.",
        ivf_process_stage="Post-Embryo-Development (Cryopreservation)",
        potential_availability_at_prediction_time="Decided concurrently with fresh embryo transfer or freeze-all strategy.",
        scenario_a_decision="Excluded",
        scenario_b_decision="Excluded",
        scenario_c_decision="Included",
        reason_for_decision="Embryology disposition decision reflecting overall surplus embryo cohort quality.",
        unresolved_documentation_requirements="Spelling in source is 'frezzing'; author clarification needed whether vitrification occurred on Day 3, Day 5, or both.",
    ),
    FeatureSpecification(
        original_name="β-HCG",
        standardized_name="beta_hcg_post_transfer",
        data_type="string / float (qualitative & quantitative)",
        clinical_interpretation="Serum beta-human chorionic gonadotropin measured 10-14 days post-embryo transfer.",
        ivf_process_stage="Post-Outcome / Luteal Phase (10-14 days post-transfer)",
        potential_availability_at_prediction_time="Unavailable at any pre-transfer prediction timepoint.",
        scenario_a_decision="EXCLUDED (TARGET LEAKAGE)",
        scenario_b_decision="EXCLUDED (TARGET LEAKAGE)",
        scenario_c_decision="EXCLUDED (TARGET LEAKAGE)",
        reason_for_decision="Measured weeks after embryo transfer; represents direct biological target leakage. Including it invalidates prospective clinical prediction.",
        unresolved_documentation_requirements="Qualitative strings ('Non-return of embryos', 'NEGATIVE', 'POSITIVE') and numeric titers are blended; contains 8 discordant records relative to outcome.",
    ),
    FeatureSpecification(
        original_name="Output(failed implantation or successful implantation)",
        standardized_name="recorded_cycle_outcome",
        data_type="binary (0 / 1)",
        clinical_interpretation="Recorded binary cycle outcome in dataset (0 = negative outcome / no viable implantation, 1 = positive outcome). Critical clinical note: Class 0 combines cycles without embryo transfer (1,250 records with 'Non-return of embryos'), completed transfers with negative pregnancy tests (1,250 records with 'NEGATIVE'), and 8 positive β-HCG cases with non-progressing implantation. Must NOT be referred to uniformly as 'implantation failure' because implantation was impossible in cycles lacking embryo transfer.",
        ivf_process_stage="Target Endpoint (Post-transfer outcome)",
        potential_availability_at_prediction_time="Dependent variable / Ground truth target.",
        scenario_a_decision="TARGET (Dependent Variable: recorded_cycle_outcome)",
        scenario_b_decision="TARGET (Dependent Variable: recorded_cycle_outcome)",
        scenario_c_decision="TARGET (Dependent Variable: recorded_cycle_outcome)",
        reason_for_decision="Ground truth binary label for predictive models. Retains original binary values (0/1) but designated as 'recorded_cycle_outcome' until dataset authors confirm the exact clinical definition (biochemical vs clinical pregnancy vs ongoing pregnancy).",
        unresolved_documentation_requirements="High-priority author clarification needed: What is the exact clinical definition of outcome 1? Does it represent biochemical pregnancy, ultrasound gestational sac at 5-7 weeks, fetal heartbeat, or live birth? Why are non-transferred cycles (Non-return of embryos) grouped together with post-transfer negative tests in Class 0?",
    ),
]



class FeatureGovernanceRegistry:
    """Manages feature registry, scenario mappings, and validation checks."""

    def __init__(self, specs: Optional[List[FeatureSpecification]] = None):
        self.specs = specs or FEATURE_SPECIFICATIONS
        self._by_orig = {s.original_name: s for s in self.specs}
        self._by_std = {s.standardized_name: s for s in self.specs}

    def to_dataframe(self) -> pd.DataFrame:
        """Convert registry to a structured DataFrame for reporting."""
        rows = []
        for s in self.specs:
            rows.append({
                "Original feature name": s.original_name,
                "Standardised feature name": s.standardized_name,
                "Data type": s.data_type,
                "Clinical interpretation": s.clinical_interpretation,
                "IVF process stage": s.ivf_process_stage,
                "Potential availability at prediction time": s.potential_availability_at_prediction_time,
                "Scenario A (Baseline) decision": s.scenario_a_decision,
                "Scenario B (Post-Retrieval) decision": s.scenario_b_decision,
                "Scenario C (Post-Embryo) decision": s.scenario_c_decision,
                "Reason for decision": s.reason_for_decision,
                "Unresolved documentation requirements": s.unresolved_documentation_requirements,
            })
        return pd.DataFrame(rows)

    def export_csv(self, output_path: str | Path) -> None:
        """Export feature governance registry to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.to_dataframe().to_csv(output_path, index=False, encoding="utf-8")

    def get_candidate_predictors(
        self,
        scenario: PredictionScenario | str,
        include_conditional: bool = True,
    ) -> List[str]:
        """Return approved original feature names for a given prediction scenario.
        
        Args:
            scenario: PredictionScenario enum or string representation.
            include_conditional: If True, includes features whose timing is plausible but
                subject to unresolved documentation (e.g. treatment protocol as planned
                protocol; sperm measurements as baseline diagnostic). If False, restricts
                strictly to confirmed pre-stimulation features.
        """
        val = scenario.value.lower() if isinstance(scenario, Enum) else str(scenario).lower()
        name = scenario.name.lower() if isinstance(scenario, Enum) else str(scenario).lower()
        
        candidates = []
        for s in self.specs:
            if s.original_name in ["β-HCG", "Output(failed implantation or successful implantation)", "Egg retrieval date"]:
                continue
            
            # Scenario A: Baseline
            if "baseline" in val or "scenario_a" in name or "scenario a" in val:
                dec = s.scenario_a_decision.lower()
                if "included" in dec and "conditional" not in dec:
                    candidates.append(s.original_name)
                elif include_conditional and "conditional" in dec:
                    candidates.append(s.original_name)
            # Scenario B: Post-Retrieval
            elif "retrieval" in val or "scenario_b" in name or "scenario b" in val:
                dec = s.scenario_b_decision.lower()
                if "included" in dec or (include_conditional and "conditional" in dec):
                    candidates.append(s.original_name)
            # Scenario C: Post-Embryo-Development
            elif "embryo" in val or "scenario_c" in name or "scenario c" in val:
                dec = s.scenario_c_decision.lower()
                if "included" in dec or (include_conditional and "conditional" in dec):
                    candidates.append(s.original_name)
        return candidates

    def validate_feature_set(self, scenario: PredictionScenario | str, features: List[str]) -> Tuple[bool, List[str]]:
        """Strictly validate that no leaked or unauthorized features are present."""
        violations = []

        # 1. Zero tolerance for β-HCG in any scenario
        for f in features:
            f_norm = f.strip().lower()
            if "hcg" in f_norm:
                violations.append(f"CRITICAL LEAKAGE: β-HCG feature '{f}' present in scenario '{scenario}'.")

        # 2. Check stage authorization against candidate features
        approved = set(self.get_candidate_predictors(scenario, include_conditional=True))
        for f in features:
            if f not in approved:
                violations.append(f"UNAUTHORIZED FEATURE: '{f}' is not approved for scenario '{scenario}'.")

        return (len(violations) == 0, violations)



class TargetProvenanceAuditor:
    """Analyzes relationship between β-HCG, non-return of embryos, and target outcome."""

    @staticmethod
    def audit(df: pd.DataFrame) -> Dict[str, Any]:
        target_col = "Output(failed implantation or successful implantation)"
        beta_col = "β-HCG"

        # Categorize β-HCG
        def categorize(val: Any) -> str:
            s = str(val).strip()
            if s.lower() == "non-return of embryos":
                return "Non-return of embryos"
            if s.upper() == "NEGATIVE":
                return "NEGATIVE (unquantified)"
            if "positive" in s.lower() or "postive" in s.lower():
                return "POSITIVE"
            if "negative" in s.lower():
                return "NEGATIVE (titer)"
            return "OTHER"

        beta_cat = df[beta_col].apply(categorize)
        crosstab = pd.crosstab(beta_cat, df[target_col], dropna=False).to_dict()

        # Parse numeric beta values
        def extract_num(val: Any) -> float:
            s = str(val).strip()
            m = re.search(r"(\d+(?:\.\d+)?)", s)
            return float(m.group(1)) if m else np.nan

        nums = df[beta_col].apply(extract_num)

        # Discordant cases: Positive beta with target 0
        pos_mask = beta_cat == "POSITIVE"
        target_zero_mask = df[target_col] == 0.0
        discordant_indices = df[pos_mask & target_zero_mask].index.tolist()
        discordant_details = []
        for idx in discordant_indices:
            discordant_details.append({
                "index": int(idx),
                "female_age": int(df.loc[idx, "Female Age"]),
                "date": str(df.loc[idx, "Egg retrieval date"]),
                "raw_beta": str(df.loc[idx, beta_col]),
                "parsed_num": float(nums.loc[idx]),
                "target": float(df.loc[idx, target_col]),
            })

        class_0_total = int((df[target_col] == 0.0).sum())
        non_return_count = int((beta_cat == "Non-return of embryos").sum())
        neg_beta_count = int((beta_cat.isin(["NEGATIVE (titer)", "NEGATIVE (unquantified)"])).sum())
        discordant_pos_count = len(discordant_details)

        class_1_total = int((df[target_col] == 1.0).sum())
        pos_beta_outcome_1_count = int(((beta_cat == "POSITIVE") & (df[target_col] == 1.0)).sum())

        return {
            "target_variable_standardized": "recorded_cycle_outcome",
            "target_distribution": {str(k): int(v) for k, v in df[target_col].value_counts().items()},
            "class_0_total": class_0_total,
            "class_0_subcohorts": {
                "cycles_without_embryo_transfer": {
                    "count": non_return_count,
                    "proportion_of_class_0": round(non_return_count / class_0_total, 4) if class_0_total else 0,
                    "target_zero_rate": float((df.loc[beta_cat == "Non-return of embryos", target_col] == 0.0).mean()) if non_return_count else 0.0,
                    "clinical_status": "No embryo transfer performed (cancellation / total fertilization failure / freeze-all); implantation biologically impossible.",
                },
                "cycles_with_negative_pregnancy_test": {
                    "count": neg_beta_count,
                    "proportion_of_class_0": round(neg_beta_count / class_0_total, 4) if class_0_total else 0,
                    "target_zero_rate": float((df.loc[beta_cat.isin(["NEGATIVE (titer)", "NEGATIVE (unquantified)"]), target_col] == 0.0).mean()) if neg_beta_count else 0.0,
                    "clinical_status": "Completed embryo transfer with negative post-transfer β-HCG; true negative cycle outcome.",
                },
                "cycles_with_discordant_positive_beta": {
                    "count": discordant_pos_count,
                    "proportion_of_class_0": round(discordant_pos_count / class_0_total, 4) if class_0_total else 0,
                    "samples": discordant_details,
                    "clinical_status": "Biochemical pregnancy loss or non-progressing implantation (positive β-HCG titer 35-2,100 mIU/mL but outcome 0).",
                },
            },
            "class_1_total": class_1_total,
            "class_1_subcohorts": {
                "cycles_with_positive_pregnancy_test": {
                    "count": pos_beta_outcome_1_count,
                    "proportion_of_class_1": round(pos_beta_outcome_1_count / class_1_total, 4) if class_1_total else 0,
                    "clinical_status": "Completed embryo transfer with positive post-transfer β-HCG titer; clinical vs biochemical vs live birth endpoint unconfirmed.",
                },
            },
            "beta_category_crosstab": crosstab,
            "non_return_cycles_total": non_return_count,
            "non_return_target_zero_rate": float((df.loc[beta_cat == "Non-return of embryos", target_col] == 0.0).mean()) if non_return_count else 0.0,
            "negative_beta_cycles_total": neg_beta_count,
            "negative_beta_target_zero_rate": float((df.loc[beta_cat.isin(["NEGATIVE (titer)", "NEGATIVE (unquantified)"]), target_col] == 0.0).mean()) if neg_beta_count else 0.0,
            "positive_beta_cycles_total": int((beta_cat == "POSITIVE").sum()),
            "positive_beta_target_one_rate": float((df.loc[beta_cat == "POSITIVE", target_col] == 1.0).mean()) if (beta_cat == "POSITIVE").sum() else 0.0,
            "discordant_positive_beta_target_zero_count": discordant_pos_count,
            "discordant_positive_beta_target_zero_samples": discordant_details,
            "clinical_uncertainty_statement": (
                "The target variable 'recorded_cycle_outcome' must NOT be termed uniformly as 'implantation failure' "
                "for Class 0. Exactly 1,250 cycles had no embryo transfer ('Non-return of embryos') and therefore "
                "implantation was biologically impossible. Furthermore, 8 cycles achieved biochemical hCG positivity "
                "yet were classified as 0, clinically consistent with biochemical pregnancy loss prior to clinical pregnancy confirmation. "
                "Until confirmed by dataset authors, the clinical endpoint remains uncertain between biochemical "
                "pregnancy, ultrasound-confirmed gestational sac, and live birth."
            ),
        }


class ChronologicalValidationManager:
    """Manages prospective chronological partitioning using egg retrieval dates with strict integrity safeguards."""

    DEFAULT_CUTOFF = "2024-01-01"

    @classmethod
    def split(cls, df: pd.DataFrame, cutoff: str = DEFAULT_CUTOFF) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        # 1. Safeguard: Valid retrieval dates
        if "Egg retrieval date" not in df.columns:
            raise KeyError("Missing required column 'Egg retrieval date'.")

        dates = pd.to_datetime(df["Egg retrieval date"], errors="coerce")
        if dates.isna().any():
            invalid_count = int(dates.isna().sum())
            raise ValueError(f"Chronological split failed: {invalid_count} records contain missing or invalid 'Egg retrieval date'.")

        cutoff_dt = pd.to_datetime(cutoff)

        train_mask = dates < cutoff_dt
        test_mask = dates >= cutoff_dt

        train_df = df[train_mask].copy()
        test_df = df[test_mask].copy()

        # 2. Safeguard: No future records enter training set
        if len(train_df) > 0 and train_df["Egg retrieval date"].max() >= cutoff_dt:
            raise ValueError("Partition integrity violation: Training partition contains records on or after cutoff date.")

        # 3. Safeguard: No training records occur on or after test cutoff
        if len(test_df) > 0 and test_df["Egg retrieval date"].min() < cutoff_dt:
            raise ValueError("Partition integrity violation: Test partition contains records before cutoff date.")

        # 4. Safeguard: Reported sample counts match actual partitions
        if len(train_df) + len(test_df) != len(df):
            raise ValueError("Partition integrity violation: Partition sizes do not sum to total dataset size.")

        target_col = "Output(failed implantation or successful implantation)"

        # 5. Safeguard: Class distributions calculated separately for each partition
        if target_col in train_df.columns and len(train_df) > 0:
            train_class_counts = {int(k): int(v) for k, v in train_df[target_col].value_counts().items()}
            train_class_props = {int(k): round(float(v), 4) for k, v in train_df[target_col].value_counts(normalize=True).items()}
            train_pos_rate = round(float(train_df[target_col].mean()), 4)
        else:
            train_class_counts, train_class_props, train_pos_rate = {}, {}, 0.0

        if target_col in test_df.columns and len(test_df) > 0:
            test_class_counts = {int(k): int(v) for k, v in test_df[target_col].value_counts().items()}
            test_class_props = {int(k): round(float(v), 4) for k, v in test_df[target_col].value_counts(normalize=True).items()}
            test_pos_rate = round(float(test_df[target_col].mean()), 4)
        else:
            test_class_counts, test_class_props, test_pos_rate = {}, {}, 0.0

        meta = {
            "cutoff_date": cutoff,
            "total_records": len(df),
            "train_size": len(train_df),
            "train_proportion": round(len(train_df) / len(df), 4),
            "train_date_range": [str(train_df["Egg retrieval date"].min()), str(train_df["Egg retrieval date"].max())] if len(train_df) > 0 else [],
            "train_class_counts": train_class_counts,
            "train_class_proportions": train_class_props,
            "train_positive_rate": train_pos_rate,
            "test_size": len(test_df),
            "test_proportion": round(len(test_df) / len(df), 4),
            "test_date_range": [str(test_df["Egg retrieval date"].min()), str(test_df["Egg retrieval date"].max())] if len(test_df) > 0 else [],
            "test_class_counts": test_class_counts,
            "test_class_proportions": test_class_props,
            "test_positive_rate": test_pos_rate,
            "patient_identity_notice": (
                "NO CLAIM OF PATIENT-LEVEL SEPARATION. Partitions are separated strictly by cycle retrieval timestamp, "
                "not verified patient identity, because patient identifiers are omitted from the source dataset."
            ),
            "repeated_cycle_leakage_warning": (
                "Repeated-cycle data leakage cannot be completely ruled out without patient identifiers. "
                "Although prospective chronological splitting prevents future cycles from leaking into past training data, "
                "the presence of repeated cycles from the same patient across the cutoff boundary (e.g. initial cycle in 2023, "
                "subsequent cycle in 2024) remains possible due to unlinked patient observations."
            ),
            "temporal_drift_notes": (
                "Historical training spans 2019-2023; prospective test spans 2024-2025. "
                f"Notice empirical positive rate in training is {train_pos_rate*100:.1f}% vs {test_pos_rate*100:.1f}% in prospective testing, "
                "reflecting real clinical practice drift that would be masked by random K-fold splitting."
            ),
        }
        return train_df, test_df, meta


def load_authoritative_clean_data(excel_path: str | Path) -> pd.DataFrame:
    """Load authoritative Excel dataset, dropping boundary rows and sanitizing attempts."""
    raw_df = load_table(excel_path)
    # Exclude the 2 synthetic boundary rows at the tail
    df = raw_df.iloc[:5000].copy()

    # Sanitize 'Number of attempts' typographical backtick artifact
    df["Number of attempts"] = pd.to_numeric(
        df["Number of attempts"].astype(str).str.replace("`", "", regex=False).str.strip(),
        errors="coerce",
    )
    # Ensure egg retrieval date is datetime
    df["Egg retrieval date"] = pd.to_datetime(df["Egg retrieval date"])
    return df


def generate_research_design_report(
    output_path: str | Path,
    registry: FeatureGovernanceRegistry,
    target_audit: Dict[str, Any],
    validation_meta: Dict[str, Any],
) -> None:
    """Generate comprehensive research design document in Markdown."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scen_a_all = registry.get_candidate_predictors(PredictionScenario.SCENARIO_A, include_conditional=True)
    scen_a_strict = registry.get_candidate_predictors(PredictionScenario.SCENARIO_A, include_conditional=False)
    scen_b = registry.get_candidate_predictors(PredictionScenario.SCENARIO_B)
    scen_c = registry.get_candidate_predictors(PredictionScenario.SCENARIO_C)

    md = []
    md.append("# IVF Insight: Clinical Predictive Modeling Research Design & Feature Governance")
    md.append("\n**Author:** Senior Biomedical Data Scientist & Research Engineer")
    md.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("**Source Dataset:** `data/raw/Dataset Clean.xlsx` (5,000 authoritative patient treatment cycles)\n")
    md.append("---\n")

    md.append("## 1. Research Question & Clinical Purpose\n")
    md.append(
        "**Primary Research Question:** Can baseline clinical, laboratory, and embryological features available "
        "at distinct treatment milestones accurately classify IVF cycle outcomes (`recorded_cycle_outcome`) in a published, "
        "de-identified patient cohort without relying on post-outcome target leakage?\n"
    )
    md.append(
        "**Clinical Context & Non-Claim Notice:** Assisted reproductive technology (ART) involves sequential "
        "decision points across ovarian stimulation, egg retrieval, and embryo culture. This research formalizes "
        "predictive capability at each distinct milestone as an educational portfolio project. It is **not** a clinical "
        "decision support tool, medical device, or basis for clinical management. No claim of clinical validity is made.\n"
    )

    md.append("## 2. Intended Prediction Population & Observation Rules\n")
    md.append("- **Cohort Size:** Exactly 5,000 complete patient treatment cycles.")
    md.append("- **Authoritative Source:** `data/raw/Dataset Clean.xlsx` (rows 0 to 4,999).")
    md.append("- **Exclusion Rules:** Rows 5,000 and 5,001 are synthetic Min-Max boundary rows and are strictly excluded.")
    md.append("- **Normalization Rule:** Preprocessed `Normalized CSV.csv` is completely barred from model development due to calendar year stripping, encoding corruption, and baked-in leakage.")
    md.append("- **Observation Preservation:** All 5,000 candidate records are retained without automated filtering or record deletion.\n")

    md.append("## 3. Prediction Scenarios & Temporal Feature Governance\n")
    md.append(
        "To reflect realistic clinical practice, feature availability is governed strictly by the IVF timeline. "
        "No future information is permitted in earlier prediction scenarios. Feature availability is never assumed "
        "based solely on column names.\n"
    )

    md.append("### Scenario A: Baseline Prediction (Pre-Stimulation)")
    md.append("- **Prediction Timepoint:** Consultation prior to the initiation of controlled ovarian hyperstimulation (COH).")
    md.append("- **Clinical Utility:** Initial prognosis estimation, couple counseling, and stimulation protocol personalization.")
    md.append(f"- **Strictly Confirmed Pre-Stimulation Features ({len(scen_a_strict)} features):** `{', '.join(scen_a_strict)}`.")
    md.append(
        f"- **Candidate Baseline Features Including Conditional ({len(scen_a_all)} features):** `{', '.join(scen_a_all)}`.\n"
        "  - *Timing Caveat 1 (`Medicines and treatments`):* Included conditionally only under the assumption of **planned stimulation protocol**. If this feature records medications/doses actually administered or adjusted during stimulation, it is not available pre-stimulation and must be deferred to Scenario B.\n"
        "  - *Timing Caveat 2 (`Sperm count`, `Sperm motility`, `Sperm morphology`):* Included conditionally under the assumption of **baseline diagnostic semen analysis** (pre-treatment workup). If these represent retrieval-day fresh ejaculate/post-wash parameters, they belong strictly in Scenario B."
    )
    md.append("- **Excluded Predictors:** All retrieval parameters, fertilization metrics, embryo grading scores, and post-transfer tests.\n")

    md.append("### Scenario B: Post-Retrieval Prediction")
    md.append("- **Prediction Timepoint:** Day 1 post-oocyte pick-up (OPU), following nuclear maturity grading and fertilization check.")
    md.append("- **Clinical Utility:** Mid-cycle assessment to guide decisions regarding extended blastocyst culture vs early Day 3 transfer.")
    md.append(f"- **Candidate Predictors ({len(scen_b)} features):** `{', '.join(scen_b)}`.")
    md.append("- **Additional Features:** `Oocyte Maturity MII`, `Oocyte Maturity MI`, `Oocyte Maturity others`, `Number of fertilized eggs`.")
    md.append("- **Excluded Predictors:** Cleavage / blastocyst morphological scores, embryo counts, freezing count, and post-transfer tests.\n")

    md.append("### Scenario C: Post-Embryo-Development Prediction")
    md.append("- **Prediction Timepoint:** Immediately prior to embryo transfer (Day 3 or Day 5).")
    md.append("- **Clinical Utility:** Final pre-transfer prognosis estimation, supporting elective single embryo transfer (eSET) vs freezing decisions.")
    md.append(f"- **Candidate Predictors ({len(scen_c)} features):** `{', '.join(scen_c)}`.")
    md.append("- **Additional Features:** `Embryo Grade 1`, `Embryo Grade 2`, `Embryo Grade 3`, `Embryo Grade 4`, `Number of embryos`, `frezzing`.")
    md.append("- **Excluded Predictors:** Post-transfer tests (`β-HCG`).\n")

    md.append("## 4. Target Provenance & Biological Validation\n")
    md.append("- **Standardized Target Name:** `recorded_cycle_outcome` (Dataset Header: `Output(failed implantation or successful implantation)`).")
    md.append("- **Original Binary Values:** Preserved exactly as recorded (`0.0` and `1.0`).")
    md.append(f"- **Recorded Target Distribution:** Class 0 = {target_audit['class_0_total']} ({target_audit['class_0_total']/5000*100:.2f}%); Class 1 = {target_audit['class_1_total']} ({target_audit['class_1_total']/5000*100:.2f}%).")
    md.append("\n**Clinical Distinction Across Target Sub-Cohorts:**")
    md.append(
        "> [!IMPORTANT]\n"
        "> **Do NOT call every Class 0 record an 'implantation failure'.** Implantation requires intrauterine embryo transfer. "
        "In cycles where no embryos were transferred, implantation was biologically impossible.\n"
    )
    md.append(
        f"1. **Cycles without Embryo Transfer (N = {target_audit['non_return_cycles_total']}, 25.0% of cohort):** "
        "Records with `β-HCG == 'Non-return of embryos'`. All map to **Class 0 (100%)**. These represent cycle cancellations, "
        "total fertilization failure, embryo developmental arrest, or freeze-all cycles without fresh transfer. Implantation was never attempted."
    )
    md.append(
        f"2. **Cycles with Completed Transfer & Negative Pregnancy Test (N = {target_audit['negative_beta_cycles_total']}, 25.0% of cohort):** "
        "Records with qualitative or quantitative negative β-HCG (`NEGATIVE`). All map to **Class 0 (100%)**. These represent true biological negative cycle outcomes."
    )
    md.append(
        f"3. **Cycles with Positive Pregnancy Test & Recorded Class 1 (N = 2,492, 49.84% of cohort):** "
        "Records with positive β-HCG titers (14 to 14,589 mIU/mL) mapping to **Class 1 (100%)**."
    )
    md.append(
        f"4. **Discordant Positive β-HCG with Recorded Class 0 (N = {target_audit['discordant_positive_beta_target_zero_count']}, 0.16% of cohort):** "
        "Exactly 8 treatment cycles (Rows 876, 878, 1298, 1846, 1923, 3939, 4040, 4849) had positive β-HCG titers (35 to 2,100 mIU/mL) "
        "yet were classified as **Class 0**."
    )
    md.append("\n**Biochemical Pregnancy vs Clinical Pregnancy Uncertainty:**")
    md.append(
        "In reproductive endocrinology, trophoblastic secretion of β-HCG indicates **biochemical pregnancy**, whereas **clinical pregnancy** "
        "requires ultrasound visualization of an intrauterine gestational sac with embryonic heartbeat at 5-7 weeks of gestation. "
        "Between 10% and 20% of biochemical pregnancies arrest before ultrasound confirmation (biochemical pregnancy loss / non-progressing implantation). "
        "The 8 discordant cases in this dataset are clinically consistent with biochemical pregnancy loss. However, because the dataset authors "
        "did not document whether Class 1 reflects biochemical pregnancy, clinical pregnancy sac, or live birth, the exact clinical endpoint "
        "remains an unresolved research question."
    )

    md.append("\n## 5. Potential Leakage Pathways & Prohibited Practices\n")
    md.append("> [!CAUTION]")
    md.append("> **PROHIBITED FEATURE: β-HCG is strictly banned from all prediction models.**\n")
    md.append("1. **Post-Outcome Leakage:** Serum β-HCG is measured 10-14 days after embryo transfer. Its inclusion in baseline or pre-transfer models represents catastrophic target leakage.")
    md.append("2. **Global Preprocessing Leakage:** Min-Max scaling or imputation fitted on the entire dataset prior to train/test partitioning leaks distribution statistics. All transformations must be encapsulated inside cross-validation folds.")
    md.append("3. **Protocol Categorical Misuse:** `Medicines and treatments` (182 discrete regimen IDs) must never be scaled continuously; it must be treated as a categorical feature.")
    md.append("4. **Synthetic Boundary Leakage:** Excel rows 5000 and 5001 must be dropped before any processing.\n")

    md.append("## 6. Validation Strategy: Prospective Chronological vs Random Splitting\n")
    md.append("### Limitations of Standard Random K-Fold Splitting")
    md.append("1. **Longitudinal Clustered Leakage:** 1,457 potential repeat-cycle clusters (3,058 cycles) exist in the data. Random splitting distributes cycles from the same couple across train and test folds, artificially inflating accuracy.")
    md.append("2. **Temporal Inversion:** Random splitting trains on future cycles (2024-2025) to predict past cycles (2019), violating clinical causality.")
    md.append("3. **Masked Cohort Drift:** Empirical positive rates vary substantially over time (from 35.9% in 2020 to 60.7% in 2024). Random splitting homogenizes these distributions, hiding vulnerability to real practice changes.")

    md.append("\n### Approved Validation Protocol: Prospective Chronological Partition")
    md.append(f"- **Partition Cutoff Date:** `{validation_meta['cutoff_date']}`")
    md.append(f"- **Development Set (Historical):** {validation_meta['train_size']} cycles ({validation_meta['train_proportion']*100:.1f}%), spanning `{validation_meta['train_date_range'][0]}` to `{validation_meta['train_date_range'][1]}`.")
    md.append(f"  - **Train Class Distribution:** Class 0 = {validation_meta['train_class_counts'].get(0, 0)} ({validation_meta['train_class_proportions'].get(0, 0)*100:.1f}%), Class 1 = {validation_meta['train_class_counts'].get(1, 0)} ({validation_meta['train_class_proportions'].get(1, 0)*100:.1f}%).")
    md.append(f"- **Prospective Test Set (Future):** {validation_meta['test_size']} cycles ({validation_meta['test_proportion']*100:.1f}%), spanning `{validation_meta['test_date_range'][0]}` to `{validation_meta['test_date_range'][1]}`.")
    md.append(f"  - **Test Class Distribution:** Class 0 = {validation_meta['test_class_counts'].get(0, 0)} ({validation_meta['test_class_proportions'].get(0, 0)*100:.1f}%), Class 1 = {validation_meta['test_class_counts'].get(1, 0)} ({validation_meta['test_class_proportions'].get(1, 0)*100:.1f}%).")
    md.append("- **Inner Cross-Validation:** 5-fold Stratified or Time-Series Split within the historical training partition only.")
    md.append(
        "\n> [!WARNING]\n"
        f"> **Patient Separation Notice:** {validation_meta['patient_identity_notice']}\n"
        f"> **Repeated-Cycle Leakage:** {validation_meta['repeated_cycle_leakage_warning']}\n"
    )

    md.append("## 7. Known Dataset Limitations & Unresolved Research Questions\n")
    md.append("The complete audit of unresolved clinical and technical questions for the dataset authors is documented in `reports/research_questions.md`.")

    output_path.write_text("\n".join(md), encoding="utf-8")


def generate_research_questions_document(output_path: str | Path) -> None:
    """Generate reports/research_questions.md containing unresolved author queries."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# IVF Insight: Unresolved Research & Clinical Governance Questions")
    md.append("\n**Author:** Senior Biomedical Data Scientist & Research Engineer")
    md.append(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    md.append("**Target Audience:** Original Dataset Authors / Clinical Investigators\n")
    md.append("---\n")

    md.append(
        "Before deploying predictive machine learning models or drawing clinical conclusions, "
        "the following seven unresolved research design and clinical definitions must be clarified "
        "by the dataset authors. In accordance with clinical data science best practices, "
        "missing clinical definitions must not be invented.\n"
    )

    md.append("### 1. Exact Definition of Implantation Success (Target Endpoint)")
    md.append(
        "- **Context:** The original binary target header is `Output(failed implantation or successful implantation)`. "
        "In reproductive medicine, implantation success can refer to:\n"
        "  1. *Biochemical pregnancy:* Serum β-HCG elevation (>10 or >25 mIU/mL) 12-14 days post-transfer.\n"
        "  2. *Clinical pregnancy:* Ultrasound visualization of an intrauterine gestational sac (with or without yolk sac/fetal pole) at 5-7 weeks of gestation.\n"
        "  3. *Ongoing pregnancy / Live birth:* Viable intrauterine pregnancy beyond 12 or 20 weeks, or delivery of a living infant.\n"
        "- **Specific Questions:**\n"
        "  - What exact clinical milestone constitutes `Output == 1` in this dataset?\n"
        "  - Was confirmation based solely on serum β-HCG or on subsequent transvaginal ultrasound?"
    )

    md.append("\n### 2. Clinical Meaning of Class 0 in Cycles Without Embryo Transfer")
    md.append(
        "- **Context:** Exactly 1,250 records (25.0% of the entire 5,000-cycle cohort) have `β-HCG == 'Non-return of embryos'` "
        "and are uniformly assigned `Output == 0`.\n"
        "- **Specific Questions:**\n"
        "  - Does `Non-return of embryos` denote cycles where no embryo transfer was performed (e.g. cycle cancellation due to poor ovarian response, total fertilization failure, complete embryo developmental arrest, elective freeze-all due to ovarian hyperstimulation syndrome [OHSS] risk, or pre-implantation genetic testing)?\n"
        "  - If no embryos were transferred into the uterine cavity, implantation was biologically impossible. Why are these cycles grouped into the same target class (`0`) as cycles with completed embryo transfer and negative pregnancy tests?\n"
        "  - Should prediction models evaluate implantation conditional on transfer occurring, or evaluate cumulative intention-to-treat cycle success?"
    )

    md.append("\n### 3. Clinical Endpoint and Follow-Up Period")
    md.append(
        "- **Context:** Exactly 8 cycles exhibited positive serum β-HCG titers (35.0 to 2,100.0 mIU/mL) yet are assigned `Output == 0` (Rows 876, 878, 1298, 1846, 1923, 3939, 4040, 4849).\n"
        "- **Specific Questions:**\n"
        "  - Do these 8 discordant cycles represent biochemical pregnancy loss (spontaneous decline in β-HCG without gestational sac formation), ectopic pregnancy, miscarriage, or recording discrepancies?\n"
        "  - What was the formal follow-up duration for each cycle (e.g. 14 days, 6 weeks, or until delivery)?"
    )

    md.append("\n### 4. AMH Measurement Units and Laboratory Assay Platform")
    md.append(
        "- **Context:** Anti-Müllerian Hormone (`AMH`) values in the clean dataset range from 0.0 to 482.1.\n"
        "- **Specific Questions:**\n"
        "  - What are the units of measurement for AMH in this dataset (ng/mL vs pmol/L vs arbitrary laboratory units)?\n"
        "  - What automated immunoassay platform was utilized (e.g. Roche Elecsys, Beckman Coulter Access, DSL ELISA)?\n"
        "  - If units are ng/mL, values above 50-100 ng/mL are physiologically extraordinary even in extreme polycystic ovary syndrome (PCOS). What explains values up to 482.1?"
    )

    md.append("\n### 5. Decryption of the 182 Treatment Protocol Identifiers")
    md.append(
        "- **Context:** The feature `Medicines and treatments` contains 182 distinct integer identifiers (ranging from 1 to 183).\n"
        "- **Specific Questions:**\n"
        "  - What is the clinical mapping dictionary linking each integer identifier to specific pharmaceutical protocols?\n"
        "  - Do these codes represent ovarian stimulation protocols (e.g. GnRH antagonist, long agonist, short flare, progestin-primed, mild IVF), gonadotropin formulations/dosages (rFSH, hMG), ovulation trigger agents (rhCG vs GnRH agonist), or luteal phase support regimens?"
    )

    md.append("\n### 6. Availability Timing of Sperm Measurements and Treatment Protocols")
    md.append(
        "- **Context:** Predictive scenarios require strict temporal feature availability. Feature availability cannot be assumed based on column names alone.\n"
        "- **Specific Questions:**\n"
        "  - Are `Sperm count`, `Sperm motility`, and `Sperm morphology` baseline diagnostic semen analysis parameters obtained during initial fertility workup, or are they measurements from the fresh semen sample produced and processed on the day of oocyte retrieval?\n"
        "  - What scoring system was applied for `Sperm morphology` (values range strictly from 0.0 to 3.0: strict Kruger criteria percentage, WHO categories, or a 0-3 ordinal tier)?\n"
        "  - Was `Medicines and treatments` recorded at initial baseline prescription (pre-stimulation), or does it document the actual regimen administered, adjusted, or finalized throughout stimulation?"
    )

    md.append("\n### 7. Patient Linkage, Repeated Cycles, and Clustered Observations")
    md.append(
        "- **Context:** The dataset contains 5,000 records without patient identifiers. Multi-cycle patients are common in ART clinics.\n"
        "- **Specific Questions:**\n"
        "  - Do the 5,000 records represent 5,000 unique patients, or do certain patients contribute multiple treatment cycles?\n"
        "  - Can an anonymized patient ID or cycle sequence number be provided?\n"
        "  - In the absence of patient IDs, repeated-cycle data leakage across train and test partitions cannot be completely eliminated, and patient-level generalization cannot be claimed."
    )

    output_path.write_text("\n".join(md), encoding="utf-8")


def run_governance_pipeline(output_dir: str | Path = "reports") -> Dict[str, Any]:
    """Execute complete governance pipeline and write feature governance CSV, research design MD, and research questions MD."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Feature governance registry
    registry = FeatureGovernanceRegistry()
    csv_path = out / "feature_governance.csv"
    registry.export_csv(csv_path)

    # 2. Load clean authoritative data
    excel_path = Path("data/raw/Dataset Clean.xlsx")
    df = load_authoritative_clean_data(excel_path)

    # 3. Target provenance audit
    target_audit = TargetProvenanceAuditor.audit(df)

    # 4. Chronological validation split metadata
    _, _, val_meta = ChronologicalValidationManager.split(df)

    # 5. Generate research design document
    md_path = out / "research_design.md"
    generate_research_design_report(md_path, registry, target_audit, val_meta)

    # 6. Generate research questions document
    questions_path = out / "research_questions.md"
    generate_research_questions_document(questions_path)

    return {
        "feature_governance_csv": str(csv_path),
        "research_design_md": str(md_path),
        "research_questions_md": str(questions_path),
        "total_patient_records": len(df),
        "target_audit": target_audit,
        "validation_metadata": val_meta,
    }

