"""
MergeGuard AI - FastAPI Application
Provides RESTful APIs for MR defect risk prediction, git diff analysis,
GitLab integration, JWT authentication, MongoDB document storage, and analytics.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .database import engine, Base, get_db
from .models import PredictionRecord, UserRecord
from .schemas import (
    DirectPredictRequest,
    GitDiffPredictRequest,
    GitLabMRRequest,
    RiskPredictionResponse,
    PredictionListItem,
    AnalyticsResponse,
    RiskFactorItem,
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    MongoStatusResponse,
)
from .ml_service import MLService
from .gitlab_client import GitLabClient
from .mongodb import MongoDBManager
from .auth import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_optional_current_user,
    seed_default_admin,
)

# Initialize relational database tables at module load
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables exist on startup
    Base.metadata.create_all(bind=engine)

    print("[Startup] Initializing MergeGuard ML Service...")
    ml_service = MLService.get_instance()
    print(f"[Startup] Champion model loaded: {ml_service.champion_type}")

    # Initialize MongoDB connection
    mongo = MongoDBManager.get_instance()
    if mongo.is_connected:
        print("[Startup] MongoDB document store connected.")
    else:
        print("[Startup] MongoDB running in dual fallback mode.")

    # Seed demo records & default admin user
    db = next(get_db())
    try:
        seed_default_admin(db)
        if db.query(PredictionRecord).count() == 0:
            print("[Startup] Seeding initial demo analysis records...")
            seed_demo_data(db, ml_service)
    except Exception as e:
        print(f"[Startup] Notice during startup seed: {e}")
    finally:
        db.close()

    yield
    print("[Shutdown] Cleaning up MergeGuard AI resources...")


def seed_demo_data(db: Session, ml_service: MLService):
    """Populates the database with initial representative MR predictions."""
    demos = [
        {
            "project_name": "gitlab-org/gitlab",
            "mr_iid": 14209,
            "mr_title": "Refactor authentication session handler and permission gate",
            "metrics": {
                "la": 940, "ld": 230, "nf": 28, "nd": 7, "ns": 3,
                "ent": 3.6, "ndev": 6, "age": 120, "nuc": 30,
                "aexp": 50, "arexp": 40, "asexp": 3
            },
            "tests_modified": False,
            "critical_modules": True,
        },
        {
            "project_name": "apache/groovy",
            "mr_iid": 1845,
            "mr_title": "Fix null pointer in AST expression visitor and add unit tests",
            "metrics": {
                "la": 45, "ld": 12, "nf": 3, "nd": 2, "ns": 1,
                "ent": 1.1, "ndev": 2, "age": 45, "nuc": 10,
                "aexp": 320, "arexp": 280, "asexp": 180
            },
            "tests_modified": True,
            "critical_modules": False,
        },
        {
            "project_name": "torvalds/linux",
            "mr_iid": 502,
            "mr_title": "Documentation update for memory barrier semantics",
            "metrics": {
                "la": 14, "ld": 2, "nf": 1, "nd": 1, "ns": 1,
                "ent": 0.0, "ndev": 1, "age": 10, "nuc": 4,
                "aexp": 600, "arexp": 500, "asexp": 350
            },
            "tests_modified": False,
            "critical_modules": False,
        },
    ]

    for demo in demos:
        try:
            res = ml_service.predict_direct(
                metrics=demo["metrics"],
                tests_modified=demo["tests_modified"],
                critical_modules=demo["critical_modules"],
            )
            record = PredictionRecord(
                project_name=demo["project_name"],
                mr_iid=demo["mr_iid"],
                mr_title=demo["mr_title"],
                risk_score=res.risk_score,
                risk_level=res.risk_level,
                defect_probability=res.defect_probability,
                metrics_json=json.dumps(res.metrics_summary),
                risk_factors_json=json.dumps(res.top_risk_factors),
                mitigating_factors_json=json.dumps(res.mitigating_factors),
                recommendations_json=json.dumps(res.recommendations),
                created_by_user="admin",
                created_at=datetime.now(timezone.utc),
            )
            db.add(record)

            # Also sync to MongoDB if connected
            mongo = MongoDBManager.get_instance()
            mongo.insert_prediction({
                "project_name": demo["project_name"],
                "mr_iid": demo["mr_iid"],
                "mr_title": demo["mr_title"],
                "risk_score": res.risk_score,
                "risk_level": res.risk_level,
                "defect_probability": res.defect_probability,
                "metrics_summary": res.metrics_summary,
                "top_risk_factors": res.top_risk_factors,
                "mitigating_factors": res.mitigating_factors,
                "recommendations": res.recommendations,
                "created_by_user": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            print(f"[Seed] Notice: Could not seed record: {e}")

    try:
        db.commit()
    except Exception:
        db.rollback()


app = FastAPI(
    title="MergeGuard AI - API",
    description="Intelligent Software Defect & Merge Request Risk Prediction Engine with MongoDB & JWT Auth",
    version="1.1.0",
    lifespan=lifespan,
)

# Global CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler ensuring CORS headers on 500 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[Unhandled Error on {request.method} {request.url.path}]: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Server Error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


# ==========================================
# Authentication Endpoints
# ==========================================

@app.post("/api/v1/auth/register", response_model=TokenResponse, tags=["Authentication"])
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new developer/reviewer account and returns a JWT access token."""
    try:
        user = create_user(
            email=req.email,
            username=req.username,
            password=req.password,
            full_name=req.full_name,
            role="engineer",
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration error: {str(e)}")

    token = create_access_token({"sub": str(user.id), "email": user.email, "username": user.username})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            created_at=user.created_at.isoformat(),
        ),
    )


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues a JWT Bearer token."""
    user = authenticate_user(req.username_or_email, req.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    token = create_access_token({"sub": str(user.id), "email": user.email, "username": user.username})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            created_at=user.created_at.isoformat(),
        ),
    )


@app.get("/api/v1/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_profile(user: UserRecord = Depends(get_current_user)):
    """Returns the authenticated user's profile."""
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )


