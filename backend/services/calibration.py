"""
Calibration — Phase 2, Step 5
4-tier fallback hierarchy (PRD Section 2.3):
  Tier 1: ArUco marker  → full homography (tilt + scale)
  Tier 2: ID-1 Card     → full homography (tilt + scale)
  Tier 3: Coin          → scale only (no tilt correction)
  Tier 4: None          → pinhole model (lowest confidence)
"""
import cv2
import numpy as np
from typing import Optional, Tuple


# ─── Constants ────────────────────────────────────────────────────────────────

# ISO 7810 ID-1 card dimensions (Aadhaar, PAN, driving licence, credit card)
ID1_WIDTH_MM = 85.6
ID1_HEIGHT_MM = 53.98

# RBI-standardized Indian coin diameters
COIN_DIAMETERS_MM = {
    "1_rupee": 21.93,
    "2_rupee": 25.0,
    "5_rupee": 23.0,
    "10_rupee": 27.0,
}
DEFAULT_COIN_MM = 23.0  # ₹5 coin — most common

# ArUco dictionary to use — DICT_4X4_50 is small and fast to detect
ARUCO_DICT = cv2.aruco.DICT_4X4_50
ARUCO_REAL_SIZE_MM = 100.0  # 10cm × 10cm printed marker


# ─── Tier 1: ArUco Marker ────────────────────────────────────────────────────

def detect_aruco(image: np.ndarray) -> dict:
    """
    Detects an ArUco marker and computes a full homography matrix.

    Returns:
        {
            "ok": bool,
            "homography": np.ndarray (3×3) or None,
            "px_per_mm": float or None,
            "tilt_corrected": bool,
            "confidence": "HIGH"|"MEDIUM"|"LOW",
            "tier": "ARUCO",
            "error": str (only on failure)
        }
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)

    if ids is None or len(corners) == 0:
        return {
            "ok": False,
            "homography": None,
            "px_per_mm": None,
            "tilt_corrected": False,
            "confidence": "LOW",
            "tier": "ARUCO",
            "error": "No ArUco marker detected in the image.",
        }

    # Use the first detected marker
    marker_corners = corners[0][0]  # shape (4, 2)

    # Real-world corners of the printed marker (100mm × 100mm)
    half = ARUCO_REAL_SIZE_MM / 2
    real_corners = np.array([
        [-half, -half],
        [ half, -half],
        [ half,  half],
        [-half,  half],
    ], dtype=np.float32)

    # Compute homography: maps image pixel coords → real-world mm coords
    H, _ = cv2.findHomography(marker_corners, real_corners)

    # Estimate px/mm from the marker's pixel size
    side_px = np.linalg.norm(marker_corners[1] - marker_corners[0])
    px_per_mm = side_px / ARUCO_REAL_SIZE_MM

    return {
        "ok": True,
        "homography": H,
        "px_per_mm": round(float(px_per_mm), 4),
        "tilt_corrected": True,
        "confidence": "HIGH",
        "tier": "ARUCO",
    }


# ─── Tier 2: ID-1 Card ───────────────────────────────────────────────────────

def detect_id_card(image: np.ndarray) -> dict:
    """
    Detects an ISO 7810 ID-1 card (Aadhaar, PAN, DL, credit card) by contour.
    Privacy safeguard: ONLY the geometric outline is read.
    The image region of the card is NEVER sent to any external API.

    Returns same structure as detect_aruco().
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_card = None
    target_ratio = ID1_WIDTH_MM / ID1_HEIGHT_MM  # 1.586

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 5000:  # too small to be a card
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(approx) == 4:  # rectangular contour
            rect = cv2.minAreaRect(approx)
            w, h = rect[1]
            if w == 0 or h == 0:
                continue
            ratio = max(w, h) / min(w, h)

            if abs(ratio - target_ratio) < 0.15:  # ±15% tolerance
                best_card = approx.reshape(4, 2).astype(np.float32)
                break

    if best_card is None:
        return {
            "ok": False,
            "homography": None,
            "px_per_mm": None,
            "tilt_corrected": False,
            "confidence": "LOW",
            "tier": "ID_CARD",
            "error": "No ID-1 card (85.6mm × 53.98mm) detected. Try ArUco marker or coin.",
        }

    # Order corners: top-left, top-right, bottom-right, bottom-left
    pts = _order_corners(best_card)

    real_corners = np.array([
        [0, 0],
        [ID1_WIDTH_MM, 0],
        [ID1_WIDTH_MM, ID1_HEIGHT_MM],
        [0, ID1_HEIGHT_MM],
    ], dtype=np.float32)

    H, _ = cv2.findHomography(pts, real_corners)

    # px/mm from card width
    card_width_px = np.linalg.norm(pts[1] - pts[0])
    px_per_mm = card_width_px / ID1_WIDTH_MM

    return {
        "ok": True,
        "homography": H,
        "px_per_mm": round(float(px_per_mm), 4),
        "tilt_corrected": True,
        "confidence": "HIGH",
        "tier": "ID_CARD",
    }


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]    # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]    # bottom-right: largest sum
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # top-right: smallest diff
    rect[3] = pts[np.argmax(diff)] # bottom-left: largest diff
    return rect


