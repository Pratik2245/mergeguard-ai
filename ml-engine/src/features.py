"""
MergeGuard AI - Feature Engineering & Preprocessing Pipeline
Defines raw feature schemas, engineered features, and preprocessing transformations.
"""

from typing import List, Tuple, Dict, Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler


# 12 Core features from ApacheJIT commit metrics
CORE_NUMERIC_FEATURES: List[str] = [
    "la",     # lines added
    "ld",     # lines deleted
    "nf",     # number of files
    "nd",     # number of directories
    "ns",     # number of subsystems
    "ent",    # change entropy across files
    "ndev",   # developers modifying affected files
    "age",    # historical age of modified code (days)
    "nuc",    # number of unique prior changes
    "aexp",   # developer experience
    "arexp",  # developer recent experience
    "asexp",  # developer subsystem experience
]

# Engineered features added to capture domain-specific risk signals
ENGINEERED_FEATURES: List[str] = [
    "churn",           # total lines modified (la + ld)
    "churn_per_file",  # average churn per modified file
    "del_ratio",       # ratio of deletions to churn
    "exp_ratio",       # author subsystem exp / total exp
    "log_churn",       # log1p of total churn (mitigates extreme power-law skew)
    "log_la",          # log1p of lines added
    "log_ld",          # log1p of lines deleted
]

ALL_MODEL_FEATURES: List[str] = CORE_NUMERIC_FEATURES + ENGINEERED_FEATURES


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Transforms raw commit/MR metrics into rich ML features:
    - Calculates churn metrics (la + ld)
    - Measures deletion vs addition ratio
    - Computes developer subsystem familiarity ratio
    - Applies log1p transforms on heavy-tailed churn distributions
    """

    def __init__(self):
        self.feature_names = ALL_MODEL_FEATURES

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        
        # Verify required raw features exist
        for col in CORE_NUMERIC_FEATURES:
            if col not in df.columns:
                df[col] = 0.0

        # Raw numeric conversions
        la = np.maximum(df["la"].values.astype(float), 0.0)
        ld = np.maximum(df["ld"].values.astype(float), 0.0)
        nf = np.maximum(df["nf"].values.astype(float), 1.0)
        aexp = np.maximum(df["aexp"].values.astype(float), 0.0)
        asexp = np.maximum(df["asexp"].values.astype(float), 0.0)

        # Churn features
        churn = la + ld
        df["churn"] = churn
        df["churn_per_file"] = churn / nf
        df["del_ratio"] = ld / (churn + 1e-6)
        
        # Experience ratios
        df["exp_ratio"] = asexp / (aexp + 1.0)

        # Log transforms for skewed distributions
        df["log_churn"] = np.log1p(churn)
        df["log_la"] = np.log1p(la)
        df["log_ld"] = np.log1p(ld)

        return df[self.feature_names]


def get_feature_descriptions() -> Dict[str, str]:
    """Provides human-readable descriptions of all model features."""
    return {
        "la": "Lines of code added in this change",
        "ld": "Lines of code deleted in this change",
        "nf": "Number of unique files modified",
        "nd": "Number of directories affected",
        "ns": "Number of top-level subsystems touched",
        "ent": "Distribution entropy of changes across files",
        "ndev": "Historical developer count for affected files",
        "age": "Average historical age of modified files (in days)",
        "nuc": "Unique prior commit modifications to affected files",
        "aexp": "Total developer experience (past commit volume)",
        "arexp": "Recent developer experience (weighted recent activity)",
        "asexp": "Subsystem-specific developer experience",
        "churn": "Total churn (added + deleted lines)",
        "churn_per_file": "Average churn per modified file",
        "del_ratio": "Proportion of deleted code relative to total churn",
        "exp_ratio": "Proportion of experience spent in affected subsystem",
        "log_churn": "Log-scaled churn to normalize massive diff spikes",
        "log_la": "Log-scaled lines added",
        "log_ld": "Log-scaled lines deleted",
    }
