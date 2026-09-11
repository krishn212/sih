"""
Deterministic Rule Engine — Phase 1, Step 4
PRD Section 2.6: "Rules are versioned structured data, not hardcoded conditionals."

Design principles (from PRD):
  - Each rule is an independently testable function
  - Returns PASS / FAIL / MANUAL_REVIEW — never fabricates a number
  - Low-confidence input → MANUAL_REVIEW, never a guess
  - Every result references the exact rule clause (for evidence chain)
"""
import json
import re
import os
from typing import Optional

# Load rules from versioned JSON (not hardcoded)
RULES_FILE = os.path.join(os.path.dirname(__file__), "..", "rules", "rules_v1.json")

def _load_rules() -> dict:
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_rule(rule_code: str) -> Optional[dict]:
    data = _load_rules()
    for rule in data["rules"]:
        if rule["rule_code"] == rule_code:
            return rule
    return None


# ─── Individual Rule Functions ────────────────────────────────────────────────

def check_mrp(field_data: Optional[dict], full_text: Optional[str] = None) -> dict:
    """R001 — MRP must be present and correctly formatted."""
    rule = _get_rule("R001")

    if not field_data or not field_data.get("text"):
        return {
            "field": "mrp",
            "status": "FAIL",
            "rule_code": "R001",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "MRP with price and 'inclusive of all taxes'",
            "confidence": 1.0,
            "reason": "MRP declaration not found on label",
            "verified": rule["verified"],
        }

    text = field_data["text"]
    confidence = field_data.get("confidence", 0.0)

    # Low confidence → manual review
    if confidence < 0.5:
        return {
            "field": "mrp",
            "status": "MANUAL_REVIEW",
            "rule_code": "R001",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "MRP with price and 'inclusive of all taxes'",
            "confidence": confidence,
            "reason": "OCR confidence too low for reliable MRP extraction — manual verification required",
            "verified": rule["verified"],
        }

    # Check: has a price value (support parentheses like (₹), colons, INR/Rs/₹, and /-)
    has_price = bool(
        re.search(r"(?i)(?:maximum\s+retail\s+price|max\.?\s*retail\s+price|m\.?r\.?p\.?)[^0-9\n\r]{0,35}\d+(?:\.\d{1,2})?", text)
        or re.search(r"(?i)(?:Rs\.?|₹|INR|Rupees)\s*:?\s*\d+(?:\.\d{1,2})?", text)
        or re.search(r"\b\d+(?:\.\d{1,2})?\s*/-", text)
        or re.search(rule.get("required_pattern", ""), text, re.IGNORECASE)
    )

    # Check: mentions inclusive of all taxes in field text OR package context
    combined = text
    if full_text:
        combined = text + " " + str(full_text)
    has_inclusive = bool(
        re.search(r"(?i)(?:inclusive\s+of\s+all\s+taxes|incl\.?\s+of\s+all\s+taxes|incl\b.*tax|inclusive.*tax|\btaxes\b)", combined)
        or re.search(rule.get("inclusive_pattern", ""), text, re.IGNORECASE)
    )

    if not has_price:
        return {
            "field": "mrp",
            "status": "FAIL",
            "rule_code": "R001",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Price value (e.g. ₹50 or Rs 50)",
            "confidence": confidence,
            "reason": "MRP value (rupee amount) not detected in MRP declaration",
            "verified": rule["verified"],
        }

    if not has_inclusive:
        return {
            "field": "mrp",
            "status": "MANUAL_REVIEW",
            "rule_code": "R001",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Must state 'inclusive of all taxes'",
            "confidence": confidence,
            "reason": "MRP price detected, but 'inclusive of all taxes' declaration was not found in visible text — verify package flap",
            "verified": rule["verified"],
        }

    return {
        "field": "mrp",
        "status": "PASS",
        "rule_code": "R001",
        "source_clause": rule["source_clause"],
        "detected": text,
        "expected": "MRP with price and 'inclusive of all taxes'",
        "confidence": confidence,
        "reason": "MRP declaration present and correctly formatted",
        "verified": rule["verified"],
    }