# ─── Tier 3: Coin ────────────────────────────────────────────────────────────

def detect_coin(image: np.ndarray, coin_diameter_mm: float = DEFAULT_COIN_MM) -> dict:
    """
    Detects a circular coin using Hough Circle Transform and computes
    a scale-only pixels-per-mm ratio. NOTE: No tilt correction.

    Args:
        image: Input BGR image.
        coin_diameter_mm: Known real-world diameter of the coin.

    Returns same structure (but tilt_corrected=False, confidence="MEDIUM").
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # medianBlur reduces noise that confuses Hough detection
    blurred = cv2.medianBlur(gray, 5)

    h, w = image.shape[:2]
    min_radius = max(20, int(min(h, w) * 0.03))
    max_radius = int(min(h, w) * 0.25)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(h, w) // 4,
        param1=100,
        param2=75,       # Robust accumulator threshold avoids false positives on text lines
        minRadius=min_radius,
        maxRadius=max_radius,
    )

    if circles is None:
        return {
            "ok": False,
            "homography": None,
            "px_per_mm": None,
            "tilt_corrected": False,
            "confidence": "LOW",
            "tier": "COIN",
            "error": "No circular coin detected. Ensure coin is clearly visible with good contrast.",
        }

    # Use the most prominent circle (first after rounding)
    circles = np.uint16(np.around(circles))
    x, y, radius_px = circles[0][0]

    diameter_px = radius_px * 2
    px_per_mm = diameter_px / coin_diameter_mm

    return {
        "ok": True,
        "homography": None,  # No homography for scale-only
        "px_per_mm": round(float(px_per_mm), 4),
        "tilt_corrected": False,
        "confidence": "MEDIUM",
        "tier": "COIN",
        "coin_center": (int(x), int(y)),
        "coin_radius_px": int(radius_px),
    }


# ─── Tier 4: None (pinhole model) ────────────────────────────────────────────

def estimate_from_distance(
    image_height_px: int,
    working_distance_mm: float = 300.0,
    focal_length_px: Optional[float] = None,
) -> dict:
    """
    Tier 4 fallback: estimates scale using fixed working distance.
    Accuracy depends entirely on officer compliance with the on-screen guide.

    Args:
        image_height_px: Height of the image in pixels.
        working_distance_mm: Distance from camera to label (enforced by UI guide).
        focal_length_px: Camera focal length in pixels. If None, uses a
                         typical smartphone approximation.
    """
    if focal_length_px is None:
        # Rough approximation for a typical 12MP smartphone camera
        focal_length_px = image_height_px * 1.2

    px_per_mm = focal_length_px / working_distance_mm

    return {
        "ok": True,
        "homography": None,
        "px_per_mm": round(float(px_per_mm), 4),
        "tilt_corrected": False,
        "confidence": "LOW",
        "tier": "NONE",
        "note": "Scale estimated from fixed working distance — low confidence, no physical reference.",
    }


# ─── Calibration Orchestrator ─────────────────────────────────────────────────

def calibrate(image_path: str, requested_tier: str = "ARUCO", coin_mm: float = DEFAULT_COIN_MM) -> dict:
    """
    Main calibration entry point. Tries the requested tier and falls back
    automatically if detection fails.

    Args:
        image_path: Path to the image file.
        requested_tier: "ARUCO" | "ID_CARD" | "COIN" | "NONE"
        coin_mm: Coin diameter in mm (only used for COIN tier).

    Returns:
        Calibration result dict with tier, px_per_mm, confidence, etc.
    """
    image = cv2.imread(image_path)
    if image is None:
        return {
            "ok": False,
            "tier": "NONE",
            "px_per_mm": None,
            "confidence": "LOW",
            "error": f"Could not read image: {image_path}",
        }

    h, w = image.shape[:2]

    # Try requested tier first, then fall back in order
    tier_order = ["ARUCO", "ID_CARD", "COIN", "NONE"]
    start_idx = tier_order.index(requested_tier) if requested_tier in tier_order else 0

    for tier in tier_order[start_idx:]:
        if tier == "ARUCO":
            result = detect_aruco(image)
        elif tier == "ID_CARD":
            result = detect_id_card(image)
        elif tier == "COIN":
            result = detect_coin(image, coin_diameter_mm=coin_mm)
        else:
            result = estimate_from_distance(h)

        if result["ok"]:
            return result

    # Ultimate fallback — distance estimate always "succeeds"
    return estimate_from_distance(h)


# ─── Font Height Measurement ──────────────────────────────────────────────────

def measure_font_height(
    symbols: list,
    calibration_result: dict,
    image_width: int,
    surface_type: str = "FLAT",
) -> dict:
    """
    Converts symbol-level pixel bounding boxes to mm using calibration ratio.

    For curved surfaces: only measures symbols within center strip (35%–65% width).
    Anything outside → MANUAL_REVIEW.

    Args:
        symbols: List of symbol dicts from ocr_service.extract_symbols()
        calibration_result: Output from calibrate()
        image_width: Width of the image in pixels
        surface_type: "FLAT" | "CURVED"

    Returns:
        {
            "height_mm": float or None,
            "confidence": "HIGH"|"MEDIUM"|"LOW",
            "method": str,
            "outside_strip": bool,
            "symbols_measured": int,
        }
    """
    px_per_mm = calibration_result.get("px_per_mm")
    confidence = calibration_result.get("confidence", "LOW")

    if not px_per_mm or px_per_mm <= 0:
        return {
            "height_mm": None,
            "confidence": "LOW",
            "method": "no_calibration",
            "outside_strip": False,
            "symbols_measured": 0,
        }

    if not symbols:
        return {
            "height_mm": None,
            "confidence": confidence,
            "method": "no_symbols",
            "outside_strip": False,
            "symbols_measured": 0,
        }

    # For curved surfaces, constrain to center strip (PRD Section 2.4)
    strip_left = int(image_width * 0.35)
    strip_right = int(image_width * 0.65)

    valid_symbols = []
    outside_count = 0

    for sym in symbols:
        bb = sym["bounding_box"]
        center_x = bb["x"] + bb["width"] / 2

        if surface_type == "CURVED":
            if not (strip_left <= center_x <= strip_right):
                outside_count += 1
                continue  # skip — outside trusted strip

        if bb["height"] > 0:
            valid_symbols.append(bb["height"])

    if not valid_symbols:
        return {
            "height_mm": None,
            "confidence": "LOW",
            "method": "all_outside_strip" if surface_type == "CURVED" else "no_valid_symbols",
            "outside_strip": outside_count > 0,
            "symbols_measured": 0,
        }

    # Use median height (more robust than mean against outliers)
    median_height_px = float(np.median(valid_symbols))
    height_mm = median_height_px / px_per_mm

    return {
        "height_mm": round(height_mm, 3),
        "confidence": confidence,
        "method": f"calibrated_{calibration_result.get('tier', 'UNKNOWN').lower()}",
        "outside_strip": outside_count > 0,
        "symbols_measured": len(valid_symbols),
    }
