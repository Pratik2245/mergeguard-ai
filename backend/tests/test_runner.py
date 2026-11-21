"""
Standard Library Test Runner for MergeGuard AI Backend
Includes tests for ML predictions, git diff analysis, JWT authentication, and MongoDB status.
"""

import sys
import unittest
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


class TestMergeGuardBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)

    def test_1_health_check(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_loaded"])
        self.assertIn("gradient_boosting", data["champion_model"])

    def test_2_model_info(self):
        resp = self.client.get("/api/v1/model-info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("features", data)
        self.assertEqual(len(data["features"]), 12)

    def test_3_direct_prediction_high_risk(self):
        payload = {
            "la": 1200, "ld": 450, "nf": 35, "nd": 12, "ns": 4,
            "ent": 3.9, "ndev": 7.0, "age": 180.0, "nuc": 40.0,
            "aexp": 15.0, "arexp": 10.0, "asexp": 1.0,
            "project_name": "test/large-project",
            "mr_iid": 99,
            "mr_title": "Huge refactoring of core modules",
            "tests_modified": False,
            "critical_modules": True,
        }
        resp = self.client.post("/api/v1/predict/direct", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["risk_score"], 60)
        self.assertIn(data["risk_level"], ["MEDIUM", "HIGH"])
        self.assertGreater(len(data["top_risk_factors"]), 0)
        self.assertGreater(len(data["recommendations"]), 0)

    def test_4_direct_prediction_low_risk(self):
        payload = {
            "la": 10, "ld": 2, "nf": 1, "nd": 1, "ns": 1,
            "ent": 0.0, "ndev": 1.0, "age": 12.0, "nuc": 5.0,
            "aexp": 500.0, "arexp": 400.0, "asexp": 300.0,
            "project_name": "test/small-fix",
            "mr_iid": 101,
            "mr_title": "Typo fix in docs",
            "tests_modified": True,
            "critical_modules": False,
        }
        resp = self.client.post("/api/v1/predict/direct", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertLessEqual(data["risk_score"], 40)
        self.assertEqual(data["risk_level"], "LOW")

    def test_5_git_diff_prediction(self):
        diff = """diff --git a/src/auth.py b/src/auth.py
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
            "diff_text": diff,
            "project_name": "test/auth-service",
            "mr_iid": 202,
            "mr_title": "Implement secure auth token generator",
        }
        resp = self.client.post("/api/v1/predict/diff", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["metrics_summary"]["files_changed"], 2)
        self.assertTrue(data["metrics_summary"]["tests_modified"])
        self.assertTrue(data["metrics_summary"]["critical_modules_affected"])

    def test_6_analytics_and_predictions_list(self):
        resp = self.client.get("/api/v1/predictions")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 3)

        analytics_resp = self.client.get("/api/v1/analytics")
        self.assertEqual(analytics_resp.status_code, 200)
        analytics = analytics_resp.json()
        self.assertGreaterEqual(analytics["total_predictions"], 3)
        self.assertIn("avg_risk_score", analytics)

    def test_7_auth_login_default_admin(self):
        # Default admin user is seeded on startup
        login_payload = {
            "username_or_email": "admin@mergeguard.ai",
            "password": "adminpassword123",
        }
        resp = self.client.post("/api/v1/auth/login", json=login_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], "admin@mergeguard.ai")
        self.assertEqual(data["user"]["role"], "admin")

    def test_8_auth_register_and_profile(self):
        uid = uuid.uuid4().hex[:6]
        reg_payload = {
            "email": f"dev_{uid}@mergeguard.ai",
            "username": f"user_{uid}",
            "password": "strongPassword#2026",
            "full_name": f"Engineer {uid}",
        }
        resp = self.client.post("/api/v1/auth/register", json=reg_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        token = data["access_token"]
        self.assertIsNotNone(token)
        self.assertEqual(data["user"]["username"], f"user_{uid}")

        # Test authenticated endpoint /api/v1/auth/me with Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertEqual(me_data["email"], f"dev_{uid}@mergeguard.ai")

    def test_9_mongodb_status(self):
        resp = self.client.get("/api/v1/mongodb/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("connected", data)
        self.assertIn("database", data)
        self.assertEqual(data["database"], "mergeguard_ai")


if __name__ == "__main__":
    unittest.main()
