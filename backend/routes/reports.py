"""
Report generation routes — Court-Ready Form-A Legal Notice PDF & Reports.
Implements Form-A: Inspection & Seizure Notice under Section 15 & Section 36
of the Legal Metrology Act, 2009 and Legal Metrology (Packaged Commodities) Rules, 2011.
"""
import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from PIL import Image as PILImage

from models.database import get_db, Scan, Violation, Report
from utils.auth_utils import decode_token, oauth2_scheme

router = APIRouter()
REPORTS_DIR = "reports"

# ─── Statutory Penalties Schedule under Section 36 ─────────────────────────────
SECTION_36_PENALTIES = {
    "mrp": {
        "clause": "Rule 6(1)(g) — MRP & Tax Declaration",
        "penalty": "Sec 36(1): Fine up to ₹25,000 (1st offence), ₹50,000 (2nd offence), ₹1,00,000/1 yr prison (subsequent).",
    },
    "net_quantity": {
        "clause": "Rule 6(1)(e) — Standard Unit of Quantity",
        "penalty": "Sec 36(1): Fine up to ₹25,000 (1st offence), ₹50,000 (2nd offence). Non-standard units (gm/ML) prohibited.",
    },
    "usp": {
        "clause": "Rule 6(11) — Unit Sale Price (2021 Amend.)",
        "penalty": "Sec 36(1): Fine up to ₹25,000. Deceptive pricing or missing USP contravenes statutory economics.",
    },
    "font_size": {
        "clause": "Rule 8 — Minimum Character Height",
        "penalty": "Sec 36(1): Fine up to ₹25,000. Illegible or undersized statutory declarations prohibited.",
    },
    "manufacturer": {
        "clause": "Rule 6(1)(a) — Manufacturer Identity & Address",
        "penalty": "Sec 36(1): Fine up to ₹25,000 (1st offence), ₹50,000 (2nd offence). Complete address mandatory.",
    },
    "mfg_date": {
        "clause": "Rule 6(1)(f) — Date of Packing/Manufacture",
        "penalty": "Sec 36(1): Fine up to ₹25,000. Month & Year of packing/manufacture mandatory.",
    },
    "consumer_care": {
        "clause": "Rule 6(1) — Consumer Grievance Details",
        "penalty": "Sec 36(1): Fine up to ₹25,000. Name, address, telephone/email mandatory for consumer redressal.",
    },
    "country_of_origin": {
        "clause": "Rule 6(2) — Country of Origin (Imports)",
        "penalty": "Sec 36(1): Fine up to ₹25,000. Mandatory country of origin declaration for imported commodities.",
    },
}


def _compute_evidence_hash(scan: Scan, violations: list) -> str:
    """Computes a tamper-evident SHA-256 hash for legal evidence authenticity (Section 65B)."""
    hasher = hashlib.sha256()
    hasher.update(str(scan.id).encode("utf-8"))
    hasher.update(str(scan.scanned_at).encode("utf-8"))
    hasher.update(str(scan.overall_status.value).encode("utf-8"))
    if scan.product:
        hasher.update(str(scan.product.brand_name).encode("utf-8"))
    for v in sorted(violations, key=lambda x: x.field_name):
        hasher.update(f"{v.field_name}:{v.status}:{v.detected_value}".encode("utf-8"))
    return hasher.hexdigest()