# ==========================================
# MongoDB Status Endpoint
# ==========================================

@app.get("/api/v1/mongodb/status", response_model=MongoStatusResponse, tags=["Database"])
def get_mongodb_status():
    """Inspects MongoDB connection health, database statistics, and collection counts."""
    mongo = MongoDBManager.get_instance()
    info = mongo.get_status()
    return MongoStatusResponse(
        connected=info.get("connected", False),
        url=info.get("url", ""),
        database=info.get("database", ""),
        message=info.get("message", ""),
        collections=info.get("collections", {}),
    )


# ==========================================
# System Health & Model Info
# ==========================================

@app.get("/api/v1/health", tags=["System"])
def health_check():
    """System health check endpoint verifying ML model, MongoDB, and DB readiness."""
    ml_service = MLService.get_instance()
    mongo = MongoDBManager.get_instance()
    return {
        "status": "healthy",
        "service": "MergeGuard AI Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_loaded": ml_service.pipeline is not None,
        "champion_model": ml_service.champion_type,
        "mongodb_connected": mongo.is_connected,
    }


@app.get("/api/v1/model-info", tags=["System"])
def get_model_info():
    """Returns technical details regarding the active model and training evaluation benchmarks."""
    ml_service = MLService.get_instance()
    return ml_service.get_info()


# ==========================================
# Prediction Endpoints
# ==========================================

