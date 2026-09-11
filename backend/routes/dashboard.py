"""Dashboard routes — admin only."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from models.database import get_db, Scan, Violation, Product, StatusType
from utils.auth_utils import decode_token, oauth2_scheme

router = APIRouter()


def require_admin(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if payload.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), payload=Depends(require_admin)):
    total_scans = db.query(Scan).count()
    pass_count = db.query(Scan).filter(Scan.overall_status == StatusType.PASS).count()
    fail_count = db.query(Scan).filter(Scan.overall_status == StatusType.FAIL).count()
    manual_count = db.query(Scan).filter(Scan.overall_status == StatusType.MANUAL_REVIEW).count()

    pass_rate = round((pass_count / total_scans * 100), 1) if total_scans > 0 else 0

    # Top violated fields
    top_fields = (
        db.query(Violation.field_name, func.count(Violation.id).label("count"))
        .filter(Violation.status == StatusType.FAIL)
        .group_by(Violation.field_name)
        .order_by(func.count(Violation.id).desc())
        .limit(6)
        .all()
    )

    # Calibration breakdown
    cal_breakdown = {}
    for tier in ["ARUCO", "ID_CARD", "COIN", "NONE"]:
        count = db.query(Scan).filter(Scan.calibration_used == tier).count()
        cal_breakdown[tier] = count

    # Scans over last 14 days
    from datetime import datetime, timedelta, timezone
    scans_over_time = []
    for i in range(13, -1, -1):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = db.query(Scan).filter(
            Scan.scanned_at >= day_start,
            Scan.scanned_at <= day_end,
        ).count()
        scans_over_time.append({
            "date": day.strftime("%d %b"),
            "scans": count,
        })

    return {
        "total_scans": total_scans,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "manual_review_count": manual_count,
        "pass_rate": pass_rate,
        "top_violated_fields": [{"field": f, "count": c} for f, c in top_fields],
        "calibration_breakdown": cal_breakdown,
        "scans_over_time": scans_over_time,
    }


@router.get("/rules")
def get_rules(db: Session = Depends(get_db), payload=Depends(require_admin)):
    """List all rules from the database (auto-seeds from rules_v1.json if empty)."""
    from models.database import RuleVersion, create_tables
    if db.query(RuleVersion).count() == 0:
        create_tables()

    rules = db.query(RuleVersion).order_by(RuleVersion.rule_code).all()
    return {"rules": [
        {
            "id": str(r.id),
            "rule_code": r.rule_code,
            "source_clause": r.source_clause,
            "condition": r.condition,
            "threshold": r.threshold,
            "severity": r.severity,
            "verified": r.verified,
            "effective_from": r.effective_from.isoformat() if r.effective_from else None,
            "effective_until": r.effective_until.isoformat() if r.effective_until else None,
        }
        for r in rules
    ]}


@router.patch("/rules/{rule_id}")
def update_rule(rule_id: str, updates: dict, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Update a rule (admin only). Changes are effective immediately."""
    from models.database import RuleVersion
    rule = db.query(RuleVersion).filter(RuleVersion.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    allowed_fields = {"source_clause", "condition", "threshold", "severity", "verified", "effective_until"}
    for key, val in updates.items():
        if key in allowed_fields:
            setattr(rule, key, val)

    db.commit()
    return {"ok": True, "message": f"Rule {rule.rule_code} updated"}
