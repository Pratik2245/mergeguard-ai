"""
MergeGuard AI - ML Service Layer
Bridges the trained Machine Learning pipeline and Risk Engine to the FastAPI REST layer.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import joblib

# Ensure ml-engine is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_ENGINE_PATH = PROJECT_ROOT / "ml-engine"
sys.path.insert(0, str(ML_ENGINE_PATH))

from src.risk_engine import RiskEngine, RiskAnalysisResult
from src.gitlab_extractor import parse_git_diff, build_feature_dict


class MLService:
    _instance: Optional["MLService"] = None

    def __init__(self):
        self.artifact_path = ML_ENGINE_PATH / "models" / "mergeguard_model.joblib"
        self.eval_report_path = ML_ENGINE_PATH / "models" / "evaluation_report.json"
        
        if not self.artifact_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {self.artifact_path}. Please run train.py first.")

        print(f"[MLService] Loading model artifact from: {self.artifact_path}")
        saved_data = joblib.load(self.artifact_path)
        self.pipeline = saved_data["pipeline"]
        self.baseline_means = saved_data.get("baseline_means", {})
        self.champion_type = saved_data.get("champion_type", "gradient_boosting")
        self.feature_names = saved_data.get("feature_names", [])

        self.risk_engine = RiskEngine(self.pipeline, self.baseline_means)

        self.benchmarks = {}
        if self.eval_report_path.exists():
            try:
                with open(self.eval_report_path, "r") as f:
                    self.benchmarks = json.load(f)
            except Exception as e:
                print(f"[MLService] Warning: Could not read evaluation report: {e}")

    @classmethod
    def get_instance(cls) -> "MLService":
        if cls._instance is None:
            cls._instance = MLService()
        return cls._instance

    def predict_direct(
        self,
        metrics: Dict[str, Any],
        tests_modified: Optional[bool] = None,
        critical_modules: Optional[bool] = None,
    ) -> RiskAnalysisResult:
        return self.risk_engine.analyze(
            metrics=metrics,
            tests_modified=tests_modified,
            critical_modules=critical_modules,
        )

    def predict_diff(
        self,
        diff_text: str,
        dev_metrics: Optional[Dict[str, float]] = None,
    ) -> tuple[RiskAnalysisResult, Dict[str, Any]]:
        diff_metrics = parse_git_diff(diff_text)
        feature_dict = build_feature_dict(diff_metrics, dev_metrics)

        analysis = self.risk_engine.analyze(
            metrics=feature_dict,
            tests_modified=diff_metrics.tests_modified,
            critical_modules=diff_metrics.critical_modules,
        )
        return analysis, diff_metrics.to_dict()

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_type": self.champion_type,
            "feature_count": len(self.feature_names),
            "features": self.feature_names,
            "benchmarks": self.benchmarks.get("benchmarks", {}),
            "trained_samples": self.benchmarks.get("train_samples", 44834),
            "test_samples": self.benchmarks.get("test_samples", 30111),
        }
