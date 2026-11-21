"""
MergeGuard AI - Backend Integration & Unit Test Suite
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "gradient_boosting" in data["champion_model"]


def test_model_info():
    response = client.get("/api/v1/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert len(data["features"]) == 12
    assert "benchmarks" in data


def test_direct_prediction_high_risk():
    payload = {
        "la": 1200,
        "ld": 450,
        "nf": 35,
        "nd": 12,
        "ns": 4,
        "ent": 3.9,
        "ndev": 7.0,
        "age": 180.0,
        "nuc": 40.0,
        "aexp": 15.0,
        "arexp": 10.0,
        "asexp": 1.0,
        "project_name": "test/large-project",
        "mr_iid": 99,
        "mr_title": "Huge refactoring of core modules",
        "tests_modified": False,
        "critical_modules": True,
    }
    response = client.post("/api/v1/predict/direct", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 60
    assert data["risk_level"] in ["MEDIUM", "HIGH"]
    assert len(data["top_risk_factors"]) > 0
    assert len(data["recommendations"]) > 0
    assert any("test" in r.lower() for r in data["recommendations"])


def test_direct_prediction_low_risk():
    payload = {
        "la": 10,
        "ld": 2,
        "nf": 1,
        "nd": 1,
        "ns": 1,
        "ent": 0.0,
        "ndev": 1.0,
        "age": 12.0,
        "nuc": 5.0,
        "aexp": 500.0,
        "arexp": 400.0,
        "asexp": 300.0,
        "project_name": "test/small-fix",
        "mr_iid": 101,
        "mr_title": "Typo fix in docs",
        "tests_modified": True,
        "critical_modules": False,
    }
    response = client.post("/api/v1/predict/direct", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] <= 40
    assert data["risk_level"] == "LOW"


def test_git_diff_prediction():
    sample_diff = """diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,3 +1,5 @@
+import hashlib
+import secrets
 def login():
-    pass
+    return secrets.token_hex(16)
diff --git a/tests/test_auth.py b/tests/test_auth.py
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -1,2 +1,4 @@
+def test_login():
+    assert True
"""
    payload = {
        "diff_text": sample_diff,
        "project_name": "test/auth-service",
        "mr_iid": 202,
        "mr_title": "Implement secure auth token generator",
    }
    response = client.post("/api/v1/predict/diff", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert data["metrics_summary"]["files_changed"] == 2
    assert data["metrics_summary"]["tests_modified"] is True
    assert data["metrics_summary"]["critical_modules_affected"] is True


def test_analytics_and_predictions_list():
    response = client.get("/api/v1/predictions")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 3  # Initial seeded + tests

    analytics_resp = client.get("/api/v1/analytics")
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()
    assert analytics["total_predictions"] >= 3
    assert "avg_risk_score" in analytics
