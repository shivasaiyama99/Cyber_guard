"""
Pydantic models for all 5 MongoDB collections.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


# ─── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserInDB(BaseModel):
    name: str
    email: str
    hashed_password: str = ""
    googleId: Optional[str] = None
    profilePicture: Optional[str] = None
    authProvider: str = "local"
    role: str = "analyst"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    lastLogin: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profilePicture: Optional[str] = None
    authProvider: str = "local"
    created_at: datetime

    class Config:
        arbitrary_types_allowed = True


# ─── Sessions ──────────────────────────────────────────────────────────────────

class SessionModel(BaseModel):
    user_id: str
    token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

    class Config:
        arbitrary_types_allowed = True

class SessionResponse(BaseModel):
    id: str
    user_id: str
    token: str
    created_at: datetime
    expires_at: datetime

    class Config:
        arbitrary_types_allowed = True


# ─── Incidents ─────────────────────────────────────────────────────────────────

class IncidentModel(BaseModel):
    incident_id: str
    attack_type: Optional[str] = None
    risk_score: Optional[int] = None
    severity: Optional[str] = None
    source_ip: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "open"
    agent_notes: List[str] = []

    class Config:
        arbitrary_types_allowed = True

class IncidentResponse(BaseModel):
    id: str
    incident_id: str
    attack_type: Optional[str] = None
    risk_score: Optional[int] = None
    severity: Optional[str] = None
    source_ip: Optional[str] = None
    timestamp: datetime
    status: str
    agent_notes: List[str] = []

    class Config:
        arbitrary_types_allowed = True


# ─── Logs ──────────────────────────────────────────────────────────────────────

class LogModel(BaseModel):
    timestamp: Optional[str] = None
    ip_address: Optional[str] = None
    user: Optional[str] = None
    status: Optional[str] = None
    endpoint: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

class LogResponse(BaseModel):
    id: str
    timestamp: Optional[str] = None
    ip_address: Optional[str] = None
    user: Optional[str] = None
    status: Optional[str] = None
    endpoint: Optional[str] = None
    uploaded_at: datetime
    session_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


# ─── Reports ──────────────────────────────────────────────────────────────────

class ReportModel(BaseModel):
    incident_id: Optional[str] = None
    markdown_content: str
    structured_json: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

class ReportResponse(BaseModel):
    id: str
    incident_id: Optional[str] = None
    markdown_content: str
    structured_json: Dict[str, Any] = {}
    created_at: datetime
    created_by: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