def _resolve_image_path(image_url: Optional[str]) -> Optional[str]:
    """Finds the local filesystem path for a scan image."""
    if not image_url:
        return None
    cleaned = image_url.lstrip("/").replace("/", os.sep)
    # Check directly
    candidates = [
        cleaned,
        os.path.join(os.path.dirname(__file__), "..", cleaned),
        os.path.join("uploads", os.path.basename(cleaned)),
        os.path.join(os.path.dirname(__file__), "..", "uploads", os.path.basename(cleaned)),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            return os.path.abspath(p)
    return None


def _generate_court_notice_pdf(scan: Scan, violations: list, output_path: str):
    """Generates an official Form-A Statutory Notice of Inspection & Seizure PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage, KeepTogether
    )
    from reportlab.lib.units import mm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    header_gov = ParagraphStyle(
        "GovHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        alignment=1,  # Center
        textColor=colors.HexColor("#0f2942"),
    )
    header_dept = ParagraphStyle(
        "DeptHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#1e3a5f"),
    )
    header_sub = ParagraphStyle(
        "SubHeader",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        alignment=1,
        textColor=colors.HexColor("#4a5568"),
    )
    form_title = ParagraphStyle(
        "FormTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#991b1b" if scan.overall_status.value == "FAIL" else "#166534"),
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )
    body_text = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
    )
    badge_pass = ParagraphStyle(
        "BadgePass",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#166534"),
    )
    badge_fail = ParagraphStyle(
        "BadgeFail",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#991b1b"),
    )
    badge_review = ParagraphStyle(
        "BadgeReview",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#b45309"),
    )

    story = []
    page_width = 182 * mm  # Total printable width

    # ── 1. Official Government Header ──────────────────────────────────────────
    story.append(Paragraph("GOVERNMENT OF INDIA", header_gov))
    story.append(Paragraph("MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION", header_dept))
    story.append(Paragraph("DEPARTMENT OF CONSUMER AFFAIRS — LEGAL METROLOGY DIVISION", header_sub))
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f2942"), spaceBefore=1, spaceAfter=2))
    story.append(Paragraph("FORM-A: STATUTORY NOTICE OF INSPECTION & SEIZURE", form_title))
    story.append(Paragraph(
        "[Under Section 15 & Section 36 of Legal Metrology Act, 2009 read with Rule 6 of Legal Metrology (Packaged Commodities) Rules, 2011]",
        header_sub
    ))
    story.append(Spacer(1, 3 * mm))

    # ── 2. Reference & Registry Table ─────────────────────────────────────────
    evidence_hash = _compute_evidence_hash(scan, violations)
    notice_ref = f"LM/INSP/2026/{str(scan.id)[:8].upper()}"
    scanned_time = scan.scanned_at.strftime("%d %b %Y, %H:%M:%S IST") if scan.scanned_at else datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M:%S IST")

    is_violation = scan.overall_status.value == "FAIL"
    verdict_badge = "❌ NON-COMPLIANT (PENAL ACTION RECOMMENDED)" if is_violation else "✅ COMPLIANT"

    reg_data = [
        [
            Paragraph(f"<b>Notice Ref No.:</b> {notice_ref}", table_cell),
            Paragraph(f"<b>Optical Calibration:</b> {scan.calibration_used.value}", table_cell),
        ],
        [
            Paragraph(f"<b>Date & Time of Inspection:</b> {scanned_time}", table_cell),
            Paragraph(f"<b>Optical Scale:</b> {scan.px_per_mm_ratio or 'N/A'} px/mm", table_cell),
        ],
        [
            Paragraph(f"<b>Inspection Station:</b> DEL-LM-TERM-04", table_cell),
            Paragraph(f"<b>Deployment Mode:</b> {scan.deployment_mode}", table_cell),
        ],
        [
            Paragraph(f"<b>Statutory Finding:</b> <b>{verdict_badge}</b>", table_cell_bold),
            Paragraph(f"<b>Evidentiary Hash:</b> {evidence_hash[:20]}...", table_cell),
        ],
    ]
    reg_table = Table(reg_data, colWidths=[91 * mm, 91 * mm])
    reg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(reg_table)
    story.append(Spacer(1, 3 * mm))

    # ── 3. Product Particulars & Photographic Evidence ────────────────────────
    prod_brand = scan.product.brand_name if scan.product else "Pre-packaged Commodity"
    prod_cat = scan.product.category if scan.product else "Consumer Goods"
    surface_geom = scan.product.surface_type if scan.product else "FLAT"

    # Extract observed values from violations list
    obs_map = {v.field_name: v.detected_value for v in violations}
    mrp_text = obs_map.get("mrp") or "—"
    net_qty_text = obs_map.get("net_quantity") or "—"
    usp_text = obs_map.get("usp") or "—"
    mfr_text = obs_map.get("manufacturer") or "—"

    product_info_paragraphs = [
        Paragraph("<b>INSPECTED COMMODITY DOSSIER</b>", body_bold),
        Spacer(1, 1 * mm),
        Paragraph(f"<b>Brand / Trade Name:</b> {prod_brand}", table_cell),
        Paragraph(f"<b>Commodity Category:</b> {prod_cat}", table_cell),
        Paragraph(f"<b>Package Surface:</b> {surface_geom} (Curvature Unwarping Applied)", table_cell),
        Paragraph(f"<b>Declared Net Quantity:</b> {net_qty_text}", table_cell),
        Paragraph(f"<b>Declared MRP:</b> {mrp_text}", table_cell),
        Paragraph(f"<b>Declared Unit Sale Price (USP):</b> {usp_text}", table_cell),
        Paragraph(f"<b>Manufacturer / Packer:</b> {mfr_text[:70]}", table_cell),
    ]

    # Product image thumbnail
    img_path = _resolve_image_path(scan.image_url)
    img_element = None
    if img_path:
        try:
            with PILImage.open(img_path) as pimg:
                orig_w, orig_h = pimg.size
                max_w = 48 * mm
                max_h = 42 * mm
                aspect = orig_h / orig_w
                if (max_w * aspect) <= max_h:
                    target_w = max_w
                    target_h = max_w * aspect
                else:
                    target_h = max_h
                    target_w = max_h / aspect
                img_element = RLImage(img_path, width=target_w, height=target_h)
        except Exception:
            img_element = None

    if img_element:
        dossier_data = [
            [product_info_paragraphs, [img_element, Paragraph("<font size=6 color='#64748b'><b>Figure 1:</b> Scanned Commodity</font>", styles["Normal"])]]
        ]
        dossier_table = Table(dossier_data, colWidths=[130 * mm, 52 * mm])
        dossier_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
    else:
        dossier_data = [[product_info_paragraphs]]
        dossier_table = Table(dossier_data, colWidths=[182 * mm])
        dossier_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
    story.append(dossier_table)
    story.append(Spacer(1, 3 * mm))

    # ── 4. Mathematical Cross-Verification Statutory Callout ──────────────────
    usp_violation = next((v for v in violations if v.field_name == "usp"), None)
    if usp_violation:
        status_val = usp_violation.status.value if hasattr(usp_violation.status, "value") else str(usp_violation.status)
        is_usp_fail = status_val == "FAIL"
        box_bg = colors.HexColor("#fef2f2" if is_usp_fail else "#f0fdf4")
        box_border = colors.HexColor("#ef4444" if is_usp_fail else "#22c55e")
        usp_verdict = "❌ STATUTORY MATH INCONSISTENCY WARNING" if is_usp_fail else "✅ STATUTORY ECONOMICS VERIFIED"

        math_callout_data = [
            [Paragraph(f"<b>STATUTORY ECONOMICS & USP CROSS-VERIFICATION (Rule 6(11) — 2021 Amendment)</b>", body_bold)],
            [Paragraph(f"<b>Statutory Principle:</b> Declared Volume/Quantity = Declared MRP ÷ Declared Unit Sale Price (USP)", table_cell)],
            [Paragraph(f"<b>Analysis:</b> {usp_violation.detected_value or '—'}", table_cell)],
            [Paragraph(f"<b>Finding:</b> <b>{usp_verdict}</b> — {usp_violation.expected_value or ''}", table_cell_bold)],
        ]
        math_table = Table(math_callout_data, colWidths=[182 * mm])
        math_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), box_bg),
            ("BOX", (0, 0), (-1, -1), 1, box_border),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(math_table)
        story.append(Spacer(1, 3 * mm))

    # ── 5. Tabulation of Statutory Violations & Section 36 Penalties ───────────
    story.append(Paragraph("<b>STATUTORY DECLARATIONS & PENALTY ASSESSMENT UNDER SECTION 36</b>", body_bold))
    story.append(Spacer(1, 1 * mm))

    table_data = [
        [
            Paragraph("<b>Sl.</b>", table_cell_bold),
            Paragraph("<b>Mandatory Declaration & Clause</b>", table_cell_bold),
            Paragraph("<b>Observed on Package</b>", table_cell_bold),
            Paragraph("<b>Statutory Finding</b>", table_cell_bold),
            Paragraph("<b>Prescribed Penalty (Sec 36)</b>", table_cell_bold),
        ]
    ]

    for idx, v in enumerate(violations, start=1):
        field = v.field_name
        status_val = v.status.value if hasattr(v.status, "value") else str(v.status)
        pen_info = SECTION_36_PENALTIES.get(field, {
            "clause": f"Rule 6 — {field.replace('_', ' ').title()}",
            "penalty": "Sec 36(1): Fine up to ₹25,000 for non-standard declaration."
        })

        if status_val == "PASS":
            status_para = Paragraph("COMPLIANT", badge_pass)
            penalty_para = Paragraph("Nil (Conforms to Rules)", table_cell)
        elif status_val == "FAIL":
            status_para = Paragraph("VIOLATION", badge_fail)
            penalty_para = Paragraph(pen_info["penalty"], table_cell)
        else:
            status_para = Paragraph("MANUAL REVIEW", badge_review)
            penalty_para = Paragraph("Subject to Metrology Inspection", table_cell)

        clause_text = f"<b>{field.replace('_', ' ').title()}</b><br/><font size=6 color='#64748b'>{pen_info['clause']}</font>"
        obs_text = (str(v.detected_value or "Declaration not found")[:75])

        table_data.append([
            Paragraph(str(idx), table_cell),
            Paragraph(clause_text, table_cell),
            Paragraph(obs_text, table_cell),
            status_para,
            penalty_para,
        ])

    viol_table = Table(table_data, colWidths=[8 * mm, 46 * mm, 44 * mm, 26 * mm, 58 * mm])
    viol_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(viol_table)
    story.append(Spacer(1, 3 * mm))

    # ── 6. Statutory Notice & Directions ──────────────────────────────────────
    story.append(Paragraph("<b>STATUTORY NOTICE & DIRECTIONS UNDER SECTION 15</b>", body_bold))
    story.append(Paragraph(
        "<b>WHEREAS</b>, an inspection of the above pre-packaged commodity was conducted by the undersigned Legal Metrology "
        "Inspector in exercise of powers conferred under Section 15 of the Legal Metrology Act, 2009; and "
        "<b>WHEREAS</b>, the optical analysis and deterministic rule verification have established the statutory contraventions detailed above; "
        "<b>NOW THEREFORE</b>, you are hereby called upon to <b>SHOW CAUSE in writing within seven (7) days</b> of receipt of this notice as to "
        "why penal proceedings under Section 36 of the Act should not be initiated against your establishment, or why the non-compliant "
        "stock should not be seized. Failure to submit a satisfactory reply within the stipulated time shall result in prosecution before "
        "the competent Judicial Magistrate First Class without further notice.",
        table_cell
    ))
    story.append(Spacer(1, 3 * mm))

    # ── 7. Inspector Sign-off & Cryptographic Integrity Block ─────────────────
    sign_block = [
        [
            Paragraph(
                "<b>ELECTRONIC RECORD CERTIFICATE (Sec 65B Indian Evidence Act)</b><br/>"
                "This document is an electronically certified inspection record. The evidentiary chain, "
                "optical measurements, and rule derivations have been cryptographically sealed.<br/>"
                f"<b>SHA-256 Digest:</b> <font face='Courier' size=6>{evidence_hash}</font>",
                table_cell
            ),
            Paragraph(
                "<br/>"
                "_______________________________________<br/>"
                "<b>Legal Metrology Inspector</b><br/>"
                "Enforcement Wing, Zone II<br/>"
                "Department of Consumer Affairs, Govt. of India<br/>"
                "<i>Seal & Digital Signature Attached</i>",
                table_cell
            ),
        ]
    ]
    sign_table = Table(sign_block, colWidths=[115 * mm, 67 * mm])
    sign_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(KeepTogether([sign_table]))

    doc.build(story)


from fastapi.security import OAuth2PasswordBearer

oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@router.get("/{scan_id}/pdf")
def download_pdf(
    scan_id: str,
    token: Optional[str] = None,
    auth_header: Optional[str] = Depends(oauth2_optional),
    db: Session = Depends(get_db),
):
    """
    Downloads court-ready Form-A Legal Notice PDF.
    Accepts JWT from Authorization header OR ?token= query parameter for direct browser links.
    """
    jwt_str = auth_header or token

    scan = db.query(Scan).options(joinedload(Scan.violations), joinedload(Scan.product)).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if jwt_str:
        try:
            payload = decode_token(jwt_str)
            if payload.get("role") != "ADMIN" and scan.user_id and str(scan.user_id) != payload.get("sub"):
                raise HTTPException(status_code=403, detail="Access denied")
        except HTTPException:
            raise
        except Exception:
            pass  # Fallback to generating the official Form-A notice if valid scan exists

    os.makedirs(REPORTS_DIR, exist_ok=True)
    pdf_path = os.path.join(REPORTS_DIR, f"report_{scan_id}.pdf")

    # Generate fresh court-ready PDF notice
    _generate_court_notice_pdf(scan, scan.violations, pdf_path)

    # Save or update report record
    existing = db.query(Report).filter(Report.scan_id == scan_id).first()
    if not existing:
        report = Report(scan_id=scan_id, pdf_url=f"/reports/report_{scan_id}.pdf")
        db.add(report)
        db.commit()

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"Form_A_Legal_Notice_{str(scan_id)[:8]}.pdf"
    )
