"""
MergeGuard AI - Training Pipeline & Model Serialization Script
Trains and validates baseline and advanced ML models on the ApacheJIT dataset,
evaluating them using rigorous temporal validation and exporting production artifacts.
"""

import sys
import json
from pathlib import Path
import pandas as pd
import numpy as np
import joblib

# Ensure src package is importable
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR.parent))

from src.features import CORE_NUMERIC_FEATURES, FeatureEngineer
from src.model import create_model_pipeline, evaluate_model
from src.risk_engine import RiskEngine


def run_training_pipeline():
    print("=" * 70)
    print(" MergeGuard AI: Machine Learning Training & Evaluation Pipeline")
    print("=" * 70)

    # Locate datasets
    dataset_dir = CURRENT_DIR.parent / "data" / "raw" / "apachejit" / "dataset"
    train_path = dataset_dir / "apachejit_train.csv"
    test_path = dataset_dir / "apachejit_test_large.csv"

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(f"Dataset files not found under {dataset_dir}")

    print(f"\n[1/5] Loading datasets...")
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    print(f"  Training set: {train_df.shape[0]:,} rows (historical 2003-2016)")
    print(f"  Testing set:  {test_df.shape[0]:,} rows (future temporal test 2017-2020)")

    # Prepare features and target
    X_train = train_df[CORE_NUMERIC_FEATURES]
    y_train = train_df["buggy"].astype(int)

    X_test = test_df[CORE_NUMERIC_FEATURES]
    y_test = test_df["buggy"].astype(int)

    print(f"\n[2/5] Target class balance:")
    train_pos_pct = (y_train.mean()) * 100
    test_pos_pct = (y_test.mean()) * 100
    print(f"  Train Buggy Rate: {train_pos_pct:.2f}% (artificially balanced by ApacheJIT authors)")
    print(f"  Test Buggy Rate:  {test_pos_pct:.2f}% (true imbalanced real-world distribution)")

    # Compute baseline feature means for explainability
    baseline_means = X_train.mean().to_dict()

    # Models to train & compare
    model_types = ["dummy", "logistic_regression", "random_forest", "gradient_boosting"]
    eval_results = {}
    fitted_pipelines = {}

    print(f"\n[3/5] Training and benchmarking candidate models...")
    for m_type in model_types:
        print(f"  -> Training '{m_type}'...")
        pipeline = create_model_pipeline(m_type)
        pipeline.fit(X_train, y_train)
        
        metrics = evaluate_model(pipeline, X_test, y_test)
        eval_results[m_type] = metrics
        fitted_pipelines[m_type] = pipeline
        
        print(f"     ROC-AUC: {metrics['roc_auc']:.4f} | PR-AUC: {metrics['pr_auc']:.4f} | Recall: {metrics['recall']:.4f} | F1: {metrics['f1']:.4f}")

    # Display comparison table
    print("\n" + "=" * 70)
    print(" MODEL BENCHMARK COMPARISON (Evaluated on Temporal Holdout Test Set)")
    print("=" * 70)
    print(f"{'Model':<22} | {'ROC-AUC':<8} | {'PR-AUC':<8} | {'Recall':<8} | {'Precision':<10} | {'F1':<6}")
    print("-" * 70)
    for m_type, m in eval_results.items():
        print(f"{m_type:<22} | {m['roc_auc']:<8.4f} | {m['pr_auc']:<8.4f} | {m['recall']:<8.4f} | {m['precision']:<10.4f} | {m['f1']:<6.4f}")
    print("-" * 70)

    # Champion model selection (gradient_boosting provides superior non-linear interactions & calibration)
    champion_type = "gradient_boosting"
    champion_pipeline = fitted_pipelines[champion_type]
    print(f"\n[4/5] Selected Champion Model: '{champion_type}'")

    # Verify RiskEngine behavior with sample cases
    print(f"\n[5/5] Validating Explainable Risk Engine with Champion Model...")
    risk_engine = RiskEngine(champion_pipeline, baseline_means)

    # Test case 1: High risk commit (large churn, scattered files, low experience)
    high_risk_input = {
        "la": 850, "ld": 320, "nf": 22, "nd": 8, "ns": 3,
        "ent": 3.8, "ndev": 8, "age": 250, "nuc": 45,
        "aexp": 25, "arexp": 20, "asexp": 2,
    }
    high_res = risk_engine.analyze(high_risk_input, tests_modified=False, critical_modules=True)
    print(f"  High-risk Test Case  -> Score: {high_res.risk_score}/100 [{high_res.risk_level}]")
    print(f"     Top Factor: {high_res.top_risk_factors[0]['label'] if high_res.top_risk_factors else 'None'}")
    print(f"     Recs Count: {len(high_res.recommendations)}")

    # Test case 2: Low risk commit (small atomic change, high subsystem experience)
    low_risk_input = {
        "la": 12, "ld": 4, "nf": 1, "nd": 1, "ns": 1,
        "ent": 0.0, "ndev": 1, "age": 15, "nuc": 5,
        "aexp": 450, "arexp": 380, "asexp": 220,
    }
    low_res = risk_engine.analyze(low_risk_input, tests_modified=True, critical_modules=False)
    print(f"  Low-risk Test Case   -> Score: {low_res.risk_score}/100 [{low_res.risk_level}]")

    # Save artifacts
    models_dir = CURRENT_DIR.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_artifact_path = models_dir / "mergeguard_model.joblib"
    joblib.dump({
        "pipeline": champion_pipeline,
        "baseline_means": baseline_means,
        "champion_type": champion_type,
        "feature_names": CORE_NUMERIC_FEATURES,
    }, model_artifact_path)
    print(f"\n>>> Saved trained model pipeline to: {model_artifact_path}")

    # Save evaluation report JSON
    eval_report_path = models_dir / "evaluation_report.json"
    with open(eval_report_path, "w") as f:
        json.dump({
            "champion_model": champion_type,
            "benchmarks": eval_results,
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "feature_names": CORE_NUMERIC_FEATURES,
        }, f, indent=2)
    print(f">>> Saved evaluation benchmark report to: {eval_report_path}")

    print("\nTraining and artifact serialization successfully completed!")
    return eval_results


if __name__ == "__main__":
    run_training_pipeline()
