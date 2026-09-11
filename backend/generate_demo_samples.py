"""
Generates 2 realistic demo test packaging labels with ArUco / card calibration markers:
1. compliant_sample.jpg  -> 100% passes all 10 Legal Metrology Rules (R001-R010)
2. violation_sample.jpg  -> Fails R001 (Missing tax text), R002 (illegal 'gm'), R007 (undersized font)
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_demo_samples():
    output_dir = os.path.join(os.path.dirname(__file__), "demo_samples")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate ArUco marker image (DICT_4X4_50, ID 0)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 200  # pixels (representing 100mm -> 2.0 px/mm)
    marker_img = np.zeros((marker_size, marker_size), dtype=np.uint8)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, 0, marker_size, marker_img, 1)
    
    # Add a clean white border around marker
    marker_img = cv2.copyMakeBorder(marker_img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    marker_rgb = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2RGB)
    mh, mw, _ = marker_rgb.shape

    # -------------------------------------------------------------
    # SAMPLE 1: COMPLIANT SAMPLE (All rules PASS)
    # -------------------------------------------------------------
    canvas_w, canvas_h = 1200, 800
    comp_img = np.full((canvas_h, canvas_w, 3), 245, dtype=np.uint8) # soft grey background

    # Package box (White background)
    cv2.rectangle(comp_img, (50, 50), (850, 750), (255, 255, 255), -1)
    cv2.rectangle(comp_img, (50, 50), (850, 750), (30, 80, 180), 6) # blue packaging border
    
    # Place ArUco marker on the right side (acting as calibration reference)
    comp_img[80:80+mh, 900:900+mw] = marker_rgb
    cv2.rectangle(comp_img, (890, 70), (910+mw, 90+mh), (120, 120, 120), 2)
    cv2.putText(comp_img, "ArUco Calib: 100mm", (890, 80 + mh + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)

    # Draw text using PIL for clean rendering
    pil_comp = Image.fromarray(comp_img)
    draw = ImageDraw.Draw(pil_comp)

    # Header / Brand
    draw.rectangle([(50, 50), (850, 150)], fill=(30, 80, 180))
    draw.text((80, 75), "NUTRI-GOLD PREMIUM ALMONDS", fill=(255, 255, 255))
    
    # Declarations compliant with Legal Metrology 2011 & GSR 779(E)
    texts_comp = [
        ("COMMODITY: California Almonds (Whole)", 180, (20, 20, 20)),
        ("NET QUANTITY: 250 g", 230, (0, 100, 0)), # Standard SI unit 'g' & proper font size
        ("MRP: Rs. 350.00 (inclusive of all taxes)", 280, (0, 0, 0)), # Inclusive of all taxes
        ("UNIT SALE PRICE (USP): Rs. 1.40 / g", 330, (0, 0, 180)), # Exact 350 / 250 = 1.40 math!
        ("MONTH & YEAR OF PKG: 08/2026", 380, (20, 20, 20)),
        ("BATCH NO: NGA-2026-B4", 430, (20, 20, 20)),
        ("MFD & PACKED BY: NutriGold Agro Foods Pvt Ltd,", 480, (20, 20, 20)),
        ("Plot 42, GIDC Industrial Estate, Naroda, Ahmedabad, Gujarat - 382330", 520, (60, 60, 60)),
        ("FOR COMPLAINTS / FEEDBACK CONTACT CONSUMER CELL:", 580, (20, 20, 20)),
        ("Executive, NutriGold Agro Foods (address as above)", 620, (60, 60, 60)),
        ("Toll-Free: 1800-200-9988 | Email: care@nutrigold.in", 660, (60, 60, 60)),
        ("COUNTRY OF ORIGIN: INDIA", 710, (20, 20, 20)),
    ]

    for line, y_pos, color in texts_comp:
        draw.text((90, y_pos), line, fill=color)

    comp_path = os.path.join(output_dir, "compliant_sample.jpg")
    pil_comp.save(comp_path, quality=95)
    print(f"[OK] Generated: {comp_path}")

    # -------------------------------------------------------------
    # SAMPLE 2: VIOLATION SAMPLE (Triggers Non-Compliance)
    # -------------------------------------------------------------
    # Violations:
    # 1. R001 FAIL: MRP Rs. 350.00 without "inclusive of all taxes"
    # 2. R002 FAIL: Net Wt: 250 gm (Illegal unit 'gm' instead of standard 'g')
    # 3. R008 FAIL: USP Rs. 2.50 / g (Math mismatch: 350 / 250 should be 1.40, not 2.50!)
    # 4. R009 FAIL: Uses prohibited modifier "Approx. Net Wt"
    # -------------------------------------------------------------
    viol_img = np.full((canvas_h, canvas_w, 3), 245, dtype=np.uint8)

    # Package box
    cv2.rectangle(viol_img, (50, 50), (850, 750), (255, 255, 255), -1)
    cv2.rectangle(viol_img, (50, 50), (850, 750), (180, 40, 40), 6) # red packaging border
    
    # Place ArUco marker
    viol_img[80:80+mh, 900:900+mw] = marker_rgb
    cv2.rectangle(viol_img, (890, 70), (910+mw, 90+mh), (120, 120, 120), 2)
    cv2.putText(viol_img, "ArUco Calib: 100mm", (890, 80 + mh + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)

    pil_viol = Image.fromarray(viol_img)
    draw_v = ImageDraw.Draw(pil_viol)

    # Header / Brand
    draw_v.rectangle([(50, 50), (850, 150)], fill=(180, 40, 40))
    draw_v.text((80, 75), "CRUNCHY BITES SPICY NUTS (NON-COMPLIANT)", fill=(255, 255, 255))

    texts_viol = [
        ("COMMODITY: Mixed Spicy Peanuts", 180, (20, 20, 20)),
        ("NET WEIGHT: Approx. 250 gm", 230, (180, 0, 0)), # VIOLATION: "Approx." (R009) & "gm" (R002)
        ("PRICE: Rs. 350.00", 280, (180, 0, 0)),           # VIOLATION: Missing "inclusive of all taxes" (R001)
        ("USP: Rs. 2.50 / g", 330, (180, 0, 0)),            # VIOLATION: Math mismatch 350/250 != 2.50 (R008)
        ("PACKED: 08/2026", 380, (20, 20, 20)),
        ("BATCH: CB-991", 430, (20, 20, 20)),
        ("PACKED BY: Local Foods Ltd, Industrial Area, Solan", 480, (20, 20, 20)), # Missing PIN code!
        ("CONSUMER HELPLINE: 9876543210", 580, (20, 20, 20)),
    ]

    for line, y_pos, color in texts_viol:
        draw_v.text((90, y_pos), line, fill=color)

    viol_path = os.path.join(output_dir, "violation_sample.jpg")
    pil_viol.save(viol_path, quality=95)
    print(f"[OK] Generated: {viol_path}")

    # -------------------------------------------------------------
    # SAMPLE 3: MANUAL REVIEW SAMPLE (Uncalibrated Packaging)
    # -------------------------------------------------------------
    # How it works:
    # 1. All mandatory text declarations (MRP, Net Qty, Mfg Date, Address, Consumer Care, USP) are 100% compliant.
    # 2. NO ArUco marker or reference card is present on the packaging.
    # 3. Calibration pipeline falls back to Tier 4 (NONE / Distance estimate) with LOW confidence.
    # 4. Under Statutory Rule R007 (Principle #2 "Zero Fabricated Certainty"):
    #    The system refuses to guess millimeters from uncalibrated pixels.
    #    It returns MANUAL_REVIEW for font_size.
    # 5. Overall scan status becomes MANUAL_REVIEW (0 FAIL, 1 MANUAL_REVIEW).
    # -------------------------------------------------------------
    review_img = np.full((canvas_h, canvas_w, 3), 245, dtype=np.uint8)

    # Package box (Amber / Gold theme for manual review advisory)
    cv2.rectangle(review_img, (50, 50), (850, 750), (255, 255, 255), -1)
    cv2.rectangle(review_img, (50, 50), (850, 750), (200, 130, 20), 6) # amber packaging border

    # Right side: UNCALIBRATED NOTICE (No ArUco / ID Card)
    cv2.rectangle(review_img, (880, 80), (1170, 480), (255, 255, 255), -1)
    cv2.rectangle(review_img, (880, 80), (1170, 480), (200, 130, 20), 2)
    cv2.putText(review_img, "UNCALIBRATED LABEL", (895, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 90, 0), 2)
    cv2.putText(review_img, "No Fiducial Marker", (895, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1)
    cv2.putText(review_img, "No ArUco or Card", (895, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1)
    cv2.putText(review_img, "Calibration: NONE", (895, 255), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (40, 40, 40), 2)
    cv2.putText(review_img, "Confidence: LOW", (895, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (40, 40, 40), 2)
    cv2.putText(review_img, "Rule 8 Font Height:", (895, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 1)
    cv2.putText(review_img, "INSUFFICIENT DATA", (895, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (200, 50, 0), 2)
    cv2.putText(review_img, "-> MANUAL REVIEW", (895, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 50, 0), 2)

    pil_review = Image.fromarray(review_img)
    draw_r = ImageDraw.Draw(pil_review)

    # Header / Brand
    draw_r.rectangle([(50, 50), (850, 150)], fill=(200, 130, 20))
    draw_r.text((80, 75), "HIMALAYAN ORGANIC GREEN TEA", fill=(255, 255, 255))

    texts_review = [
        ("COMMODITY: Pure Darjeeling Green Tea Bags", 180, (20, 20, 20)),
        ("NET QUANTITY: 100 g", 230, (0, 100, 0)),
        ("MRP: Rs. 220.00 (inclusive of all taxes)", 280, (0, 0, 0)),
        ("UNIT SALE PRICE (USP): Rs. 2.20 / g", 330, (0, 0, 180)),
        ("MONTH & YEAR OF PKG: 09/2026", 380, (20, 20, 20)),
        ("BATCH NO: HGT-2026-M1", 430, (20, 20, 20)),
        ("MFD & PACKED BY: Himalayan Herbals & Foods Pvt Ltd,", 480, (20, 20, 20)),
        ("Plot 14, Phase II, Industrial Area, Baddi, Solan, HP - 173205", 520, (60, 60, 60)),
        ("CONSUMER CARE CELL: Toll-Free 1800-200-8899 | Email: care@himalayanherbals.in", 580, (20, 20, 20)),
        ("FOR FEEDBACK / QUERIES CONTACT: Executive, Himalayan Herbals (address as above)", 630, (60, 60, 60)),
        ("COUNTRY OF ORIGIN: INDIA", 700, (20, 20, 20)),
    ]

    for line, y_pos, color in texts_review:
        draw_r.text((90, y_pos), line, fill=color)

    review_path = os.path.join(output_dir, "manual_review_sample.jpg")
    pil_review.save(review_path, quality=95)
    print(f"[OK] Generated: {review_path}")

    return comp_path, viol_path, review_path

if __name__ == "__main__":
    create_demo_samples()

