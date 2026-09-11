"""
SQLAlchemy models matching the production schema from PRD Section 2.9
"""
import os
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, Column, String, Text, Numeric, Boolean,
    DateTime, Date, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
connect_args = {"connect_timeout": 8}
if DATABASE_URL and "sslmode" not in DATABASE_URL and "supabase" in DATABASE_URL:
    joiner = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{joiner}sslmode=require"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Enums ───────────────────────────────────────────────────────────────────

class RoleType(str, enum.Enum):
    INSPECTOR = "INSPECTOR"
    ADMIN = "ADMIN"


class CalibrationTier(str, enum.Enum):
    ARUCO = "ARUCO"
    ID_CARD = "ID_CARD"
    COIN = "COIN"
    NONE = "NONE"


class StatusType(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


# ─── Models ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(SAEnum(RoleType), default=RoleType.INSPECTOR)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scans = relationship("Scan", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="admin")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    barcode = Column(Text, unique=True, nullable=True)
    brand_name = Column(Text, nullable=False)
    manufacturer_details = Column(Text, nullable=True)
    category = Column(Text, nullable=False)
    surface_type = Column(Text, default="FLAT")

    scans = relationship("Scan", back_populates="product")


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    rule_code = Column(Text, nullable=False)
    source_clause = Column(Text, nullable=False)
    applies_to = Column(Text, nullable=True)
    condition = Column(Text, nullable=False)
    threshold = Column(Text, nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date, nullable=True)
    severity = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)

    violations = relationship("Violation", back_populates="rule_version")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    image_url = Column(Text, nullable=False)
    calibration_used = Column(SAEnum(CalibrationTier), nullable=False)
    px_per_mm_ratio = Column(Numeric(10, 4), nullable=True)
    overall_status = Column(SAEnum(StatusType), nullable=False)
    deployment_mode = Column(Text, default="HANDHELD")
    scanned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="scans")
    user = relationship("User", back_populates="scans")
    violations = relationship("Violation", back_populates="scan", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="scan", uselist=False, cascade="all, delete-orphan")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"))
    rule_version_id = Column(UUID(as_uuid=True), ForeignKey("rule_versions.id"), nullable=True)
    field_name = Column(Text, nullable=False)
    expected_value = Column(Text, nullable=True)
    detected_value = Column(Text, nullable=True)
    measured_height_mm = Column(Numeric(5, 2), nullable=True)
    required_height_mm = Column(Numeric(5, 2), nullable=True)
    status = Column(SAEnum(StatusType), nullable=False)
    confidence_score = Column(Numeric(4, 3), nullable=True)
    evidence_crop_url = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="violations")
    rule_version = relationship("RuleVersion", back_populates="violations")
    audit_logs = relationship("AuditLog", back_populates="violation", cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    violation_id = Column(UUID(as_uuid=True), ForeignKey("violations.id", ondelete="CASCADE"))
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action_taken = Column(Text, nullable=False)
    override_reason = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    violation = relationship("Violation", back_populates="audit_logs")
    admin = relationship("User", back_populates="audit_logs")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default="uuid_generate_v4()")
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"))
    pdf_url = Column(Text, nullable=True)
    docx_url = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scan = relationship("Scan", back_populates="report")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def create_tables():
    """Create all tables and seed statutory rules if not present."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(RuleVersion).count() == 0:
            import json
            import os
            from datetime import date
            rules_path = os.path.join(os.path.dirname(__file__), "..", "rules", "rules_v1.json")
            if os.path.exists(rules_path):
                with open(rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                eff_from = date.fromisoformat(data.get("effective_from", "2011-04-01"))
                for r in data.get("rules", []):
                    rv = RuleVersion(
                        rule_code=r["rule_code"],
                        source_clause=r["source_clause"],
                        applies_to=r.get("applies_to", "all"),
                        condition=r.get("condition", "statutory_requirement"),
                        threshold=r.get("description"),
                        effective_from=eff_from,
                        severity=r.get("severity", "HIGH"),
                        verified=r.get("verified", True),
                    )
                    db.add(rv)
                db.commit()
    except Exception as e:
        print(f"Warning during seed: {e}")
        db.rollback()
    finally:
        db.close()


def get_db():
    """FastAPI dependency — yields a DB session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
