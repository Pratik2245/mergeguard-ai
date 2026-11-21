"""
Pydantic Schemas for MergeGuard AI REST API
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


# ==========================================
# Authentication Schemas
# ==========================================

class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    username: str = Field(..., description="Unique username", min_length=3, max_length=50)
    password: str = Field(..., description="Account password", min_length=6)
    full_name: Optional[str] = Field(None, description="Full name of engineer")


class UserLoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    id: Optional[int] = None
    email: str
    username: str
    full_name: Optional[str] = None
    role: str = "engineer"
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MongoStatusResponse(BaseModel):
    connected: bool
    url: str
    database: str
    message: str
    collections: Dict[str, Any] = {}


# ==========================================
# Prediction & Change Analysis Schemas
# ==========================================

class DirectPredictRequest(BaseModel):
    # Core commit / MR metrics
    la: float = Field(..., description="Lines of code added", ge=0)
    ld: float = Field(..., description="Lines of code deleted", ge=0)
    nf: float = Field(..., description="Number of modified files", ge=1)
    nd: float = Field(..., description="Number of modified directories", ge=1)
    ns: float = Field(..., description="Number of modified subsystems", ge=1)
    ent: float = Field(..., description="Entropy of changes across files", ge=0.0)
    
    # Historical developer metrics (optional with defaults)
    ndev: Optional[float] = Field(2.0, description="Average developers associated with files", ge=0)
    age: Optional[float] = Field(30.0, description="Average age of code in days", ge=0)
    nuc: Optional[float] = Field(12.0, description="Number of unique changes to code", ge=0)
    aexp: Optional[float] = Field(100.0, description="Author total commit experience", ge=0)
    arexp: Optional[float] = Field(80.0, description="Author recent experience", ge=0)
    asexp: Optional[float] = Field(25.0, description="Author subsystem experience", ge=0)

    # Contextual metadata
    project_name: Optional[str] = Field("mergeguard/demo-repo", description="Git repository name")
    mr_iid: Optional[int] = Field(None, description="Merge Request IID/number")
    mr_title: Optional[str] = Field(None, description="Merge Request title")
    tests_modified: Optional[bool] = Field(None, description="Whether test files were modified")
    critical_modules: Optional[bool] = Field(None, description="Whether critical modules were touched")


class GitDiffPredictRequest(BaseModel):
    diff_text: str = Field(..., description="Raw unified git diff output (e.g., from git diff or GitLab)")
    project_name: Optional[str] = Field("mergeguard/git-diff", description="Git repository name")
    mr_iid: Optional[int] = Field(None, description="Merge Request IID")
    mr_title: Optional[str] = Field("Raw Git Diff Analysis", description="MR title or description")
    aexp: Optional[float] = Field(100.0, description="Author total experience")
    arexp: Optional[float] = Field(80.0, description="Author recent experience")
    asexp: Optional[float] = Field(25.0, description="Author subsystem experience")


class GitLabMRRequest(BaseModel):
    gitlab_url: Optional[str] = Field("https://gitlab.com", description="GitLab instance URL")
    project_id: str = Field(..., description="GitLab project path or ID (e.g. 'gitlab-org/gitlab')")
    mr_iid: int = Field(..., description="Merge Request IID")
    private_token: Optional[str] = Field(None, description="GitLab personal access token (optional for public repos)")


class RiskFactorItem(BaseModel):
    feature: str
    label: str
    value: str
    impact: str
    description: str
    weight: Optional[float] = None


class RiskPredictionResponse(BaseModel):
    id: Optional[int] = None
    project_name: str
    mr_iid: Optional[int] = None
    mr_title: Optional[str] = None
    risk_score: int = Field(..., description="Calibrated risk score between 0 and 100", ge=0, le=100)
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    defect_probability: float = Field(..., description="Calibrated model defect probability")
    top_risk_factors: List[RiskFactorItem]
    mitigating_factors: List[RiskFactorItem]
    recommendations: List[str]
    metrics_summary: Dict[str, Any]
    created_by_user: Optional[str] = None
    created_at: str


class PredictionListItem(BaseModel):
    id: int
    project_name: str
    mr_iid: Optional[int]
    mr_title: Optional[str]
    risk_score: int
    risk_level: str
    defect_probability: float
    created_at: str


class AnalyticsResponse(BaseModel):
    total_predictions: int
    avg_risk_score: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    high_risk_pct: float
    common_recommendations: List[Dict[str, Any]]
