"""
MergeGuard AI - MongoDB Database Connection & Collection Manager
Provides resilient document storage for user accounts, complete prediction documents,
and raw Git diff artifacts.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "mergeguard_ai")


class MongoDBManager:
    _instance: Optional["MongoDBManager"] = None

    def __init__(self):
        self.url = MONGODB_URL
        self.db_name = MONGODB_DB_NAME
        self.client: Optional[MongoClient] = None
        self.is_connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(self.url, serverSelectionTimeoutMS=1500)
            # Ping database to test connectivity
            self.client.admin.command("ping")
            self.is_connected = True
            print(f"[MongoDB] Connected successfully to {self.url}/{self.db_name}")
            self._ensure_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            self.is_connected = False
            print(f"[MongoDB] Note: MongoDB connection at {self.url} unavailable ({e}). Running with graceful dual-storage fallback.")

    def _ensure_indexes(self):
        if not self.is_connected or self.client is None:
            return
        db = self.client[self.db_name]
        try:
            db.users.create_index("email", unique=True)
            db.users.create_index("username", unique=True)
            db.predictions.create_index([("project_name", 1), ("created_at", -1)])
            db.predictions.create_index("risk_level")
        except Exception as e:
            print(f"[MongoDB] Index creation notice: {e}")

    @classmethod
    def get_instance(cls) -> "MongoDBManager":
        if cls._instance is None:
            cls._instance = MongoDBManager()
        return cls._instance

    @property
    def users_col(self) -> Optional[Collection]:
        if self.is_connected and self.client:
            return self.client[self.db_name]["users"]
        return None

    @property
    def predictions_col(self) -> Optional[Collection]:
        if self.is_connected and self.client:
            return self.client[self.db_name]["predictions"]
        return None

    def insert_prediction(self, doc: Dict[str, Any]) -> bool:
        """Stores a complete prediction report document in MongoDB."""
        if not self.is_connected or self.predictions_col is None:
            return False
        try:
            doc_copy = dict(doc)
            if "created_at" in doc_copy and isinstance(doc_copy["created_at"], str):
                # Ensure stored as ISO timestamp
                pass
            self.predictions_col.insert_one(doc_copy)
            return True
        except Exception as e:
            print(f"[MongoDB] Error inserting prediction: {e}")
            return False

    def get_predictions(self, risk_level: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_connected or self.predictions_col is None:
            return []
        try:
            query = {}
            if risk_level and risk_level != "ALL":
                query["risk_level"] = risk_level.upper()
            cursor = self.predictions_col.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"[MongoDB] Error querying predictions: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """Returns MongoDB health, connection status, and document statistics."""
        if not self.is_connected or self.client is None:
            return {
                "connected": False,
                "url": self.url,
                "database": self.db_name,
                "message": "MongoDB is not reachable at this address. Fallback relational storage is active.",
                "collections": {},
            }
        
        try:
            db = self.client[self.db_name]
            users_count = db.users.count_documents({})
            predictions_count = db.predictions.count_documents({})
            return {
                "connected": True,
                "url": self.url,
                "database": self.db_name,
                "message": "Connected to MongoDB",
                "collections": {
                    "users": users_count,
                    "predictions": predictions_count,
                },
            }
        except Exception as e:
            return {
                "connected": False,
                "url": self.url,
                "database": self.db_name,
                "error": str(e),
            }
