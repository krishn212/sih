"""
Pydantic schemas for request/response validation.
Kept separate from SQLAlchemy models (models/database.py).
"""
from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "INSPECTOR"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: str


# ─── OCR / Pipeline ──────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class OCRWord(BaseModel):
    text: str
    confidence: float
    bounding_box: BoundingBox


class ClassifiedField(BaseModel):
    field_name: str
    text: str
    confidence: float
    bounding_box: BoundingBox
    source: str  # "regex", "keyword", "spatial", "yolo"


class RuleResult(BaseModel):
    field: str
    status: str              # PASS | FAIL | MANUAL_REVIEW
    rule_code: str
    source_clause: str
    detected: Optional[str]
    expected: Optional[str]
    confidence: float
    reason: str
    bounding_box: Optional[BoundingBox]
    verified: bool           # whether the rule has been verified against actual Rules 2011 text


# ─── Evidence Chain ──────────────────────────────────────────────────────────

class EvidenceStep(BaseModel):
    step: int
    label: str
    data: dict


class EvidenceChain(BaseModel):
    violation_id: Optional[str]
    field_name: str
    steps: List[EvidenceStep]
    overall_status: str


# ─── Scan ────────────────────────────────────────────────────────────────────

class ScanCreate(BaseModel):
    calibration_type: str   # ARUCO | ID_CARD | COIN | NONE
    surface_type: str       # FLAT | CURVED
    brand_name: Optional[str] = "Unknown"
    category: Optional[str] = "General"
    barcode: Optional[str] = None


class ViolationOut(BaseModel):
    id: str
    field_name: str
    status: str
    detected_value: Optional[str]
    expected_value: Optional[str]
    measured_height_mm: Optional[float]
    required_height_mm: Optional[float]
    confidence_score: Optional[float]
    evidence_crop_url: Optional[str]
    source_clause: Optional[str]
    verified: Optional[bool]
    evidence_chain: Optional[EvidenceChain]

    class Config:
        from_attributes = True


class ScanOut(BaseModel):
    id: str
    image_url: str
    overall_status: str
    calibration_used: str
    px_per_mm_ratio: Optional[float]
    scanned_at: datetime
    brand_name: Optional[str]
    category: Optional[str]
    violations: List[ViolationOut]

    class Config:
        from_attributes = True


class ScanListItem(BaseModel):
    id: str
    overall_status: str
    calibration_used: str
    scanned_at: datetime
    brand_name: Optional[str]
    violation_count: int

    class Config:
        from_attributes = True


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_scans: int
    pass_count: int
    fail_count: int
    manual_review_count: int
    pass_rate: float
    top_violated_fields: List[dict]
    scans_over_time: List[dict]
    calibration_breakdown: dict


# ─── Rules Management ────────────────────────────────────────────────────────

class RuleOut(BaseModel):
    id: str
    rule_code: str
    source_clause: str
    applies_to: Optional[str]
    condition: str
    threshold: Optional[str]
    effective_from: date
    effective_until: Optional[date]
    severity: Optional[str]
    verified: bool

    class Config:
        from_attributes = True


class RuleUpdate(BaseModel):
    source_clause: Optional[str]
    condition: Optional[str]
    threshold: Optional[str]
    severity: Optional[str]
    verified: Optional[bool]
    effective_until: Optional[date]


# ─── Admin override ──────────────────────────────────────────────────────────

class OverrideRequest(BaseModel):
    action_taken: str    # OVERRIDDEN_PASS | CONFIRMED_FAIL
    override_reason: str
