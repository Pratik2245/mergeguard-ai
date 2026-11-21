"""
MergeGuard AI - Authentication & JWT Security Module
Supports Argon2 secure password hashing, PyJWT token issuance and verification,
with dual persistence to MongoDB and relational databases.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

# Password hashing with Argon2 (with fallback to PBKDF2 HMAC)
try:
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    def hash_password(password: str) -> str:
        return ph.hash(password)
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return ph.verify(hashed_password, plain_password)
        except Exception:
            return False
except ImportError:
    import hashlib
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
        return f"{salt}${key}"
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            salt, key = hashed_password.split("$", 1)
            check = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt.encode(), 100000).hex()
            return secrets.compare_digest(key, check)
        except Exception:
            return False

from .database import get_db
from .models import UserRecord
from .mongodb import MongoDBManager

# JWT Configuration (RFC 7519 Standard compliant)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mergeguard-ai-secret-key-prod-2026-supersecure")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Ensure "sub" is string per RFC 7519
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_user_by_email_or_username(identifier: str, db: Session) -> Optional[UserRecord]:
    try:
        user = db.query(UserRecord).filter(
            (UserRecord.email == identifier) | (UserRecord.username == identifier)
        ).first()
        return user
    except Exception:
        db.rollback()
        return None


def create_user(
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "engineer",
    db: Session = None,
) -> UserRecord:
    # Normalize inputs
    email_clean = email.strip().lower()
    username_clean = username.strip().lower()

    # Verify uniqueness
    existing = get_user_by_email_or_username(email_clean, db) or get_user_by_email_or_username(username_clean, db)
    if existing:
        raise ValueError("User with this email or username already exists.")

    hashed = hash_password(password)
    now = datetime.now(timezone.utc)

    # 1. Store in Relational DB
    user_record = UserRecord(
        email=email_clean,
        username=username_clean,
        full_name=full_name.strip() if full_name else username_clean,
        hashed_password=hashed,
        role=role,
        created_at=now,
    )
    
    try:
        db.add(user_record)
        db.commit()
        db.refresh(user_record)
    except Exception:
        db.rollback()
        raise

    # 2. Store in MongoDB if connected
    mongo = MongoDBManager.get_instance()
    if mongo.is_connected and mongo.users_col is not None:
        try:
            mongo.users_col.insert_one({
                "id": user_record.id,
                "email": email_clean,
                "username": username_clean,
                "full_name": user_record.full_name,
                "hashed_password": hashed,
                "role": role,
                "created_at": now.isoformat(),
            })
        except Exception as e:
            print(f"[MongoDB] Notice: Could not sync user to MongoDB: {e}")

    return user_record


def authenticate_user(identifier: str, password: str, db: Session) -> Optional[UserRecord]:
    clean_id = identifier.strip().lower()
    user = get_user_by_email_or_username(clean_id, db)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def seed_default_admin(db: Session):
    """Creates a default demo admin user if no users exist."""
    try:
        admin = db.query(UserRecord).filter(UserRecord.email == "admin@mergeguard.ai").first()
        if not admin:
            print("[Auth] Creating default administrator: admin@mergeguard.ai")
            create_user(
                email="admin@mergeguard.ai",
                username="admin",
                password="adminpassword123",
                full_name="Lead DevOps Reviewer",
                role="admin",
                db=db,
            )
    except Exception as e:
        db.rollback()
        print(f"[Auth] Notice during admin seed: {e}")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> UserRecord:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject",
        )

    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Optional[UserRecord]:
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    sub = payload.get("sub")
    try:
        user_id = int(sub)
        return db.query(UserRecord).filter(UserRecord.id == user_id).first()
    except (ValueError, TypeError):
        return None
