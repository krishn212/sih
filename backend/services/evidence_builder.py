"""
Evidence Builder — Phase 3
Assembles the full evidence chain per violation:
  Image → Region → OCR Text → Measurement → Rule Clause → Decision

This chain is the signature feature of the system (PRD Section 2.5).
Every violation must have a fully traceable evidence chain.
"""
import os
import uuid
from typing import Optional

import cv2
import numpy as np


def crop_evidence_region(
    image_path: str,
    bounding_box: dict,
    output_dir: str = "uploads",
    padding: int = 20,
) -> Optional[str]:
    """
    Crops the evidence region from the original image and saves it.

    Args:
        image_path: Path to the full label image.
        bounding_box: {"x": int, "y": int, "width": int, "height": int}
        output_dir: Directory to save the crop.
        padding: Extra pixels around the box for readability.

    Returns:
        Relative path to the saved crop, or None on failure.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None

    h, w = image.shape[:2]
    x = max(0, bounding_box.get("x", 0) - padding)
    y = max(0, bounding_box.get("y", 0) - padding)
    x2 = min(w, x + bounding_box.get("width", 0) + padding * 2)
    y2 = min(h, y + bounding_box.get("height", 0) + padding * 2)

    crop = image[y:y2, x:x2]
    if crop.size == 0:
        return None

    os.makedirs(output_dir, exist_ok=True)
    filename = f"evidence_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, crop)

    return f"/uploads/{filename}"


def build_evidence_chain(
    scan_id: str,
    field_name: str,
    image_path: str,
    image_url: str,
    classified_field: Optional[dict],
    rule_result: dict,
    calibration_result: Optional[dict],
    font_measurement: Optional[dict],
    output_dir: str = "uploads",
) -> dict:
    """
    Builds the complete evidence chain for one violation/field check.

    Returns:
        {
            "violation_id": str,
            "field_name": str,
            "steps": [...],  # ordered evidence steps
            "overall_status": str,
            "evidence_crop_url": str or None,
        }
    """
    steps = []
    evidence_crop_url = None

    # ── Step 1: Original image ────────────────────────────────────────────────
    steps.append({
        "step": 1,
        "label": "📷 Original Scan",
        "data": {
            "image_url": image_url,
            "scan_id": scan_id,
        },
    })

    # ── Step 2: Detected region ───────────────────────────────────────────────
    bounding_box = None
    if classified_field:
        bounding_box = classified_field.get("bounding_box")

    if field_name == "exemption_scope":
        steps.append({
            "step": 2,
            "label": "📍 Statutory Scope Analysis",
            "data": {
                "field_name": "Statutory Jurisdiction (Rule 3 & 26)",
                "bounding_box": None,
                "note": "Derived from declared Net Quantity & Packaging Dimensions (Rule 3 & 26 threshold audit)",
            },
        })
        steps.append({
            "step": 3,
            "label": "📝 Scope Classification",
            "data": {
                "text": rule_result.get("detected") or "Standard Retail Package Scope (10g - 25kg)",
                "confidence": 1.0,
                "ocr_engine": "Deterministic Statutory Scope Engine (Rules 2011)",
            },
        })
    elif bounding_box:
        crop_path = crop_evidence_region(image_path, bounding_box, output_dir)
        if crop_path:
            evidence_crop_url = crop_path

        steps.append({
            "step": 2,
            "label": f"📍 Detected Region — {field_name.replace('_', ' ').title()}",
            "data": {
                "field_name": field_name,
                "bounding_box": bounding_box,
                "crop_url": evidence_crop_url,
                "source": classified_field.get("source", "unknown"),
            },
        })
        ocr_text = classified_field.get("text") if classified_field else None
        ocr_confidence = classified_field.get("confidence", 0.0) if classified_field else 0.0
        steps.append({
            "step": 3,
            "label": "📝 Extracted Text (OCR)",
            "data": {
                "text": ocr_text or "— not detected —",
                "confidence": round(ocr_confidence, 3),
                "ocr_engine": "Google Cloud Vision / Gemini 2.5 Flash",
            },
        })
    else:
        steps.append({
            "step": 2,
            "label": f"📍 Region — {field_name.replace('_', ' ').title()}",
            "data": {
                "field_name": field_name,
                "bounding_box": None,
                "note": "Declaration not found on visible package surface",
            },
        })
        ocr_text = classified_field.get("text") if classified_field else None
        ocr_confidence = classified_field.get("confidence", 0.0) if classified_field else 0.0
        steps.append({
            "step": 3,
            "label": "📝 Extracted Text (OCR)",
            "data": {
                "text": ocr_text or "— not detected —",
                "confidence": round(ocr_confidence, 3),
                "ocr_engine": "Google Cloud Vision / Gemini 2.5 Flash",
            },
        })

    # ── Step 4: Measurement (font size if applicable) ─────────────────────────
    if font_measurement and field_name == "font_size":
        steps.append({
            "step": 4,
            "label": "📏 Font Size Measurement",
            "data": {
                "measured_height_mm": font_measurement.get("height_mm"),
                "calibration_tier": calibration_result.get("tier") if calibration_result else "NONE",
                "calibration_confidence": calibration_result.get("confidence", "LOW") if calibration_result else "LOW",
                "px_per_mm": calibration_result.get("px_per_mm") if calibration_result else None,
                "tilt_corrected": calibration_result.get("tilt_corrected", False) if calibration_result else False,
                "symbols_measured": font_measurement.get("symbols_measured", 0),
            },
        })
    elif calibration_result:
        steps.append({
            "step": 4,
            "label": "📏 Calibration Used",
            "data": {
                "tier": calibration_result.get("tier"),
                "px_per_mm": calibration_result.get("px_per_mm"),
                "confidence": calibration_result.get("confidence"),
                "tilt_corrected": calibration_result.get("tilt_corrected", False),
            },
        })

    # ── Step 5: Rule clause ───────────────────────────────────────────────────
    steps.append({
        "step": 5 if calibration_result else 4,
        "label": "⚖️ Applicable Rule",
        "data": {
            "rule_code": rule_result.get("rule_code"),
            "source_clause": rule_result.get("source_clause"),
            "expected": rule_result.get("expected"),
            "verified": rule_result.get("verified", False),
            "unverified_warning": (
                "⚠️ This rule has not been verified against the actual Rules 2011 text."
                if not rule_result.get("verified", False)
                else None
            ),
        },
    })

    # ── Step 6: Decision ─────────────────────────────────────────────────────
    status = rule_result.get("status", "MANUAL_REVIEW")
    status_icon = {"PASS": "✅", "FAIL": "❌", "MANUAL_REVIEW": "⚠️"}.get(status, "❓")

    steps.append({
        "step": 6 if calibration_result else 5,
        "label": f"{status_icon} Decision: {status}",
        "data": {
            "status": status,
            "reason": rule_result.get("reason"),
            "detected": rule_result.get("detected"),
            "expected": rule_result.get("expected"),
            "confidence": rule_result.get("confidence"),
        },
    })

    return {
        "violation_id": str(uuid.uuid4()),
        "field_name": field_name,
        "steps": steps,
        "overall_status": status,
        "evidence_crop_url": evidence_crop_url,
    }


def build_all_evidence(
    scan_id: str,
    image_path: str,
    image_url: str,
    classified_fields: dict,
    rule_results: list,
    calibration_result: Optional[dict],
    font_measurement: Optional[dict],
    output_dir: str = "uploads",
) -> list:
    """
    Builds evidence chains for all rule results.

    Returns:
        List of evidence chain dicts, one per rule result.
    """
    chains = []

    for rule_result in rule_results:
        field_name = rule_result.get("field", "unknown")
        classified_field = classified_fields.get(field_name)

        chain = build_evidence_chain(
            scan_id=scan_id,
            field_name=field_name,
            image_path=image_path,
            image_url=image_url,
            classified_field=classified_field,
            rule_result=rule_result,
            calibration_result=calibration_result,
            font_measurement=font_measurement,
            output_dir=output_dir,
        )
        chains.append(chain)

    return chains