@app.post("/api/v1/predict/direct", response_model=RiskPredictionResponse, tags=["Predictions"])
def predict_direct(
    req: DirectPredictRequest,
    db: Session = Depends(get_db),
    user: Optional[UserRecord] = Depends(get_optional_current_user),
):
    """
    Evaluates Merge Request risk directly from quantitative commit/MR metrics.
    Stores the full result in relational storage and MongoDB.
    """
    ml_service = MLService.get_instance()
    
    metrics = {
        "la": req.la, "ld": req.ld, "nf": req.nf, "nd": req.nd, "ns": req.ns,
        "ent": req.ent, "ndev": req.ndev, "age": req.age, "nuc": req.nuc,
        "aexp": req.aexp, "arexp": req.arexp, "asexp": req.asexp,
    }

    res = ml_service.predict_direct(
        metrics=metrics,
        tests_modified=req.tests_modified,
        critical_modules=req.critical_modules,
    )

    created_by = user.username if user else "anonymous"
    now = datetime.now(timezone.utc)

    record = PredictionRecord(
        project_name=req.project_name or "mergeguard/demo",
        mr_iid=req.mr_iid,
        mr_title=req.mr_title or f"MR #{req.mr_iid}" if req.mr_iid else "Direct Feature Prediction",
        risk_score=res.risk_score,
        risk_level=res.risk_level,
        defect_probability=res.defect_probability,
        metrics_json=json.dumps(res.metrics_summary),
        risk_factors_json=json.dumps(res.top_risk_factors),
        mitigating_factors_json=json.dumps(res.mitigating_factors),
        recommendations_json=json.dumps(res.recommendations),
        created_by_user=created_by,
        created_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Sync to MongoDB document collection
    mongo = MongoDBManager.get_instance()
    mongo.insert_prediction({
        "id": record.id,
        "project_name": record.project_name,
        "mr_iid": record.mr_iid,
        "mr_title": record.mr_title,
        "risk_score": res.risk_score,
        "risk_level": res.risk_level,
        "defect_probability": res.defect_probability,
        "metrics_summary": res.metrics_summary,
        "top_risk_factors": res.top_risk_factors,
        "mitigating_factors": res.mitigating_factors,
        "recommendations": res.recommendations,
        "created_by_user": created_by,
        "created_at": now.isoformat(),
    })

    return RiskPredictionResponse(
        id=record.id,
        project_name=record.project_name,
        mr_iid=record.mr_iid,
        mr_title=record.mr_title,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        defect_probability=record.defect_probability,
        top_risk_factors=[RiskFactorItem(**f) for f in res.top_risk_factors],
        mitigating_factors=[RiskFactorItem(**f) for f in res.mitigating_factors],
        recommendations=res.recommendations,
        metrics_summary=res.metrics_summary,
        created_by_user=created_by,
        created_at=record.created_at.isoformat(),
    )


@app.post("/api/v1/predict/diff", response_model=RiskPredictionResponse, tags=["Predictions"])
def predict_git_diff(
    req: GitDiffPredictRequest,
    db: Session = Depends(get_db),
    user: Optional[UserRecord] = Depends(get_optional_current_user),
):
    """
    Parses a raw unified git diff, extracts code change metrics, evaluates risk,
    and stores the document in MongoDB.
    """
    ml_service = MLService.get_instance()
    dev_metrics = {"aexp": req.aexp, "arexp": req.arexp, "asexp": req.asexp}

    res, diff_meta = ml_service.predict_diff(req.diff_text, dev_metrics=dev_metrics)
    created_by = user.username if user else "anonymous"
    now = datetime.now(timezone.utc)

    record = PredictionRecord(
        project_name=req.project_name,
        mr_iid=req.mr_iid,
        mr_title=req.mr_title,
        risk_score=res.risk_score,
        risk_level=res.risk_level,
        defect_probability=res.defect_probability,
        metrics_json=json.dumps(res.metrics_summary),
        risk_factors_json=json.dumps(res.top_risk_factors),
        mitigating_factors_json=json.dumps(res.mitigating_factors),
        recommendations_json=json.dumps(res.recommendations),
        created_by_user=created_by,
        created_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Sync to MongoDB with raw diff snippet
    mongo = MongoDBManager.get_instance()
    mongo.insert_prediction({
        "id": record.id,
        "project_name": record.project_name,
        "mr_iid": record.mr_iid,
        "mr_title": record.mr_title,
        "risk_score": res.risk_score,
        "risk_level": res.risk_level,
        "defect_probability": res.defect_probability,
        "metrics_summary": res.metrics_summary,
        "top_risk_factors": res.top_risk_factors,
        "mitigating_factors": res.mitigating_factors,
        "recommendations": res.recommendations,
        "raw_diff_preview": req.diff_text[:1500],
        "created_by_user": created_by,
        "created_at": now.isoformat(),
    })

    return RiskPredictionResponse(
        id=record.id,
        project_name=record.project_name,
        mr_iid=record.mr_iid,
        mr_title=record.mr_title,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        defect_probability=record.defect_probability,
        top_risk_factors=[RiskFactorItem(**f) for f in res.top_risk_factors],
        mitigating_factors=[RiskFactorItem(**f) for f in res.mitigating_factors],
        recommendations=res.recommendations,
        metrics_summary=res.metrics_summary,
        created_by_user=created_by,
        created_at=record.created_at.isoformat(),
    )


@app.post("/api/v1/predict/gitlab", response_model=RiskPredictionResponse, tags=["GitLab Integration"])
async def predict_gitlab_mr(
    req: GitLabMRRequest,
    db: Session = Depends(get_db),
    user: Optional[UserRecord] = Depends(get_optional_current_user),
):
    """
    Fetches a live Merge Request from GitLab REST API, parses diffs, and returns risk analysis.
    """
    client = GitLabClient(base_url=req.gitlab_url, private_token=req.private_token)
    try:
        mr_meta = await client.fetch_merge_request(req.project_id, req.mr_iid)
        diff_text = await client.fetch_mr_diffs(req.project_id, req.mr_iid)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch GitLab MR: {str(e)}"
        )

    ml_service = MLService.get_instance()
    res, _ = ml_service.predict_diff(diff_text)
    created_by = user.username if user else "anonymous"
    now = datetime.now(timezone.utc)

    record = PredictionRecord(
        project_name=req.project_id,
        mr_iid=req.mr_iid,
        mr_title=mr_meta.get("title", f"GitLab MR !{req.mr_iid}"),
        risk_score=res.risk_score,
        risk_level=res.risk_level,
        defect_probability=res.defect_probability,
        metrics_json=json.dumps(res.metrics_summary),
        risk_factors_json=json.dumps(res.top_risk_factors),
        mitigating_factors_json=json.dumps(res.mitigating_factors),
        recommendations_json=json.dumps(res.recommendations),
        created_by_user=created_by,
        created_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Sync to MongoDB
    mongo = MongoDBManager.get_instance()
    mongo.insert_prediction({
        "id": record.id,
        "project_name": record.project_name,
        "mr_iid": record.mr_iid,
        "mr_title": record.mr_title,
        "risk_score": res.risk_score,
        "risk_level": res.risk_level,
        "defect_probability": res.defect_probability,
        "metrics_summary": res.metrics_summary,
        "top_risk_factors": res.top_risk_factors,
        "mitigating_factors": res.mitigating_factors,
        "recommendations": res.recommendations,
        "created_by_user": created_by,
        "created_at": now.isoformat(),
    })

    return RiskPredictionResponse(
        id=record.id,
        project_name=record.project_name,
        mr_iid=record.mr_iid,
        mr_title=record.mr_title,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        defect_probability=record.defect_probability,
        top_risk_factors=[RiskFactorItem(**f) for f in res.top_risk_factors],
        mitigating_factors=[RiskFactorItem(**f) for f in res.mitigating_factors],
        recommendations=res.recommendations,
        metrics_summary=res.metrics_summary,
        created_by_user=created_by,
        created_at=record.created_at.isoformat(),
    )


@app.get("/api/v1/predictions", response_model=List[PredictionListItem], tags=["Predictions"])
def list_predictions(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW, MEDIUM, HIGH"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lists historical prediction records sorted by recency."""
    query = db.query(PredictionRecord)
    if risk_level:
        query = query.filter(PredictionRecord.risk_level == risk_level.upper())
    records = query.order_by(desc(PredictionRecord.created_at)).limit(limit).all()

    return [
        PredictionListItem(
            id=r.id,
            project_name=r.project_name,
            mr_iid=r.mr_iid,
            mr_title=r.mr_title,
            risk_score=r.risk_score,
            risk_level=r.risk_level,
            defect_probability=r.defect_probability,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]


@app.get("/api/v1/predictions/{prediction_id}", response_model=RiskPredictionResponse, tags=["Predictions"])
def get_prediction_detail(prediction_id: int, db: Session = Depends(get_db)):
    """Retrieves full details, metrics, risk factors, and recommendations for a past prediction."""
    r = db.query(PredictionRecord).filter(PredictionRecord.id == prediction_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Prediction record not found")

    return RiskPredictionResponse(
        id=r.id,
        project_name=r.project_name,
        mr_iid=r.mr_iid,
        mr_title=r.mr_title,
        risk_score=r.risk_score,
        risk_level=r.risk_level,
        defect_probability=r.defect_probability,
        top_risk_factors=json.loads(r.risk_factors_json),
        mitigating_factors=json.loads(r.mitigating_factors_json),
        recommendations=json.loads(r.recommendations_json),
        metrics_summary=json.loads(r.metrics_json),
        created_by_user=r.created_by_user,
        created_at=r.created_at.isoformat(),
    )


@app.get("/api/v1/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
def get_analytics(db: Session = Depends(get_db)):
    """Aggregates system-wide risk metrics across all evaluated Merge Requests."""
    total = db.query(PredictionRecord).count()
    if total == 0:
        return AnalyticsResponse(
            total_predictions=0,
            avg_risk_score=0.0,
            high_risk_count=0,
            medium_risk_count=0,
            low_risk_count=0,
            high_risk_pct=0.0,
            common_recommendations=[],
        )

    avg_score = db.query(func.avg(PredictionRecord.risk_score)).scalar() or 0.0
    high_count = db.query(PredictionRecord).filter(PredictionRecord.risk_level == "HIGH").count()
    med_count = db.query(PredictionRecord).filter(PredictionRecord.risk_level == "MEDIUM").count()
    low_count = db.query(PredictionRecord).filter(PredictionRecord.risk_level == "LOW").count()

    # Collect recommendation frequency
    all_records = db.query(PredictionRecord.recommendations_json).all()
    rec_counts: Dict[str, int] = {}
    for (rec_json,) in all_records:
        for rec in json.loads(rec_json):
            rec_counts[rec] = rec_counts.get(rec, 0) + 1

    common_recs = [
        {"recommendation": k, "count": v}
        for k, v in sorted(rec_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return AnalyticsResponse(
        total_predictions=total,
        avg_risk_score=round(float(avg_score), 1),
        high_risk_count=high_count,
        medium_risk_count=med_count,
        low_risk_count=low_count,
        high_risk_pct=round((high_count / total) * 100, 1),
        common_recommendations=common_recs,
    )
