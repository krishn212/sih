"""
Phase 0 Test Script — Run this FIRST before anything else.
Tests the full core pipeline (no UI, no auth) against a real product image.

Usage:
  python phase0_test.py path/to/product_photo.jpg

What it tests:
  1. Blur gate
  2. Google Cloud Vision OCR (word-level)
  3. Field classification (regex + keyword)
  4. Rule engine (all 6 rules)

Output: Structured JSON verdict to stdout + a detailed log.
"""
import sys
import json
import os
from dotenv import load_dotenv

# Ensure Windows PowerShell handles Unicode symbols cleanly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# Add backend to path when running from root
sys.path.insert(0, os.path.dirname(__file__))

from services.blur_gate import check_blur
from services.ocr_service import extract_words
from services.field_classifier import classify_fields
from services.rule_engine import run_all_rules


def run_phase0(image_path: str, is_imported: bool = False):
    print(f"\n{'='*60}")
    print(f"LEGAL METROLOGY COMPLIANCE SCANNER — Phase 0 Test")
    print(f"Image: {image_path}")
    print(f"{'='*60}\n")

    # Step 1: Blur check
    print("▶ Step 1: Blur Gate")
    blur = check_blur(image_path)
    if not blur["ok"]:
        print(f"  ❌ REJECTED — {blur['reason']}")
        print(f"  Sharpness score: {blur['variance']} (min: {blur['threshold']})")
        return
    print(f"  ✅ Image sharp enough (score: {blur['variance']})")

    # Step 2: Perception / OCR
    provider_name = "Gemini Vision" if os.getenv("GEMINI_API_KEY") else "Offline Edge OCR (Windows Native)"
    print(f"\n▶ Step 2: Perception Engine [{provider_name}]")
    ocr = extract_words(image_path)
    if not ocr["ok"]:
        print(f"  ❌ OCR FAILED — {ocr.get('error')}")
        return
    provider_used = ocr.get("provider", "unknown")
    print(f"  ✅ {len(ocr['words'])} words detected via [{provider_used}]")
    print(f"  Image size: {ocr['image_width']}×{ocr['image_height']} px")
    if ocr['words']:
        print(f"  Sample words: {[w['text'] for w in ocr['words'][:10]]}")
    else:
        print("  ⚠️ No text detected in this frame (ensure label is facing camera)")

    # Step 3: Field classification
    print("\n▶ Step 3: Field Classification")
    classification = classify_fields(ocr["words"], ocr["image_width"], ocr["image_height"])
    fields = classification["fields"]

    for field_name, field_data in fields.items():
        print(f"  ✅ {field_name}: '{field_data['text'][:60]}' (confidence: {field_data['confidence']:.2f}, source: {field_data['source']})")

    unmatched_count = len(classification.get("unmatched_blocks", []))
    print(f"  ⚠️  {unmatched_count} unmatched text blocks")

    # Step 4: Rule engine
    print("\n▶ Step 4: Rule Engine")
    rule_output = run_all_rules(
        classified_fields=fields,
        calibration_result=None,  # No calibration in Phase 0
        is_imported=is_imported,
    )

    icons = {"PASS": "✅", "FAIL": "❌", "MANUAL_REVIEW": "⚠️"}
    for result in rule_output["results"]:
        icon = icons.get(result["status"], "❓")
        print(f"  {icon} [{result['rule_code']}] {result['field'].upper()} → {result['status']}")
        if result["status"] != "PASS":
            print(f"      Reason: {result['reason']}")
            print(f"      Detected: {result.get('detected', '—')}")
            print(f"      Expected: {result.get('expected', '—')}")
        if not result.get("verified"):
            print(f"      ⚠️  UNVERIFIED RULE — verify against actual Rules 2011 text")

    print(f"\n{'─'*60}")
    print(f"OVERALL STATUS: {rule_output['overall_status']}")
    print(f"Summary: {rule_output['summary']}")
    print(f"{'─'*60}\n")

    # Full JSON output
    print("Full JSON output:")
    print(json.dumps({
        "image": image_path,
        "blur": blur,
        "ocr_word_count": len(ocr["words"]),
        "fields_detected": list(fields.keys()),
        "overall_status": rule_output["overall_status"],
        "summary": rule_output["summary"],
        "violations": [
            {
                "field": r["field"],
                "status": r["status"],
                "reason": r["reason"],
                "detected": r.get("detected"),
                "expected": r.get("expected"),
                "rule_code": r["rule_code"],
                "verified": r.get("verified", False),
            }
            for r in rule_output["results"]
            if r["status"] != "PASS"
        ],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python phase0_test.py <path_to_product_image.jpg>")
        print("Example: python phase0_test.py ../benchmark/product1.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    is_imported = "--imported" in sys.argv
    run_phase0(image_path, is_imported=is_imported)