def check_net_quantity(field_data: Optional[dict]) -> dict:
    """R002 — Net quantity must be present with a valid unit."""
    rule = _get_rule("R002")

    if not field_data or not field_data.get("text"):
        return {
            "field": "net_quantity",
            "status": "FAIL",
            "rule_code": "R002",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Net quantity with valid unit (g, kg, ml, L, mg)",
            "confidence": 1.0,
            "reason": "Net quantity declaration not found on label",
            "verified": rule["verified"],
        }

    text = field_data["text"]
    confidence = field_data.get("confidence", 0.0)

    if confidence < 0.5:
        return {
            "field": "net_quantity",
            "status": "MANUAL_REVIEW",
            "rule_code": "R002",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Net quantity with valid unit",
            "confidence": confidence,
            "reason": "OCR confidence too low — manual verification required",
            "verified": rule["verified"],
        }

    # Check for invalid units first
    for invalid_unit in rule["invalid_units"]:
        pattern = r"\b\d+(?:\.\d+)?\s*" + re.escape(invalid_unit) + r"\b"
        if re.search(pattern, text):
            return {
                "field": "net_quantity",
                "status": "FAIL",
                "rule_code": "R002",
                "source_clause": rule["source_clause"],
                "detected": text,
                "expected": f"Valid SI unit (e.g. 'g' not '{invalid_unit}')",
                "confidence": confidence,
                "reason": f"Invalid unit '{invalid_unit}' used. Must use correct SI unit abbreviation.",
                "verified": rule["verified"],
            }

    # Check for valid units
    valid_pattern = r"\b(\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(u) for u in rule["valid_units"]) + r")\b"
    if re.search(valid_pattern, text):
        return {
            "field": "net_quantity",
            "status": "PASS",
            "rule_code": "R002",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Net quantity with valid unit",
            "confidence": confidence,
            "reason": "Net quantity present with valid unit",
            "verified": rule["verified"],
        }

    return {
        "field": "net_quantity",
        "status": "FAIL",
        "rule_code": "R002",
        "source_clause": rule["source_clause"],
        "detected": text,
        "expected": "Quantity value with SI unit (g, kg, ml, L, mg)",
        "confidence": confidence,
        "reason": "Net quantity value or valid unit not found",
        "verified": rule["verified"],
    }


def check_manufacturer(field_data: Optional[dict]) -> dict:
    """R003 — Manufacturer name and address must be present."""
    rule = _get_rule("R003")

    if not field_data or not field_data.get("text"):
        return {
            "field": "manufacturer",
            "status": "FAIL",
            "rule_code": "R003",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Manufacturer/packer/importer name and address",
            "confidence": 1.0,
            "reason": "Manufacturer/packer/importer declaration not found on label",
            "verified": rule["verified"],
        }

    text = field_data["text"]
    confidence = field_data.get("confidence", 0.0)

    if confidence < 0.5:
        return {
            "field": "manufacturer",
            "status": "MANUAL_REVIEW",
            "rule_code": "R003",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Manufacturer name and address",
            "confidence": confidence,
            "reason": "OCR confidence too low — manual verification required",
            "verified": rule["verified"],
        }

    # Basic check: must have enough content for a name + address
    if len(text.strip()) < rule["min_length"]:
        return {
            "field": "manufacturer",
            "status": "FAIL",
            "rule_code": "R003",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Full manufacturer name and address",
            "confidence": confidence,
            "reason": "Manufacturer declaration too short — likely incomplete address",
            "verified": rule["verified"],
        }

    return {
        "field": "manufacturer",
        "status": "PASS",
        "rule_code": "R003",
        "source_clause": rule["source_clause"],
        "detected": text,
        "expected": "Manufacturer name and address",
        "confidence": confidence,
        "reason": "Manufacturer/packer/importer declaration present",
        "verified": rule["verified"],
    }


def check_mfg_date(field_data: Optional[dict]) -> dict:
    """R004 — Month and year of manufacture/packing/import must be present."""
    rule = _get_rule("R004")

    if not field_data or not field_data.get("text"):
        return {
            "field": "mfg_date",
            "status": "FAIL",
            "rule_code": "R004",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Month and year of manufacture/packing/import",
            "confidence": 1.0,
            "reason": "Manufacturing/packing date not found on label",
            "verified": rule["verified"],
        }

    text = field_data["text"]
    confidence = field_data.get("confidence", 0.0)

    if confidence < 0.5:
        return {
            "field": "mfg_date",
            "status": "MANUAL_REVIEW",
            "rule_code": "R004",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Month and year of manufacture",
            "confidence": confidence,
            "reason": "OCR confidence too low — manual verification required",
            "verified": rule["verified"],
        }

    # Check for valid date patterns
    date_patterns = [
        r"\b(0[1-9]|1[0-2])[/\-](20\d{2})\b",  # MM/YYYY
        r"(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s*(20\d{2})",  # MMM YYYY
    ]

    for pattern in date_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "field": "mfg_date",
                "status": "PASS",
                "rule_code": "R004",
                "source_clause": rule["source_clause"],
                "detected": text,
                "expected": "Month and year (e.g. 03/2024 or Mar 2024)",
                "confidence": confidence,
                "reason": "Manufacturing/packing date present in valid format",
                "verified": rule["verified"],
            }

    return {
        "field": "mfg_date",
        "status": "FAIL",
        "rule_code": "R004",
        "source_clause": rule["source_clause"],
        "detected": text,
        "expected": "Month and year format (MM/YYYY or Mon YYYY)",
        "confidence": confidence,
        "reason": "Date found but not in a recognizable month/year format",
        "verified": rule["verified"],
    }


