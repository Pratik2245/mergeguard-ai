"""
MergeGuard AI - Model Definitions, Training, and Evaluation Suite
Trains baseline and advanced classifiers, evaluating them on real-world temporal splits.
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
)

from .features import FeatureEngineer, ALL_MODEL_FEATURES


def create_model_pipeline(model_type: str = "gradient_boosting") -> Pipeline:
    """
    Constructs an end-to-end Scikit-Learn pipeline consisting of:
    1. Feature engineering (calculating domain metrics, churn ratios, log transforms)
    2. Optional standard scaling (required for linear models)
    3. The classifier (Dummy, Logistic Regression, Random Forest, or HistGradientBoosting)
    """
    engineer = FeatureEngineer()

    if model_type == "dummy":
        clf = DummyClassifier(strategy="prior")
        return Pipeline([
            ("engineer", engineer),
            ("clf", clf),
        ])

    elif model_type == "logistic_regression":
        scaler = StandardScaler()
        clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        return Pipeline([
            ("engineer", engineer),
            ("scaler", scaler),
            ("clf", clf),
        ])

    elif model_type == "random_forest":
        clf = RandomForestClassifier(
            n_estimators=120,
            max_depth=12,
            min_samples_leaf=15,
            class_weight="balanced",
            n_jobs=-1,
            random_state=42,
        )
        return Pipeline([
            ("engineer", engineer),
            ("clf", clf),
        ])

    elif model_type == "gradient_boosting":
        # Native LightGBM-style histogram gradient booster from scikit-learn
        clf = HistGradientBoostingClassifier(
            max_iter=160,
            learning_rate=0.07,
            max_depth=8,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=42,
        )
        return Pipeline([
            ("engineer", engineer),
            ("clf", clf),
        ])

    else:
        raise ValueError(f"Unknown model_type: {model_type}")


def evaluate_model(pipeline: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
    """
    Evaluates a trained model pipeline against ground truth test labels.
    Calculates comprehensive industry metrics: Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, and Confusion Matrix.
    """
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "pr_auc": float(average_precision_score(y_test, y_prob)),
        "brier_score": float(brier_score_loss(y_test, y_prob)),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
    }
