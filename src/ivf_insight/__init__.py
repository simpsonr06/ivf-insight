"""IVF Insight: reproducible exploratory analysis and baseline modelling."""
from .reconciliation import DatasetReconciler
from .governance import (
    PredictionScenario,
    FeatureGovernanceRegistry,
    load_authoritative_clean_data,
    run_governance_pipeline,
)

__version__ = "0.1.0"
__all__ = [
    "DatasetReconciler",
    "PredictionScenario",
    "FeatureGovernanceRegistry",
    "load_authoritative_clean_data",
    "run_governance_pipeline",
]