def check_consumer_care(field_data: Optional[dict]) -> dict:
    """R005 — Consumer care contact must be present."""
    rule = _get_rule("R005")

    if not field_data or not field_data.get("text"):
        return {
            "field": "consumer_care",
            "status": "FAIL",
            "rule_code": "R005",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Consumer care phone number or email",
            "confidence": 1.0,
            "reason": "Consumer care contact not found on label",
            "verified": rule["verified"],
        }

    text = field_data["text"]
    confidence = field_data.get("confidence", 0.0)

    if confidence < 0.5:
        return {
            "field": "consumer_care",
            "status": "MANUAL_REVIEW",
            "rule_code": "R005",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Consumer care contact",
            "confidence": confidence,
            "reason": "OCR confidence too low — manual verification required",
            "verified": rule["verified"],
        }

    has_phone = bool(re.search(r"(?:(?:\+91|0)?[6-9]\d{9})", text))
    has_email = bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
    has_tollfree = bool(re.search(r"(?i)(?:1800|toll\s*free)", text))

    if has_phone or has_email or has_tollfree:
        return {
            "field": "consumer_care",
            "status": "PASS",
            "rule_code": "R005",
            "source_clause": rule["source_clause"],
            "detected": text,
            "expected": "Consumer care phone or email",
            "confidence": confidence,
            "reason": "Consumer care contact details present",
            "verified": rule["verified"],
        }

    return {
        "field": "consumer_care",
        "status": "FAIL",
        "rule_code": "R005",
        "source_clause": rule["source_clause"],
        "detected": text,
        "expected": "Valid phone number or email address",
        "confidence": confidence,
        "reason": "Consumer care text found but no valid phone number or email detected",
        "verified": rule["verified"],
    }


def check_country_of_origin(field_data: Optional[dict], is_imported: bool = False) -> dict:
    """R006 — Country of origin required for imported goods. VERIFIED rule."""
    rule = _get_rule("R006")

    if not is_imported:
        return {
            "field": "country_of_origin",
            "status": "PASS",
            "rule_code": "R006",
            "source_clause": rule["source_clause"],
            "detected": "N/A — domestic product",
            "expected": "Not required for domestic products",
            "confidence": 1.0,
            "reason": "Product marked as domestic — country of origin not required",
            "verified": rule["verified"],
        }

    if not field_data or not field_data.get("text"):
        return {
            "field": "country_of_origin",
            "status": "FAIL",
            "rule_code": "R006",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Country of origin declaration for imported goods",
            "confidence": 1.0,
            "reason": "Country of origin not found — required for imported goods under Rule 6(2)",
            "verified": rule["verified"],
        }

    return {
        "field": "country_of_origin",
        "status": "PASS",
        "rule_code": "R006",
        "source_clause": rule["source_clause"],
        "detected": field_data["text"],
        "expected": "Country of origin",
        "confidence": field_data.get("confidence", 1.0),
        "reason": "Country of origin declared",
        "verified": rule["verified"],
    }


