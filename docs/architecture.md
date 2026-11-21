# MergeGuard AI — System Architecture & Engineering Specifications

MergeGuard AI is an industry-grade Machine Learning and Software Engineering system that predicts software defect risk for Git commits and Merge Requests. It analyzes code change dynamics, developer interaction patterns, and repository history to calculate calibrated risk scores, categorize changes into actionable risk tiers (`LOW`, `MEDIUM`, `HIGH`), explain risk drivers, and provide code review recommendations.

---

## 1. High-Level Architecture Topology

```
+-------------------------------------------------------------+
|                 Developer / Code Reviewer                   |
+-------------------------------------------------------------+
                              |
                              v
                +----------------------------+
                |    Angular 21 Dashboard    |
                +----------------------------+
                              |
                    REST APIs | HTTP
                              v
        +--------------------------------------------+
        |            FastAPI Backend                 |
        |  - CORS & Async Request Handling           |
        |  - Pydantic Validation                     |
        |  - GitLab REST API Client                  |
        +--------------------------------------------+
                 |                         |
                 v                         v
+---------------------------------+  +-------------------------------+
|      MergeGuard Risk Engine     |  |     PostgreSQL / SQLite       |
|  - Feature Pipeline             |  |  - Prediction Records         |
|  - HistGradientBoosting Model   |  |  - Risk Factors JSON          |
|  - 0-100 Calibrated Risk Score  |  |  - Review Recommendations     |
|  - Grounded Explainability      |  +-------------------------------+
+---------------------------------+
```

---

## 2. Machine Learning Pipeline Architecture

### 2.1 The Just-In-Time (JIT) Defect Problem
Unlike file-level defect prediction (which predicts if an entire file has bugs after release), **Just-In-Time (JIT) defect prediction** predicts defects at the moment a commit or Merge Request is authored.

### 2.2 Feature Representation (12 Core + 7 Engineered Features)
The system extracts code change metrics and historical developer metrics:

| Feature | Category | Definition | Domain Meaning |
|---|---|---|---|
| `la` | Churn | Lines Added | Raw modification volume |
| `ld` | Churn | Lines Deleted | Refactoring or deletion volume |
| `nf` | Dispersion | Number of Files | Breadth of affected files |
| `nd` | Dispersion | Number of Directories | Breadth of directories touched |
| `ns` | Dispersion | Number of Subsystems | Cross-system boundary crossing |
| `ent` | Entropy | Shannon Change Entropy | Measure of how evenly changes are scattered across files |
| `ndev` | Collaboration | Historical Developer Count | Developer collaboration density on modified files |
| `age` | Temporal | Historical Age (days) | Age of code being touched (legacy code indicator) |
| `nuc` | Stability | Number of Unique Changes | Churn frequency of affected files |
| `aexp` | Experience | Developer Total Commits | Overall repository author experience |
| `arexp` | Experience | Developer Recent Commits | Author recent activity velocity |
| `asexp` | Experience | Subsystem Commits | Author familiarity with the specific modified subsystem |

**Engineered Features:**
1. `churn = la + ld`: Aggregate volume of modified lines.
2. `churn_per_file = churn / nf`: Average change intensity per file.
3. `del_ratio = ld / (churn + 1e-6)`: Ratio of deleted lines to total churn.
4. `exp_ratio = asexp / (aexp + 1)`: Relative developer specialization in this subsystem.
5. `log_la, log_ld, log_churn`: Log1p transforms to normalize extreme power-law churn spikes.

### 2.3 The Temporal Validation Strategy
- **Training Set (2003–2016)**: 44,834 commits. Artificially balanced by ApacheJIT authors to 50.01% positive class.
- **Holdout Test Set (2017–2020)**: 30,111 commits. **Real-world unbalanced distribution** with only 19.32% defects.
- **Key Takeaway**: Random k-fold cross-validation is **invalid** for time-series software defect prediction because it leaks future repository dynamics into past commits. Our temporal split guarantees realistic generalization.

---

## 3. Model Benchmark Results

Models evaluated on the real-world temporal holdout set (30,111 commits):

| Model Architecture | ROC-AUC | PR-AUC | Defect Recall | Precision | F1-Score | Status |
|---|---|---|---|---|---|---|
| Dummy Classifier (Prior) | 0.5000 | 0.1932 | 100.0% | 19.32% | 0.3239 | Naive Baseline |
| Logistic Regression | 0.7996 | 0.4908 | 77.91% | 35.94% | 0.4919 | Linear Baseline |
| Random Forest (120 Trees) | 0.8072 | 0.5089 | 82.74% | 34.83% | 0.4902 | Strong Baseline |
| **HistGradientBoosting** | **0.8034** | **0.5001** | **81.88%** | **34.96%** | **0.4900** | **Production Champion** |

---

## 4. Explainable Risk Engine & Recommendations

The `RiskEngine`:
1. Converts the model output into an intuitive **0–100 Calibrated Risk Score**.
2. Categorizes into operational tiers:
   - `LOW` (0–39): Pass-through standard CI.
   - `MEDIUM` (40–69): Targeted review of modified modules.
   - `HIGH` (70–100): Mandatory senior review, extra automated tests, staged deployment.
3. Computes local feature attribution to explain **why** the change is risky.
4. Generates contextual recommendations (e.g., missing test files, scattered diffs, low subsystem experience).
