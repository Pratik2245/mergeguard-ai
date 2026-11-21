"""
MergeGuard AI - GitLab & Git Diff Metric Extractor
Parses Git diffs, commits, and GitLab MR metadata into model-compatible feature vectors.
"""

from typing import Dict, Any, List, Optional
import math
import re
from pathlib import Path


class GitDiffMetrics:
    def __init__(
        self,
        la: int,
        ld: int,
        nf: int,
        nd: int,
        ns: int,
        ent: float,
        tests_modified: bool,
        critical_modules: bool,
        changed_files: List[str],
    ):
        self.la = la
        self.ld = ld
        self.nf = nf
        self.nd = nd
        self.ns = ns
        self.ent = ent
        self.tests_modified = tests_modified
        self.critical_modules = critical_modules
        self.changed_files = changed_files

    def to_dict(self) -> Dict[str, Any]:
        return {
            "la": self.la,
            "ld": self.ld,
            "nf": self.nf,
            "nd": self.nd,
            "ns": self.ns,
            "ent": self.ent,
            "tests_modified": self.tests_modified,
            "critical_modules": self.critical_modules,
            "changed_files": self.changed_files,
        }


CRITICAL_PATH_PATTERNS = [
    r"auth", r"security", r"payment", r"billing", r"permission",
    r"crypto", r"secret", r"database", r"migration", r"config"
]

TEST_PATH_PATTERNS = [
    r"test", r"spec", r"tests", r"__tests__", r"e2e", r"unittest"
]


def parse_git_diff(diff_text: str) -> GitDiffMetrics:
    """
    Parses unified git diff output (git diff or GitLab MR diff) into quantitative change metrics:
    - Counts additions (la) and deletions (ld)
    - Counts modified files (nf), directories (nd), subsystems (ns)
    - Computes change entropy (ent) across files
    - Detects whether test files were modified
    - Detects modifications to security/critical paths
    """
    files: Dict[str, Dict[str, int]] = {}
    current_file = None

    lines = diff_text.splitlines()
    for line in lines:
        # Match git diff header
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                # b/path/to/file
                b_path = parts[3]
                if b_path.startswith("b/"):
                    current_file = b_path[2:]
                else:
                    current_file = b_path
                files[current_file] = {"la": 0, "ld": 0}
            continue

        if line.startswith("--- ") or line.startswith("+++ "):
            continue

        if current_file and current_file in files:
            if line.startswith("+") and not line.startswith("+++"):
                files[current_file]["la"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                files[current_file]["ld"] += 1

    total_la = sum(f["la"] for f in files.values())
    total_ld = sum(f["ld"] for f in files.values())
    total_churn = total_la + total_ld
    file_count = max(len(files), 1)

    # Directories and subsystems
    directories = set()
    subsystems = set()
    for f in files.keys():
        p = Path(f)
        if len(p.parts) > 1:
            subsystems.add(p.parts[0])
            directories.add(str(p.parent))
        else:
            subsystems.add("root")
            directories.add(".")

    nd = max(len(directories), 1)
    ns = max(len(subsystems), 1)

    # Shannon Entropy across modified files: H = - sum(p * log2(p))
    entropy = 0.0
    if total_churn > 0 and len(files) > 1:
        for f_data in files.values():
            file_churn = f_data["la"] + f_data["ld"]
            if file_churn > 0:
                p = file_churn / float(total_churn)
                entropy -= p * math.log2(p)

    # Test file presence
    tests_modified = any(
        any(re.search(pat, f, re.IGNORECASE) for pat in TEST_PATH_PATTERNS)
        for f in files.keys()
    )

    # Critical module presence
    critical_modules = any(
        any(re.search(pat, f, re.IGNORECASE) for pat in CRITICAL_PATH_PATTERNS)
        for f in files.keys()
    )

    return GitDiffMetrics(
        la=total_la,
        ld=total_ld,
        nf=file_count,
        nd=nd,
        ns=ns,
        ent=round(entropy, 4),
        tests_modified=tests_modified,
        critical_modules=critical_modules,
        changed_files=list(files.keys()),
    )


def build_feature_dict(
    diff_metrics: GitDiffMetrics,
    dev_metrics: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Combines diff metrics with developer/historical context (or sensible defaults)
    to form the complete 12-dimensional feature vector.
    """
    dm = dev_metrics or {}
    return {
        "la": float(diff_metrics.la),
        "ld": float(diff_metrics.ld),
        "nf": float(diff_metrics.nf),
        "nd": float(diff_metrics.nd),
        "ns": float(diff_metrics.ns),
        "ent": float(diff_metrics.ent),
        "ndev": float(dm.get("ndev", 2.0)),
        "age": float(dm.get("age", 30.0)),
        "nuc": float(dm.get("nuc", 12.0)),
        "aexp": float(dm.get("aexp", 100.0)),
        "arexp": float(dm.get("arexp", 80.0)),
        "asexp": float(dm.get("asexp", 25.0)),
    }