def check_font_size(
    measured_height_mm: Optional[float],
    calibration_tier: str,
    calibration_confidence: str,
    package_weight_g: Optional[float] = None,
    blown_molded_embossed: bool = False,
) -> dict:
    """
    R007 — Font size must meet minimum mm height for declarations.

    CRITICAL (PRD Section 2.4):
    When calibration confidence is low, NEVER fabricate a specific number.
    Return MANUAL_REVIEW with the raw signal only.
    """
    rule = _get_rule("R007")

    # Insufficient calibration → honest MANUAL_REVIEW (never a guess)
    if calibration_tier in ("NONE",) or calibration_confidence == "LOW":
        return {
            "field": "font_size",
            "status": "MANUAL_REVIEW",
            "rule_code": "R007",
            "source_clause": rule["source_clause"],
            "detected": f"{measured_height_mm}mm (unverified)" if measured_height_mm else "N/A",
            "expected": "Minimum height per Rule 8",
            "confidence": 0.3,
            "reason": (
                "Font size: INSUFFICIENT EVIDENCE FOR VERDICT. "
                "No reliable calibration reference detected. "
                "Status: MANUAL REVIEW — human measurement required."
            ),
            "verified": rule["verified"],
        }

    if measured_height_mm is None:
        return {
            "field": "font_size",
            "status": "MANUAL_REVIEW",
            "rule_code": "R007",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Minimum height per Rule 8",
            "confidence": 0.5,
            "reason": "Could not measure character height from this image",
            "verified": rule["verified"],
        }

    # Determine required minimum height based on package weight
    required_mm = 1.0  # default (smallest package)
    if package_weight_g:
        for threshold in rule.get("thresholds_by_package_weight", []):
            if package_weight_g <= threshold["max_weight_g"]:
                required_mm = threshold["min_height_mm"]
                break

    # Rule 7 Table II: If blown, molded, or embossed, double the minimum height
    if blown_molded_embossed:
        required_mm *= 2.0

    confidence = 0.9 if calibration_tier in ("ARUCO", "ID_CARD") else 0.7

    if measured_height_mm >= required_mm:
        return {
            "field": "font_size",
            "status": "PASS",
            "rule_code": "R007",
            "source_clause": rule["source_clause"],
            "detected": f"{measured_height_mm:.2f}mm",
            "expected": f"≥ {required_mm}mm" + (" (doubled for blown/molded/embossed container)" if blown_molded_embossed else ""),
            "confidence": confidence,
            "reason": f"Character height {measured_height_mm:.2f}mm meets minimum {required_mm}mm",
            "verified": rule["verified"],
        }

    # Borderline cases with Tier 3/4 → manual review
    if calibration_tier in ("COIN", "NONE") and abs(measured_height_mm - required_mm) < 0.5:
        return {
            "field": "font_size",
            "status": "MANUAL_REVIEW",
            "rule_code": "R007",
            "source_clause": rule["source_clause"],
            "detected": f"{measured_height_mm:.2f}mm",
            "expected": f"≥ {required_mm}mm",
            "confidence": confidence,
            "reason": (
                f"Measured {measured_height_mm:.2f}mm vs required {required_mm}mm — "
                f"measurement too close to threshold with {calibration_tier} calibration only. "
                "Manual measurement recommended."
            ),
            "verified": rule["verified"],
        }

    return {
        "field": "font_size",
        "status": "FAIL",
        "rule_code": "R007",
        "source_clause": rule["source_clause"],
        "detected": f"{measured_height_mm:.2f}mm",
        "expected": f"≥ {required_mm}mm" + (" (doubled for blown/molded/embossed container)" if blown_molded_embossed else ""),
        "confidence": confidence,
        "reason": f"Character height {measured_height_mm:.2f}mm below statutory minimum {required_mm}mm",
        "verified": rule["verified"],
    }


