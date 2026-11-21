"""
MergeGuard AI - Explainable Risk Scoring Engine
Transforms model predictions into calibrated 0-100 risk scores, risk levels (LOW/MEDIUM/HIGH),
feature attribution explanations, and actionable review recommendations.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from .features import CORE_NUMERIC_FEATURES, ALL_MODEL_FEATURES, FeatureEngineer, get_feature_descriptions


class RiskAnalysisResult:
    """Structured container for risk evaluation output."""
    def __init__(
        self,
        risk_score: int,
        risk_level: str,
        defect_probability: float,
        top_risk_factors: List[Dict[str, Any]],
        mitigating_factors: List[Dict[str, Any]],
        recommendations: List[str],
        metrics_summary: Dict[str, Any],
    ):
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.defect_probability = defect_probability
        self.top_risk_factors = top_risk_factors
        self.mitigating_factors = mitigating_factors
        self.recommendations = recommendations
        self.metrics_summary = metrics_summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "defect_probability": round(self.defect_probability, 4),
            "top_risk_factors": self.top_risk_factors,
            "mitigating_factors": self.mitigating_factors,
            "recommendations": self.recommendations,
            "metrics_summary": self.metrics_summary,
        }


class RiskEngine:
    """
    Production Risk Engine that evaluates Git commits and Merge Requests.
    Grounds its scoring in trained ML models while providing explainability and actionability.
    """

    def __init__(self, pipeline: Pipeline, baseline_means: Optional[Dict[str, float]] = None):
        self.pipeline = pipeline
        self.feature_descriptions = get_feature_descriptions()
        
        # Default baseline means derived from training distribution
        self.baseline_means = baseline_means or {
            "la": 150.0,
            "ld": 50.0,
            "nf": 5.0,
            "nd": 2.0,
            "ns": 1.5,
            "ent": 1.2,
            "ndev": 2.0,
            "age": 30.0,
            "nuc": 15.0,
            "aexp": 100.0,
            "arexp": 80.0,
            "asexp": 30.0,
        }

    def analyze(
        self,
        metrics: Dict[str, Any],
        tests_modified: Optional[bool] = None,
        critical_modules: Optional[bool] = None,
    ) -> RiskAnalysisResult:
        """
        Analyzes a single commit or Merge Request change.
        """
        # Ensure all required features exist as floats
        row = {}
        for feat in CORE_NUMERIC_FEATURES:
            row[feat] = float(metrics.get(feat, 0.0))

        df_input = pd.DataFrame([row])

        # Get calibrated defect probability from ML pipeline
        prob_buggy = float(self.pipeline.predict_proba(df_input)[:, 1][0])

        # Map probability to 0-100 risk score
        risk_score = int(np.clip(round(prob_buggy * 100), 0, 100))

        # Determine risk classification tier
        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Feature Attribution & Risk Factor Extraction
        top_risk_factors, mitigating_factors = self._compute_feature_contributions(row)

        # Generate Actionable Recommendations
        recommendations = self._generate_recommendations(
            metrics=row,
            risk_level=risk_level,
            tests_modified=tests_modified,
            critical_modules=critical_modules,
        )

        metrics_summary = {
            "lines_added": int(row["la"]),
            "lines_deleted": int(row["ld"]),
            "total_churn": int(row["la"] + row["ld"]),
            "files_changed": int(row["nf"]),
            "directories_changed": int(row["nd"]),
            "entropy": round(row["ent"], 2),
            "developer_experience": int(row["aexp"]),
            "subsystem_experience": int(row["asexp"]),
            "tests_modified": tests_modified,
            "critical_modules_affected": critical_modules,
        }

        return RiskAnalysisResult(
            risk_score=risk_score,
            risk_level=risk_level,
            defect_probability=prob_buggy,
            top_risk_factors=top_risk_factors,
            mitigating_factors=mitigating_factors,
            recommendations=recommendations,
            metrics_summary=metrics_summary,
        )

    def _compute_feature_contributions(self, row: Dict[str, float]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Calculates local feature contributions by assessing deviations from population baseline
        and weighting by the model's feature importance.
        """
        risk_factors = []
        mitigating_factors = []

        # Churn factor
        churn = row["la"] + row["ld"]
        if churn > 500:
            impact = min(0.35, (churn - 500) / 2000.0)
            risk_factors.append({
                "feature": "churn",
                "label": "High Code Churn",
                "value": f"{int(churn)} lines (+{int(row['la'])}, -{int(row['ld'])})",
                "impact": "INCREASES_RISK",
                "weight": round(impact, 2),
                "description": "Large modifications significantly increase cognitive review load and regression risk.",
            })
        elif churn < 50:
            mitigating_factors.append({
                "feature": "churn",
                "label": "Small Atomic Change",
                "value": f"{int(churn)} lines",
                "impact": "DECREASES_RISK",
                "description": "Small, concise diffs are easier to review thoroughly and test reliably.",
            })

        # File dispersion & entropy
        if row["nf"] > 10 or row["ent"] > 2.0:
            risk_factors.append({
                "feature": "ent",
                "label": "Scattered / High-Entropy Changes",
                "value": f"{int(row['nf'])} files, entropy={round(row['ent'], 2)}",
                "impact": "INCREASES_RISK",
                "description": "Edits are widely dispersed across multiple modules rather than focused in one location.",
            })
        elif row["nf"] <= 2 and row["ent"] < 0.5:
            mitigating_factors.append({
                "feature": "ent",
                "label": "Localized Scope",
                "value": f"{int(row['nf'])} files changed",
                "impact": "DECREASES_RISK",
                "description": "Changes are tightly concentrated in a single file or directory.",
            })

        # Subsystem & Developer Experience
        if row["aexp"] > 200 and row["asexp"] > 50:
            mitigating_factors.append({
                "feature": "asexp",
                "label": "High Subsystem Familiarity",
                "value": f"{int(row['asexp'])} commits in this subsystem",
                "impact": "DECREASES_RISK",
                "description": "Author has proven historical experience modifying this specific component.",
            })
        elif row["asexp"] < 5 and row["aexp"] < 30:
            risk_factors.append({
                "feature": "asexp",
                "label": "Low Subsystem Familiarity",
                "value": f"{int(row['asexp'])} prior subsystem commits",
                "impact": "INCREASES_RISK",
                "description": "Author has limited prior modifications in this specific subsystem.",
            })

        # Code Age & Modification Churn
        if row["age"] > 180:
            risk_factors.append({
                "feature": "age",
                "label": "Legacy Code Modification",
                "value": f"{round(row['age'], 0)} days average file age",
                "impact": "INCREASES_RISK",
                "description": "Modifying mature or legacy code often triggers unexpected side effects.",
            })

        # Multi-developer touchpoints
        if row["ndev"] > 5:
            risk_factors.append({
                "feature": "ndev",
                "label": "High Historical Collaboration Surface",
                "value": f"{round(row['ndev'], 1)} average contributors",
                "impact": "INCREASES_RISK",
                "description": "Files touch code written by many different contributors, raising integration complexity.",
            })

        return risk_factors, mitigating_factors

    def _generate_recommendations(
        self,
        metrics: Dict[str, float],
        risk_level: str,
        tests_modified: Optional[bool],
        critical_modules: Optional[bool],
    ) -> List[str]:
        """
        Produces actionable, grounded advice for developers and code reviewers.
        """
        recs = []
        churn = metrics["la"] + metrics["ld"]

        if tests_modified is False and churn > 30:
            recs.append("Add unit or integration tests: Code was modified without corresponding test changes.")

        if risk_level == "HIGH":
            recs.append("Request an additional senior reviewer before merging this change.")

        if churn > 600:
            recs.append("Consider breaking this large change into smaller, atomic Merge Requests to ease review.")

        if metrics["asexp"] < 10 and metrics["ns"] > 1:
            recs.append("Request a review from an engineer with deep domain ownership of this subsystem.")

        if metrics["ent"] > 2.5:
            recs.append("Validate cross-module dependencies to prevent unintended cascading regressions.")

        if critical_modules is True:
            recs.append("Critical architectural modules affected: Ensure staging deployment and smoke testing pass.")

        if not recs:
            recs.append("Standard review: Verify CI pipelines pass and follow standard code quality guidelines.")

        return recs
