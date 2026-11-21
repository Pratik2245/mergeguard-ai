# MergeGuard AI 🛡️
### AI-Powered Software Defect & Merge Request Risk Prediction System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn%20%7C%20Ensembles-F7931E.svg)](https://scikit-learn.org/)
[![Angular](https://img.shields.io/badge/Frontend-Angular%2021-DD0031.svg)](https://angular.dev/)
[![Docker](https://img.shields.io/badge/Deployment-Docker%20%26%20Compose-2496ED.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes%20%26%20Helm-326CE5.svg)](https://kubernetes.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 1. Project Overview

**MergeGuard AI** is an enterprise-grade Machine Learning and Software Engineering platform that analyzes code changes and predicts their defect risk before they are merged into production. 

Designed for modern DevOps and Git workflows (specifically GitLab Merge Requests and Git commits), MergeGuard AI evaluates code churn dynamics, file dispersion entropy, and developer collaboration patterns to:
1. Predict the probability that a code change introduces a defect.
2. Generate an intuitive, calibrated **Risk Score (0–100)**.
3. Categorize changes into operational tiers: `LOW`, `MEDIUM`, and `HIGH`.
4. Provide **grounded explainability** showing which factors escalated or mitigated risk.
5. Generate **actionable review recommendations** (e.g., missing test alerts, senior domain reviewer requests, change decomposition advice).

---

## 2. Key Capabilities

* **Just-In-Time (JIT) Defect Prediction**: Evaluates risk at commit / PR review time rather than post-release file analysis.
* **Calibrated Explainable AI**: Combines gradient boosting ensemble predictions with domain-specific feature attributions.
* **Multi-Input Ingestion**:
  * **Direct Feature Analyzer**: Evaluates numeric change metrics with interactive scenario presets.
  * **Git Diff Parser**: Automatically extracts churn, file counts, Shannon entropy, and test modifications from raw unified git diffs.
  * **GitLab REST API Live Sync**: Connects directly to GitLab projects to pull live Merge Request diffs and metadata.
* **Interactive Angular Dashboard**: Visualizes risk dials, KPI metrics, recent audit history, and recommendations checklist.
* **Production Deployment Ready**: Containerized with Docker, orchestrated with Docker Compose, and packaged for Kubernetes with Helm.

---

## 3. System Architecture

```
+-------------------------------------------------------------+
|                 Developer / Code Reviewer                   |
+-------------------------------------------------------------+
                              |
                              v
                +----------------------------+
                |    Angular 21 Dashboard    |
                |  - Risk Gauge & Metrics    |
                |  - Diff Inspector          |
                |  - Audit Log & Filters     |
                +----------------------------+
                              |
                     HTTP REST API Calls
                              v
        +--------------------------------------------+
        |            FastAPI Backend                 |
        |  - Async Request Handling & CORS           |
        |  - Pydantic Schema Validation              |
        |  - GitLab REST API Client                  |
        +--------------------------------------------+
                 |                         |
                 v                         v
+---------------------------------+  +-------------------------------+
|      MergeGuard Risk Engine     |  |     PostgreSQL / SQLite       |
|  - Feature Pipeline             |  |  - Prediction Records Table   |
|  - HistGradientBoosting Model   |  |  - Risk Factors JSON          |
|  - Calibrated 0-100 Score       |  |  - Review Recommendations     |
|  - Grounded Explanations        |  +-------------------------------+
+---------------------------------+
```

---

## 4. Machine Learning Methodology

### 4.1 Dataset & Ground Truth
MergeGuard AI is trained on the **ApacheJIT** dataset (comprising over 106,000 commits from major Apache software foundations mined via Jira issue tracking and the SZZ bug-inducing commit algorithm).

* **Training Set**: 44,834 commits (2003–2016), balanced to 50% positive/negative.
* **Temporal Holdout Test Set**: 30,111 commits (2017–2020), **unmodified real-world distribution** with only 19.32% defects.
* **Why Temporal Split?** Standard random k-fold cross-validation suffers from severe data leakage in software engineering. By evaluating strictly on future repository history, our model guarantees genuine generalization.

### 4.2 Features (12 Core + 7 Engineered)
* **Code Churn**: Lines added (`la`), lines deleted (`ld`), total churn (`la + ld`), churn per file.
* **Change Dispersion**: Files modified (`nf`), directories touched (`nd`), subsystems (`ns`).
* **Entropy**: Shannon Entropy ($H = -\sum p_i \log_2 p_i$) measuring change dispersion across files.
* **Developer History**: Developer overall experience (`aexp`), recent activity (`arexp`), subsystem specialization (`asexp`), collaboration density (`ndev`).
* **Context**: File age (`age`), unique prior modifications (`nuc`), test file modifications, critical security modules.

### 4.3 Model Benchmark Comparison (On 3-Year Holdout Test Set)

| Model Architecture | ROC-AUC | PR-AUC | Defect Recall | Precision | F1-Score | Status |
|---|---|---|---|---|---|---|
| Dummy Classifier (Prior) | 0.5000 | 0.1932 | 100.0% | 19.32% | 0.3239 | Naive Baseline |
| Logistic Regression | 0.7996 | 0.4908 | 77.91% | 35.94% | 0.4919 | Linear Baseline |
| Random Forest (120 Trees) | 0.8072 | 0.5089 | 82.74% | 34.83% | 0.4902 | Ensemble Candidate |
| **HistGradientBoosting** | **0.8034** | **0.5001** | **81.88%** | **34.96%** | **0.4900** | **Production Champion** |

> **Key Metric**: On an imbalanced 19% defect rate, our champion model achieves **81.88% Recall** and **0.5001 PR-AUC** (over 2.5x higher than random baseline), catching over 8 out of 10 defect-inducing commits.

---

## 5. Repository Structure

```
mergeguard-ai/
├── backend/                        # FastAPI REST Application
│   ├── app/
│   │   ├── main.py                 # FastAPI routes and lifecycle
│   │   ├── schemas.py              # Pydantic request/response models
│   │   ├── database.py             # SQLAlchemy configuration (SQLite / PostgreSQL)
│   │   ├── models.py               # ORM PredictionRecord model
│   │   ├── ml_service.py           # Model inference and explainability bridge
│   │   └── gitlab_client.py        # GitLab REST API client
│   ├── tests/
│   │   └── test_runner.py          # Integration and unit test suite
│   └── requirements.txt
│
├── frontend/                       # Angular 21 Dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── models/risk.model.ts
│   │   │   ├── services/risk.service.ts
│   │   │   ├── app.ts              # Component signals and state
│   │   │   ├── app.html            # Dashboard templates & views
│   │   │   └── app.css             # Cyber/Dark responsive styling
│   └── package.json
│
├── ml-engine/                      # Machine Learning Training & Risk Engine
│   ├── data/raw/apachejit/         # ApacheJIT dataset files
│   ├── models/
│   │   ├── mergeguard_model.joblib # Serialized champion pipeline
│   │   └── evaluation_report.json  # Benchmark metrics JSON
│   ├── src/
│   │   ├── features.py             # Feature definitions & transformations
│   │   ├── model.py                # Model architectures & metrics
│   │   ├── risk_engine.py          # 0-100 score, tiering & recommendations
│   │   ├── gitlab_extractor.py     # Unified git diff metric extractor
│   │   └── train.py                # Reproducible training pipeline
│   └── 01_merge_request_risk_analysis.ipynb
│
├── infrastructure/                 # DevOps & Deployment
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── nginx.conf
│   ├── kubernetes/                 # Raw K8s manifests
│   └── helm/mergeguard-ai/         # Helm chart package
│
├── docs/
│   ├── architecture.md             # System & ML specifications
│   └── interview_handbook.md       # Technical interview defense Q&A
│
├── docker-compose.yml              # Multi-container local orchestration
├── .gitlab-ci.yml                  # GitLab CI pipeline
└── README.md
```

---

## 6. Quickstart & Local Setup

### Prerequisites
* Python 3.11+
* Node.js v20+ & npm
* Docker & Docker Compose (optional for containerized run)

### 1. Machine Learning Engine & Model Training
```bash
# Navigate to ML Engine
cd ml-engine

# Create virtual environment and activate
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the reproducible training pipeline
python src/train.py
```

### 2. Backend API Service
```bash
# From repository root
cd backend

# Install dependencies
pip install -r requirements.txt

# Run unit and integration tests
python tests/test_runner.py

# Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```
Interactive Swagger UI will be available at: `http://localhost:8000/docs`.

### 3. Angular Dashboard
```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Build production bundle
npm run build -- --configuration=production

# Start development server
npm start
```
Open your browser at: `http://localhost:4200`.

---

## 7. Containerized Deployment (Docker Compose)

To spin up the entire multi-tier stack (PostgreSQL + FastAPI ML Service + Angular Nginx) with a single command:

```bash
docker-compose up --build -d
```

| Service | Endpoint | Description |
|---|---|---|
| Frontend Dashboard | `http://localhost:4200` | Angular UI |
| Backend REST API | `http://localhost:8000` | FastAPI |
| API Docs | `http://localhost:8000/docs` | Swagger / OpenAPI |
| PostgreSQL | `localhost:5432` | Relational Store |

---

## 8. Kubernetes & Helm Deployment

### Deploy via Raw Manifests:
```bash
kubectl apply -f infrastructure/kubernetes/00-namespace.yaml
kubectl apply -f infrastructure/kubernetes/01-configmap-secrets.yaml
kubectl apply -f infrastructure/kubernetes/02-postgres.yaml
kubectl apply -f infrastructure/kubernetes/03-backend.yaml
kubectl apply -f infrastructure/kubernetes/04-frontend.yaml
kubectl apply -f infrastructure/kubernetes/05-ingress.yaml
```

### Deploy via Helm:
```bash
helm upgrade --install mergeguard-ai ./infrastructure/helm/mergeguard-ai \
  --namespace mergeguard-ai \
  --create-namespace
```

---

## 9. API Reference Summary

* `GET /api/v1/health`: Service health and model status.
* `GET /api/v1/model-info`: Technical specifications and benchmark metrics.
* `POST /api/v1/predict/direct`: Score change metrics (`la, ld, nf, ent, aexp, etc.`).
* `POST /api/v1/predict/diff`: Parse raw git diff text, calculate metrics, and return score.
* `POST /api/v1/predict/gitlab`: Connect to GitLab REST API, pull live MR diff, and evaluate.
* `GET /api/v1/predictions`: List audit history of past evaluated changes.
* `GET /api/v1/analytics`: Aggregate statistics (mean score, high risk count, common recs).

---

## 10. Portfolio & Interview Highlights

For detailed technical defenses, see [docs/interview_handbook.md](docs/interview_handbook.md).
* **Defensible Evaluation**: Demonstrates why accuracy is a flawed metric on imbalanced defect datasets, using PR-AUC and Recall.
* **Leakage Prevention**: Explains why temporal splitting is mandatory over random k-fold cross-validation.
* **Full-Stack Competency**: Combines modern Python/Scikit-Learn ML engineering, FastAPI async backend architectures, Angular 21 TypeScript frontend, and Kubernetes/Helm DevOps.

---

## License
MIT License. Built for portfolio demonstration and high-quality software engineering research.