def check_usp_math(
    mrp_field: Optional[dict],
    net_qty_field: Optional[dict],
    usp_field: Optional[dict],
) -> dict:
    """
    R008 — Unit Sale Price (USP) Declaration & Mathematical Consistency Check.
    Statutory Formula: Calculated Volume/Quantity = MRP / USP
    Under Rule 6(11) of Legal Metrology (Packaged Commodities) Rules, 2011 (2021 amendment).
    """
    rule = _get_rule("R008") or {
        "rule_code": "R008",
        "source_clause": "Rule 6(11) — Unit Sale Price Declaration & Mathematical Consistency [2021 Amendment]",
        "verified": True,
        "tolerance_pct": 5.0,
    }
    tolerance = float(rule.get("tolerance_pct", 5.0))

    # Case 1: USP field missing or empty
    if not usp_field or not usp_field.get("text"):
        return {
            "field": "usp",
            "status": "FAIL",
            "rule_code": "R008",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "Mandatory Unit Sale Price (USP) declaration (e.g. ₹X.XX / ml, / g, or / unit)",
            "confidence": 1.0,
            "reason": (
                "Unit Sale Price (USP) declaration not found on package. "
                "Mandatory under Rule 6(11) (2021 Amendment) of Legal Metrology Rules for consumer price transparency."
            ),
            "verified": rule["verified"],
        }

    usp_text = usp_field.get("text", "").strip()
    usp_conf = usp_field.get("confidence", 0.0)

    # If OCR confidence is too low
    if usp_conf < 0.5:
        return {
            "field": "usp",
            "status": "MANUAL_REVIEW",
            "rule_code": "R008",
            "source_clause": rule["source_clause"],
            "detected": usp_text,
            "expected": "Clear Unit Sale Price declaration",
            "confidence": usp_conf,
            "reason": "OCR confidence too low for reliable USP extraction — manual review required",
            "verified": rule["verified"],
        }

    # Case 2: Either MRP or Net Quantity is missing
    mrp_text = mrp_field.get("text", "").strip() if mrp_field else ""
    net_qty_text = net_qty_field.get("text", "").strip() if net_qty_field else ""

    if not mrp_text or not net_qty_text:
        return {
            "field": "usp",
            "status": "MANUAL_REVIEW",
            "rule_code": "R008",
            "source_clause": rule["source_clause"],
            "detected": usp_text,
            "expected": "MRP and Net Quantity declarations required for mathematical cross-verification",
            "confidence": usp_conf,
            "reason": (
                f"USP detected ('{usp_text}'), but cannot perform mathematical cross-verification because "
                f"{'MRP' if not mrp_text else 'Net Quantity'} is missing from label."
            ),
            "verified": rule["verified"],
        }

    def _extract_price(text: str) -> Optional[float]:
        clean = text.replace(",", "")
        # Prioritize matching after MRP / Rs / INR / ₹
        m = re.search(r"(?:M\.?R\.?P\.?\s*:?\s*)?(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)", clean, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        return None

    def _extract_usp(text: str):
        clean = text.replace(",", "")
        m = re.search(
            r"(?:U\.?S\.?P\.?|unit\s+sale\s+price)?\s*:?\s*(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)\s*(?:/|\s*per\s*)\s*([a-zA-Z]+)",
            clean,
            re.IGNORECASE,
        )
        if m:
            try:
                val = float(m.group(1))
                unit = m.group(2).lower()
                return val, unit
            except ValueError:
                return None, None
        return None, None

    def _extract_qty(text: str):
        clean = text.replace(",", "")
        m = re.search(
            r"(\d+(?:\.\d+)?)\s*(ml|l|litre|liter|millilitre|milliliter|g|kg|gm|gram|kilogram|mg|unit|units|n|piece|pieces|item|items)\b",
            clean,
            re.IGNORECASE,
        )
        if m:
            try:
                val = float(m.group(1))
                unit = m.group(2).lower()
                return val, unit
            except ValueError:
                return None, None
        return None, None

    mrp_val = _extract_price(mrp_text)
    usp_val, usp_unit = _extract_usp(usp_text)
    qty_val, qty_unit = _extract_qty(net_qty_text)

    if not mrp_val or not usp_val or not qty_val:
        return {
            "field": "usp",
            "status": "MANUAL_REVIEW",
            "rule_code": "R008",
            "source_clause": rule["source_clause"],
            "detected": f"USP: {usp_text} | MRP: {mrp_text} | Qty: {net_qty_text}",
            "expected": "Parseable numerical values for MRP, USP, and Net Quantity",
            "confidence": min(usp_conf, mrp_field.get("confidence", 1.0), net_qty_field.get("confidence", 1.0)),
            "reason": "Could not parse numerical values from declarations for automated mathematical cross-verification.",
            "verified": rule["verified"],
        }

    VOL_MAP = {"ml": 1.0, "millilitre": 1.0, "milliliter": 1.0, "l": 1000.0, "litre": 1000.0, "liter": 1000.0}
    MASS_MAP = {"g": 1.0, "gm": 1.0, "gram": 1.0, "kg": 1000.0, "kilogram": 1000.0, "mg": 0.001}
    COUNT_MAP = {"n": 1.0, "unit": 1.0, "units": 1.0, "piece": 1.0, "pieces": 1.0, "item": 1.0, "items": 1.0}

    qty_base = None
    qty_type = None
    usp_base_rate = None

    if qty_unit in VOL_MAP:
        qty_base = qty_val * VOL_MAP[qty_unit]
        qty_type = "volume"
        display_unit = "ml"
    elif qty_unit in MASS_MAP:
        qty_base = qty_val * MASS_MAP[qty_unit]
        qty_type = "mass"
        display_unit = "g"
    elif qty_unit in COUNT_MAP:
        qty_base = qty_val * COUNT_MAP[qty_unit]
        qty_type = "count"
        display_unit = "unit"

    if usp_unit in VOL_MAP and qty_type == "volume":
        usp_base_rate = usp_val / VOL_MAP[usp_unit]
    elif usp_unit in MASS_MAP and qty_type == "mass":
        usp_base_rate = usp_val / MASS_MAP[usp_unit]
    elif usp_unit in COUNT_MAP and qty_type == "count":
        usp_base_rate = usp_val / COUNT_MAP[usp_unit]

    if qty_base is None or usp_base_rate is None or usp_base_rate <= 0:
        if usp_unit == qty_unit and usp_val > 0:
            calc_qty = mrp_val / usp_val
            declared_qty = qty_val
            display_unit = qty_unit
        else:
            return {
                "field": "usp",
                "status": "FAIL",
                "rule_code": "R008",
                "source_clause": rule["source_clause"],
                "detected": f"Net Qty unit '{qty_unit}' vs USP unit '{usp_unit}'",
                "expected": "USP unit must correspond to declared Net Quantity unit (Rule 6(11))",
                "confidence": usp_conf,
                "reason": f"Unit mismatch: Net Quantity is declared in '{qty_unit}', but USP is declared per '{usp_unit}'.",
                "verified": rule["verified"],
            }
    else:
        calc_qty = mrp_val / usp_base_rate
        declared_qty = qty_base

    # Mathematical Cross-Verification: Volume = MRP / USP
    diff_abs = abs(calc_qty - declared_qty)
    diff_pct = (diff_abs / declared_qty) * 100.0

    detected_str = (
        f"USP: ₹{usp_val:.2f}/{usp_unit} | MRP: ₹{mrp_val:.2f} | "
        f"Declared: {qty_val:g} {qty_unit} (Math: {calc_qty:.1f} {display_unit})"
    )

    if diff_pct <= tolerance:
        return {
            "field": "usp",
            "status": "PASS",
            "rule_code": "R008",
            "source_clause": rule["source_clause"],
            "detected": detected_str,
            "expected": f"Calculated Volume/Qty (MRP ₹{mrp_val:g} / USP ₹{usp_val:g}) = {calc_qty:.1f} {display_unit} (±{tolerance}% tolerance)",
            "confidence": round(min(usp_conf, mrp_field.get("confidence", 1.0), net_qty_field.get("confidence", 1.0)), 3),
            "reason": (
                f"Statutory Economics Verified: MRP ₹{mrp_val:g} / USP ₹{usp_val:g} per {usp_unit} = "
                f"{calc_qty:.1f} {display_unit}. Consistent with declared {qty_val:g} {qty_unit} "
                f"(Variance: {diff_pct:.1f}% within ±{tolerance}% statutory margin)."
            ),
            "verified": rule["verified"],
        }
    else:
        return {
            "field": "usp",
            "status": "FAIL",
            "rule_code": "R008",
            "source_clause": rule["source_clause"],
            "detected": detected_str,
            "expected": f"Consistent Economics: Math yields {calc_qty:.1f} {display_unit}, but declared {qty_val:g} {qty_unit}",
            "confidence": round(min(usp_conf, mrp_field.get("confidence", 1.0), net_qty_field.get("confidence", 1.0)), 3),
            "reason": (
                f"Statutory Economics Inconsistency Warning: Declared MRP ₹{mrp_val:g} / USP ₹{usp_val:g} "
                f"calculates to {calc_qty:.1f} {display_unit}, whereas declared Net Quantity is {qty_val:g} {qty_unit} "
                f"(Discrepancy: {diff_pct:.1f}% exceeds ±{tolerance}% statutory threshold). "
                "Violates Rule 6(11) of Legal Metrology (Packaged Commodities) Rules, 2011."
            ),
            "verified": rule["verified"],
        }


def check_prohibited_modifiers(net_qty_field: Optional[dict]) -> dict:
    """
    R009 — Prohibition of Misleading/Vague Modifiers on Net Quantity.
    Under Rule 11 & Rule 12(6) of Legal Metrology (Packaged Commodities) Rules, 2011.
    Words like 'when packed', 'approximate', 'approx.', 'average', 'minimum',
    'not less than', 'about' are strictly prohibited from qualifying net quantity.
    """
    rule = _get_rule("R009") or {
        "rule_code": "R009",
        "source_clause": "Rule 11 & Rule 12(6) — Prohibition of Misleading/Vague Modifiers on Net Quantity [VERIFIED]",
        "verified": True,
        "prohibited_words": ["when packed", "approximate", "approx.", "approx", "average", "avg", "minimum", "not less than", "about"],
    }

    if not net_qty_field or not net_qty_field.get("text"):
        return {
            "field": "prohibited_modifiers",
            "status": "PASS",
            "rule_code": "R009",
            "source_clause": rule["source_clause"],
            "detected": None,
            "expected": "No vague modifiers qualifying quantity",
            "confidence": 1.0,
            "reason": "Net quantity not detected or empty — evaluated under R002",
            "verified": rule["verified"],
        }

    text = net_qty_field.get("text", "")
    text_lower = text.lower()

    detected_prohibited = []
    for word in rule.get("prohibited_words", []):
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, text_lower):
            detected_prohibited.append(word)

    if detected_prohibited:
        found_str = ", ".join(f"'{w}'" for w in detected_prohibited)
        return {
            "field": "prohibited_modifiers",
            "status": "FAIL",
            "rule_code": "R009",
            "source_clause": rule["source_clause"],
            "detected": f"Prohibited qualifier(s): {found_str} in '{text}'",
            "expected": "Quantity must be absolute without misleading qualifiers (Rule 11 & Rule 12(6))",
            "confidence": net_qty_field.get("confidence", 0.95),
            "reason": (
                f"Statutory Violation: Qualifier {found_str} detected. "
                "Words that create an exaggerated or misleading impression (e.g. 'approximate', 'average', 'minimum', "
                "'not less than', 'when packed') are explicitly prohibited under Rule 11 & Rule 12(6)."
            ),
            "verified": rule["verified"],
        }

    return {
        "field": "prohibited_modifiers",
        "status": "PASS",
        "rule_code": "R009",
        "source_clause": rule["source_clause"],
        "detected": text,
        "expected": "No misleading qualifiers",
        "confidence": net_qty_field.get("confidence", 0.95),
        "reason": "No prohibited or misleading modifiers ('approx', 'average', 'minimum', etc.) found in Net Quantity declaration.",
        "verified": rule["verified"],
    }


