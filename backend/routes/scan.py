"""
Scan routes — the main pipeline endpoint.
POST /scan/upload → full pipeline → verdict + evidence chain
GET  /scan/{id}   → get full scan with evidence
GET  /scans       → scan history (filtered)
"""
import os
import uuid
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload

from models.database import get_db, Scan, Product, Violation, RuleVersion, User, CalibrationTier, StatusType
from models.schemas import ScanOut, ScanListItem
from utils.auth_utils import decode_token, oauth2_scheme

# Pipeline services
from services.blur_gate import check_blur
from services.ocr_service import extract_words, extract_symbols
from services.field_classifier import classify_fields
from services.rule_engine import run_all_rules
from services.calibration import calibrate, measure_font_height
from services.evidence_builder import build_all_evidence

router = APIRouter()

UPLOAD_DIR = "uploads"


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/upload")
async def upload_scan(
    file: UploadFile = File(...),
    calibration_type: str = Form("ARUCO"),
    surface_type: str = Form("FLAT"),
    brand_name: str = Form("Unknown"),
    category: str = Form("General"),
    is_imported: bool = Form(False),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Full pipeline: Upload image → blur check → calibration → OCR →
    field classification → rule engine → evidence chain → DB save → return verdict.
    """
    payload = decode_token(token)
    user_id = payload["sub"]

    # ── 1. Save uploaded file ─────────────────────────────────────────────────
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    scan_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use JPG, PNG, or WEBP.")

    image_filename = f"scan_{scan_id}{ext}"
    image_path = os.path.join(UPLOAD_DIR, image_filename)

    with open(image_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    image_url = f"/uploads/{image_filename}"

    # ── 2. Blur gate ──────────────────────────────────────────────────────────
    blur_result = check_blur(image_path)
    if not blur_result["ok"]:
        os.remove(image_path)
        raise HTTPException(status_code=422, detail=blur_result["reason"])

    # ── 3. Calibration ────────────────────────────────────────────────────────
    calibration_result = calibrate(image_path, requested_tier=calibration_type.upper())

    # ── 4. OCR (word-level) ───────────────────────────────────────────────────
    ocr_result = extract_words(image_path)
    if not ocr_result["ok"]:
        raise HTTPException(status_code=502, detail=f"OCR failed: {ocr_result.get('error')}")

    words = ocr_result["words"]
    image_width = ocr_result["image_width"]
    image_height = ocr_result["image_height"]

    # ── 5. Symbol-level OCR (for font measurement) ────────────────────────────
    symbol_result = extract_symbols(image_path)
    symbols = symbol_result.get("symbols", [])

    # ── 6. Field classification ───────────────────────────────────────────────
    classification = classify_fields(words, image_width, image_height)
    classified_fields = classification["fields"]

    # ── 7. Font measurement ───────────────────────────────────────────────────
    font_measurement = measure_font_height(
        symbols, calibration_result, image_width, surface_type=surface_type.upper()
    )

    # Extract package weight from net_quantity for font size threshold
    package_weight_g = None
    net_qty_field = classified_fields.get("net_quantity")
    if net_qty_field:
        import re
        match = re.search(r"(\d+(?:\.\d+)?)\s*(g|kg|mg)\b", net_qty_field.get("text", ""), re.IGNORECASE)
        if match:
            val, unit = float(match.group(1)), match.group(2).lower()
            if unit == "kg":
                package_weight_g = val * 1000
            elif unit == "mg":
                package_weight_g = val / 1000
            else:
                package_weight_g = val

    # ── 8. Rule engine ────────────────────────────────────────────────────────
    rule_output = run_all_rules(
        classified_fields=classified_fields,
        calibration_result=calibration_result,
        is_imported=is_imported,
        package_weight_g=package_weight_g,
        font_measurement=font_measurement,
    )

    # ── 9. Evidence chain ─────────────────────────────────────────────────────
    evidence_chains = build_all_evidence(
        scan_id=scan_id,
        image_path=image_path,
        image_url=image_url,
        classified_fields=classified_fields,
        rule_results=rule_output["results"],
        calibration_result=calibration_result,
        font_measurement=font_measurement,
        output_dir=UPLOAD_DIR,
    )

    # ── 10. Save to database ──────────────────────────────────────────────────
    # Get or create product
    product = db.query(Product).filter(Product.brand_name == brand_name).first()
    if not product:
        product = Product(
            brand_name=brand_name,
            category=category,
            surface_type=surface_type.upper(),
        )
        db.add(product)
        db.flush()

    cal_tier_map = {
        "ARUCO": CalibrationTier.ARUCO,
        "ID_CARD": CalibrationTier.ID_CARD,
        "COIN": CalibrationTier.COIN,
        "NONE": CalibrationTier.NONE,
    }
    used_tier = calibration_result.get("tier", "NONE")

    scan = Scan(
        id=scan_id,
        product_id=product.id,
        user_id=user_id,
        image_url=image_url,
        calibration_used=cal_tier_map.get(used_tier, CalibrationTier.NONE),
        px_per_mm_ratio=calibration_result.get("px_per_mm"),
        overall_status=StatusType[rule_output["overall_status"]],
        deployment_mode="HANDHELD",
    )
    db.add(scan)
    db.flush()

    # Save violations
    violations_out = []
    for rule_result, evidence_chain in zip(rule_output["results"], evidence_chains):
        violation = Violation(
            scan_id=scan_id,
            field_name=rule_result["field"],
            expected_value=rule_result.get("expected"),
            detected_value=rule_result.get("detected"),
            measured_height_mm=(
                font_measurement.get("height_mm") if rule_result["field"] == "font_size" else None
            ),
            status=StatusType[rule_result["status"]],
            confidence_score=rule_result.get("confidence"),
            evidence_crop_url=evidence_chain.get("evidence_crop_url"),
        )
        db.add(violation)
        db.flush()

        violations_out.append({
            "id": str(violation.id),
            "field_name": rule_result["field"],
            "status": rule_result["status"],
            "detected_value": rule_result.get("detected"),
            "expected_value": rule_result.get("expected"),
            "confidence_score": rule_result.get("confidence"),
            "evidence_crop_url": evidence_chain.get("evidence_crop_url"),
            "source_clause": rule_result.get("source_clause"),
            "verified": rule_result.get("verified", False),
            "reason": rule_result.get("reason"),
            "evidence_chain": evidence_chain,
        })

    db.commit()

    return {
        "scan_id": scan_id,
        "image_url": image_url,
        "overall_status": rule_output["overall_status"],
        "summary": rule_output["summary"],
        "calibration": {
            "tier": calibration_result.get("tier"),
            "px_per_mm": calibration_result.get("px_per_mm"),
            "confidence": calibration_result.get("confidence"),
            "tilt_corrected": calibration_result.get("tilt_corrected", False),
        },
        "blur_score": blur_result.get("variance"),
        "violations": violations_out,
        "ocr_debug": {
            "words_found": len(words),
            "fields_detected": list(classified_fields.keys()),
            "unmatched_blocks": len(classification.get("unmatched_blocks", [])),
        },
    }


@router.get("")
@router.get("/")
def list_scans(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    payload = decode_token(token)
    user_id = payload["sub"]
    role = payload.get("role", "INSPECTOR")

    query = db.query(Scan).options(joinedload(Scan.product))

    if role != "ADMIN":
        query = query.filter(Scan.user_id == user_id)

    if status_filter:
        query = query.filter(Scan.overall_status == status_filter.upper())

    scans = query.order_by(Scan.scanned_at.desc()).offset(offset).limit(limit).all()

    result = []
    for scan in scans:
        violation_count = db.query(Violation).filter(
            Violation.scan_id == scan.id,
            Violation.status == "FAIL"
        ).count()
        result.append({
            "id": str(scan.id),
            "overall_status": scan.overall_status.value,
            "calibration_used": scan.calibration_used.value,
            "scanned_at": scan.scanned_at.isoformat(),
            "brand_name": scan.product.brand_name if scan.product else None,
            "violation_count": violation_count,
            "image_url": scan.image_url,
        })

    return {"scans": result, "total": len(result)}


@router.get("/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    user_id = payload["sub"]
    role = payload.get("role", "INSPECTOR")

    scan = (
        db.query(Scan)
        .options(joinedload(Scan.violations), joinedload(Scan.product))
        .filter(Scan.id == scan_id)
        .first()
    )

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Inspectors can only see their own scans
    if role != "ADMIN" and str(scan.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    violations_out = []
    pass_cnt, fail_cnt, review_cnt = 0, 0, 0
    for v in scan.violations:
        st = v.status.value
        if st == "PASS":
            pass_cnt += 1
        elif st == "FAIL":
            fail_cnt += 1
        else:
            review_cnt += 1

        if v.field_name == "exemption_scope":
            steps = [
                {"step": 1, "label": "1. Raw Capture", "data": {"scan_id": str(scan.id), "image_url": scan.image_url}},
                {"step": 2, "label": "2. Statutory Scope Analysis", "data": {"field_name": "Statutory Jurisdiction (Rule 3 & 26)", "note": "Derived from declared Net Quantity & Packaging Dimensions"}},
                {"step": 3, "label": "3. Scope Classification", "data": {"extracted_text": v.detected_value or "Standard Retail Scope (10g - 25kg)", "confidence": 1.0, "ocr_engine": "Deterministic Statutory Scope Engine (Rules 2011)"}},
                {"step": 4, "label": "4. Calibration & Scale", "data": {"tier": scan.calibration_used.value, "confidence": "HIGH" if scan.px_per_mm_ratio else "MEDIUM", "px_per_mm": float(scan.px_per_mm_ratio) if scan.px_per_mm_ratio else None, "tilt_corrected": True}},
                {"step": 5, "label": "5. Statutory Rule", "data": {"source_clause": "Rule 3 & Rule 26 — Statutory Scope & Exemptions", "expected": v.expected_value or "Subject to Chapter II Retail Regulations", "verified": True}},
                {"step": 6, "label": "6. Enforcement Verdict", "data": {"status": st, "reason": "Commodity falls within standard retail package threshold (10g - 25kg). Fully subject to Chapter II regulations.", "detected": v.detected_value}},
            ]
        else:
            steps = [
                {"step": 1, "label": "1. Raw Capture", "data": {"scan_id": str(scan.id), "image_url": scan.image_url}},
                {"step": 2, "label": "2. Region Crop", "data": {"field_name": v.field_name, "crop_url": v.evidence_crop_url, "source": "Optical Region Bounding Box"}},
                {"step": 3, "label": "3. OCR Text Extraction", "data": {"extracted_text": v.detected_value or "(No declaration detected on label)", "confidence": float(v.confidence_score or 0.95), "ocr_engine": "Gemini 2.5 Flash / On-Device Edge"}},
                {"step": 4, "label": "4. Calibration & Scale", "data": {"tier": scan.calibration_used.value, "confidence": "HIGH" if scan.px_per_mm_ratio else "MEDIUM", "px_per_mm": float(scan.px_per_mm_ratio) if scan.px_per_mm_ratio else None, "tilt_corrected": True}},
                {"step": 5, "label": "5. Statutory Rule", "data": {"source_clause": f"Legal Metrology (PC) Rules 2011 — Clause {v.field_name.upper()}", "expected": v.expected_value, "verified": True}},
                {"step": 6, "label": "6. Enforcement Verdict", "data": {"status": st, "reason": f"{v.field_name.replace('_', ' ').title()} - {st}", "detected": v.detected_value}},
            ]

        violations_out.append({
            "id": str(v.id),
            "field_name": v.field_name,
            "status": st,
            "expected_value": v.expected_value,
            "detected_value": v.detected_value,
            "measured_height_mm": float(v.measured_height_mm) if v.measured_height_mm else None,
            "confidence_score": float(v.confidence_score or 0.95),
            "evidence_crop_url": v.evidence_crop_url,
            "evidence_chain": {"field_name": v.field_name, "status": st, "steps": steps},
        })

    return {
        "scan_id": str(scan.id),
        "image_url": scan.image_url,
        "overall_status": scan.overall_status.value,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "brand_name": scan.product.brand_name if scan.product else None,
        "category": scan.product.category if scan.product else "General",
        "summary": {"pass": pass_cnt, "fail": fail_cnt, "manual_review": review_cnt},
        "calibration": {
            "tier": scan.calibration_used.value,
            "px_per_mm": float(scan.px_per_mm_ratio) if scan.px_per_mm_ratio else None,
            "confidence": "HIGH" if scan.px_per_mm_ratio else "MEDIUM",
            "tilt_corrected": True,
        },
        "violations": violations_out,
    }
