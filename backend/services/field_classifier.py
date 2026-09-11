"""
Field Classifier — Phase 1, Step 3
OCR-first approach (as mandated by PRD Section 2.7).

Priority order:
  1. Regex pattern matching
  2. Keyword proximity matching
  3. Spatial heuristics (relative position on label)
  YOLO fallback: NOT implemented here — only if 1-3 prove insufficient.

A single OCR block CAN match multiple fields — e.g. "Mfg Date: 03/26 | Net Qty: 500g"
satisfies both mfg_date and net_quantity. Do NOT let one match suppress another.
"""
import re
from typing import List, Dict, Optional


# ─── Regex Patterns ──────────────────────────────────────────────────────────
# These are illustrative patterns. VERIFY against actual Rules 2011 text.

FIELD_PATTERNS = {
    "mrp": [
        # Standard formats found on Indian labels
        r"(?i)M\.?R\.?P\.?\s*:?\s*(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)",
        r"(?i)(?:Rs\.?|₹|INR)\s*(\d+(?:\.\d{1,2})?)\s*(?:M\.?R\.?P\.?|inclusive)",
        r"(?i)maximum\s+retail\s+price",
    ],
    "net_quantity": [
        # VALID units: g, kg, ml, L, mg (case-sensitive matters — gm is a VIOLATION)
        r"\b(\d+(?:\.\d+)?)\s*(g|kg|ml|L|mg|litre|liter|gram|kilogram|millilitre)\b",
        r"(?i)net\.?\s*(?:wt\.?|qty\.?|weight|quantity|content|volume)\s*:?\s*(\d+(?:\.\d+)?)\s*(g|kg|ml|L|mg)",
        r"(?i)(?:wt|qty|weight|quantity|volume)\s*:?\s*(\d+)",
    ],
    "manufacturer": [
        r"(?i)(?:manufactured|packed|marketed|imported)\s+(?:by|for)\s*:?\s*(.+)",
        r"(?i)(?:mfr?\.?|mfg\.?|manufacturer|packer|marketer)\s*:?\s*(.+)",
    ],
    "mfg_date": [
        # Month/Year formats: MM/YYYY, MMM-YYYY, Month YYYY, MM-YY, MMM-YY
        r"(?i)(?:mfg\.?|mfd\.?|manufactured|packed|best\s+before|use\s+by|expiry)\s*(?:date|on|:)?\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{2,4}|[a-z]{3,9}\s*[\-\/\s]?\s*\d{2,4})",
        r"\b(0[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})\b",
        r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s*[\-\/\s]?\s*(20\d{2}|\d{2})\b",
    ],
    "consumer_care": [
        # Indian phone: 10 digits starting with 6-9, or with +91/0
        r"(?:(?:\+91|0)?[6-9]\d{9})",
        r"(?i)consumer\s*(?:care|helpline|service|support)\s*:?",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        r"(?i)toll\s*free\s*:?\s*[\d\s-]+",
    ],
    "country_of_origin": [
        # VERIFIED rule (from PRD)
        r"(?i)country\s+of\s+origin\s*:?\s*(.+)",
        r"(?i)made\s+in\s+(.+)",
        r"(?i)product\s+of\s+(.+)",
        r"(?i)origin\s*:?\s*(india|china|usa|uk|germany|japan|\w+)",
    ],
    "usp": [
        # Unit Sale Price — mandatory under 2021 amendment
        r"(?i)(?:U\.?S\.?P\.?|unit\s+sale\s+price)\s*:?\s*(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)\s*(?:/|\s*per\s*)(ml|g|kg|l|unit|piece|item|m|gm)",
        r"(?i)(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)\s*/\s*(ml|g|kg|l|unit|piece|item|m|gm)",
        r"(?i)(?:per\s+ml\s*/\s*per\s+gm)",
    ],
}

# Keywords that signal proximity — if a word block is near these, it likely belongs to that field
FIELD_KEYWORDS = {
    "mrp": ["mrp", "maximum retail price", "m.r.p", "price", "inclusive of all taxes"],
    "net_quantity": ["net wt", "net qty", "net weight", "net quantity", "net content", "net volume"],
    "manufacturer": ["manufactured by", "packed by", "marketed by", "mfr", "mfg by", "imported by"],
    "mfg_date": ["mfg date", "mfd", "manufactured on", "packed on", "best before", "use by", "expiry"],
    "consumer_care": ["consumer care", "consumer helpline", "toll free", "customer care", "contact us"],
    "country_of_origin": ["country of origin", "made in", "product of", "manufactured in"],
    "usp": ["usp", "unit sale price", "u.s.p", "per ml", "per gm", "per kg", "per g"],
}