def check_exemption_scope(package_weight_g: Optional[float], is_institutional: bool = False) -> dict:
    """
    R010 — Scope & Statutory Exemptions under Rule 3 & Rule 26.
    - Package <= 10g/ml: Completely exempt from Chapter II.
    - Package 10g - 20g/ml: Only MRP and Net Quantity required.
    - Package > 25kg/25L or institutional purchase: Retail Chapter II does not apply.
    """
    rule = _get_rule("R010") or {
        "rule_code": "R010",
        "source_clause": "Rule 3 & Rule 26 — Statutory Exemptions & Scope [VERIFIED]",
        "verified": True,
    }

    if is_institutional:
        return {
            "field": "exemption_scope",
            "status": "PASS",
            "rule_code": "R010",
            "source_clause": rule["source_clause"],
            "detected": "Institutional / Industrial Supply",
            "expected": "Exempt from Chapter II Retail Regulations (Rule 3)",
            "confidence": 1.0,
            "reason": "Commodity destined directly for institutional/industrial consumers is exempt from Chapter II retail packaging rules.",
            "verified": rule["verified"],
        }

    if package_weight_g is not None:
        if package_weight_g <= 10.0:
            return {
                "field": "exemption_scope",
                "status": "PASS",
                "rule_code": "R010",
                "source_clause": rule["source_clause"],
                "detected": f"{package_weight_g:g}g/ml (≤ 10g/ml)",
                "expected": "Exempt from Chapter II Retail Declarations (Rule 26(a))",
                "confidence": 1.0,
                "reason": f"Package net weight/measure is {package_weight_g:g}g/ml (≤ 10g/ml). Statutory Exemption under Rule 26 applies.",
                "verified": rule["verified"],
            }
        elif 10.0 < package_weight_g <= 20.0:
            return {
                "field": "exemption_scope",
                "status": "PASS",
                "rule_code": "R010",
                "source_clause": rule["source_clause"],
                "detected": f"{package_weight_g:g}g/ml (10g - 20g/ml)",
                "expected": "Partial Exemption: Only MRP and Net Quantity required (Rule 26 Note)",
                "confidence": 1.0,
                "reason": f"Package is between 10g/ml and 20g/ml ({package_weight_g:g}g/ml). Only MRP and Net Quantity are mandatory; other declarations exempt under Rule 26.",
                "verified": rule["verified"],
            }
        elif package_weight_g > 25000.0:
            return {
                "field": "exemption_scope",
                "status": "PASS",
                "rule_code": "R010",
                "source_clause": rule["source_clause"],
                "detected": f"{package_weight_g/1000:g}kg (> 25kg)",
                "expected": "Bulk Wholesale / Non-retail Package (Rule 3(1)(a))",
                "confidence": 1.0,
                "reason": f"Package net quantity exceeds 25 kg/litres ({package_weight_g/1000:g}kg). Governed under Chapter III Wholesale, exempt from Chapter II retail rules.",
                "verified": rule["verified"],
            }

    return {
        "field": "exemption_scope",
        "status": "PASS",
        "rule_code": "R010",
        "source_clause": rule["source_clause"],
        "detected": "Standard Retail Package Scope",
        "expected": "Subject to Chapter II Retail Regulations (Rule 3)",
        "confidence": 1.0,
        "reason": "Commodity falls within standard retail package threshold (10g - 25kg). Fully subject to Chapter II regulations.",
        "verified": rule["verified"],
    }


