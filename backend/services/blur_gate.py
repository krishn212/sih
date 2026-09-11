"""
Blur Gate — Phase 2, Step 7
Uses Laplacian variance to detect blurry images before sending them
through the expensive OCR + calibration pipeline.
"""
import cv2
import numpy as np

# Configurable threshold — images below this variance are rejected.
# 100 is a reasonable starting point; tune based on real product photos.
DEFAULT_THRESHOLD = 100.0


def check_blur(image_path: str, threshold: float = DEFAULT_THRESHOLD) -> dict:
    """
    Checks whether an image is too blurry to process reliably.

    Args:
        image_path: Absolute or relative path to the image file.
        threshold: Laplacian variance below this value → rejected.

    Returns:
        {
            "ok": bool,
            "variance": float,
            "threshold": float,
            "reason": str  # only present when ok=False
        }
    """
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return {
            "ok": False,
            "variance": 0.0,
            "threshold": threshold,
            "reason": "Could not read image file. Check the file path and format.",
        }

    variance = cv2.Laplacian(image, cv2.CV_64F).var()

    if variance < threshold:
        return {
            "ok": False,
            "variance": round(float(variance), 2),
            "threshold": threshold,
            "reason": (
                f"Image is too blurry (sharpness score: {variance:.1f}, "
                f"minimum required: {threshold}). Please retake the photo."
            ),
        }

    return {
        "ok": True,
        "variance": round(float(variance), 2),
        "threshold": threshold,
    }