def _bbox_to_dict(bbox: dict) -> dict:
    return {
        "x": bbox.get("x", 0),
        "y": bbox.get("y", 0),
        "width": bbox.get("width", 0),
        "height": bbox.get("height", 0),
    }


def _words_to_text_blocks(words: List[dict], proximity_px: int = 80) -> List[dict]:
    """
    Groups nearby OCR words into logical text blocks by spatial proximity.
    Words within `proximity_px` horizontally AND on the same line vertically
    are merged into one block.
    """
    if not words:
        return []

    # Sort by vertical position (top of bounding box), then horizontal
    sorted_words = sorted(words, key=lambda w: (w["bounding_box"]["y"], w["bounding_box"]["x"]))

    blocks = []
    current_block = {
        "words": [sorted_words[0]],
        "text": sorted_words[0]["text"],
        "confidence": sorted_words[0]["confidence"],
        "bounding_box": dict(sorted_words[0]["bounding_box"]),
    }

    for word in sorted_words[1:]:
        prev = current_block["words"][-1]
        prev_bb = prev["bounding_box"]
        curr_bb = word["bounding_box"]

        # Same line: vertical centers within half line-height of each other
        prev_center_y = prev_bb["y"] + prev_bb["height"] / 2
        curr_center_y = curr_bb["y"] + curr_bb["height"] / 2
        on_same_line = abs(prev_center_y - curr_center_y) < max(prev_bb["height"], curr_bb["height"]) * 0.6

        # Close horizontally
        gap_x = curr_bb["x"] - (prev_bb["x"] + prev_bb["width"])
        close_horizontal = gap_x < proximity_px

        if on_same_line and close_horizontal:
            current_block["words"].append(word)
            current_block["text"] += " " + word["text"]
            current_block["confidence"] = min(current_block["confidence"], word["confidence"])
            # Expand bounding box
            bb = current_block["bounding_box"]
            new_right = max(bb["x"] + bb["width"], curr_bb["x"] + curr_bb["width"])
            new_bottom = max(bb["y"] + bb["height"], curr_bb["y"] + curr_bb["height"])
            bb["width"] = new_right - bb["x"]
            bb["height"] = new_bottom - bb["y"]
        else:
            blocks.append(current_block)
            current_block = {
                "words": [word],
                "text": word["text"],
                "confidence": word["confidence"],
                "bounding_box": dict(curr_bb),
            }

    blocks.append(current_block)
    return blocks


def classify_fields(words: List[dict], image_width: int = 0, image_height: int = 0) -> dict:
    """
    Takes word-level OCR output and classifies text into the 6 mandatory fields.

    Returns:
        {
            "fields": {
                "mrp": {"text": str, "confidence": float, "bounding_box": dict, "source": str},
                "net_quantity": {...},
                "manufacturer": {...},
                "mfg_date": {...},
                "consumer_care": {...},
                "country_of_origin": {...},
            },
            "unmatched_blocks": [...],  # blocks not matched to any field
            "all_blocks": [...],        # all text blocks (for debugging)
        }
    """
    blocks = _words_to_text_blocks(words)
    field_names = list(FIELD_PATTERNS.keys())

    # Each field can have multiple candidate matches — we keep the best one
    field_candidates: Dict[str, list] = {f: [] for f in field_names}
    matched_block_indices = set()

    for idx, block in enumerate(blocks):
        text = block["text"]
        text_lower = text.lower()
        matched_fields = []

        # ── Step 1: Regex matching ────────────────────────────────────────
        for field, patterns in FIELD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matched_fields.append((field, "regex", 0.95))
                    break  # one pattern matched → move to next field

        # ── Step 2: Keyword matching ──────────────────────────────────────
        for field, keywords in FIELD_KEYWORDS.items():
            if field not in [m[0] for m in matched_fields]:  # don't double-match
                for kw in keywords:
                    if kw.lower() in text_lower:
                        matched_fields.append((field, "keyword", 0.80))
                        break

        for field, source, confidence in matched_fields:
            field_candidates[field].append({
                "text": text,
                "confidence": min(confidence, block["confidence"] if block["confidence"] > 0 else confidence),
                "bounding_box": block["bounding_box"],
                "source": source,
            })
            matched_block_indices.add(idx)

    # Pick the best candidate per field (highest confidence)
    classified = {}
    for field, candidates in field_candidates.items():
        if candidates:
            best = max(candidates, key=lambda c: c["confidence"])
            classified[field] = best

    # Collect unmatched blocks
    unmatched = [
        blocks[i] for i in range(len(blocks))
        if i not in matched_block_indices
    ]

    return {
        "fields": classified,
        "unmatched_blocks": unmatched,
        "all_blocks": blocks,
    }