# ─── Main Engine Entrypoint ───────────────────────────────────────────────────

def run_all_rules(
    classified_fields: dict,
    calibration_result: Optional[dict] = None,
    is_imported: bool = False,
    package_weight_g: Optional[float] = None,
    font_measurement: Optional[dict] = None,
    surface_type: str = "flat",
    blown_molded_embossed: bool = False,
    calibration: Optional[dict] = None,
    font_measurements: Optional[dict] = None,
    **kwargs,
) -> dict:
    """
    Runs all applicable statutory rules against classified field data.
    Implements full compliance checking per Legal Metrology (Packaged Commodities) Rules, 2011.
    """
    # Normalize aliases
    calib = calibration_result or calibration or {}
    fonts = font_measurement or font_measurements or {}
    fields = classified_fields

    # Auto-extract package weight/volume if not provided
    if package_weight_g is None and fields.get("net_quantity"):
        net_text = fields["net_quantity"].get("text", "")
        # Extract numeric quantity and unit
        q_match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|gm|gms|litre|litres|liter|liters|l|ml)\b", net_text, re.IGNORECASE)
        if q_match:
            val = float(q_match.group(1))
            unit = q_match.group(2).lower()
            if unit in ("kg", "l", "litre", "litres", "liter", "liters"):
                package_weight_g = val * 1000.0
            else:
                package_weight_g = val

    results = []

    # 1. Statutory Exemption Scope (R010)
    exemption_result = check_exemption_scope(package_weight_g=package_weight_g)
    results.append(exemption_result)

    # Check exemption thresholds under Rule 26
    is_completely_exempt = (package_weight_g is not None and package_weight_g <= 10.0)
    is_partially_exempt = (package_weight_g is not None and 10.0 < package_weight_g <= 20.0)

    # 2. Mandatory Declarations
    combined_ctx = " ".join(f.get("text", "") for f in fields.values() if isinstance(f, dict))
    results.append(check_mrp(fields.get("mrp"), full_text=combined_ctx))
    results.append(check_net_quantity(fields.get("net_quantity")))
    results.append(check_prohibited_modifiers(fields.get("net_quantity")))

    # Manufacturer details (exempt if <= 20g under Rule 26)
    mfg_res = check_manufacturer(fields.get("manufacturer"))
    if (is_completely_exempt or is_partially_exempt) and mfg_res["status"] == "FAIL":
        mfg_res["status"] = "PASS"
        mfg_res["reason"] = f"Exempted: Package net quantity ({package_weight_g:g}g/ml) <= 20g/ml under Rule 26."
    results.append(mfg_res)

    # Mfg Date (exempt if <= 20g under Rule 26)
    date_res = check_mfg_date(fields.get("mfg_date"))
    if (is_completely_exempt or is_partially_exempt) and date_res["status"] == "FAIL":
        date_res["status"] = "PASS"
        date_res["reason"] = f"Exempted: Package net quantity ({package_weight_g:g}g/ml) <= 20g/ml under Rule 26."
    results.append(date_res)

    # Consumer Care (exempt if <= 20g under Rule 26)
    care_res = check_consumer_care(fields.get("consumer_care"))
    if (is_completely_exempt or is_partially_exempt) and care_res["status"] == "FAIL":
        care_res["status"] = "PASS"
        care_res["reason"] = f"Exempted: Package net quantity ({package_weight_g:g}g/ml) <= 20g/ml under Rule 26."
    results.append(care_res)

    # Country of Origin (for imported goods)
    results.append(check_country_of_origin(fields.get("country_of_origin"), is_imported=is_imported))

    # Unit Sale Price (exempt if small pack or wholesale)
    usp_res = check_usp_math(fields.get("mrp"), fields.get("net_quantity"), fields.get("usp"))
    if (is_completely_exempt or is_partially_exempt) and usp_res["status"] == "FAIL":
        usp_res["status"] = "PASS"
        usp_res["reason"] = f"Exempted: USP declaration not mandatory for packs <= 20g/ml under Rule 6(11)."
    results.append(usp_res)

    # 3. Font Size Measurement (Rule 7 Tables I & II)
    measured_h = None
    if isinstance(fonts, dict):
        measured_h = fonts.get("height_mm") or fonts.get("net_quantity")
    elif isinstance(fonts, (int, float)):
        measured_h = float(fonts)

    calib_tier = calib.get("tier", "ARUCO" if calib.get("calibrated") else "NONE")
    calib_conf = calib.get("confidence", "HIGH" if calib.get("calibrated") else "LOW")

    results.append(check_font_size(
        measured_height_mm=measured_h,
        calibration_tier=calib_tier,
        calibration_confidence=calib_conf,
        package_weight_g=package_weight_g,
        blown_molded_embossed=blown_molded_embossed,
    ))

    # Determine overall status
    statuses = [r["status"] for r in results]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "MANUAL_REVIEW" in statuses:
        overall = "MANUAL_REVIEW"
    else:
        overall = "PASS"

    summary = {
        "pass": statuses.count("PASS"),
        "fail": statuses.count("FAIL"),
        "manual_review": statuses.count("MANUAL_REVIEW"),
    }

    return {
        "results": results,
        "rule_results": results,  # alias for backward-compatibility
        "overall_status": overall,
        "summary": summary,
    }

