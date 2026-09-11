"""
ArUco marker generator.
Run this once: python utils/aruco_generator.py
Print the output file at exactly 10cm × 10cm.
"""
import cv2
import numpy as np
import os

def generate_aruco_marker(
    marker_id: int = 0,
    size_px: int = 700,
    output_path: str = "../docs/aruco_marker.png",
):
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_image = np.zeros((size_px, size_px), dtype=np.uint8)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px, marker_image, 1)

    # Add white border for printing
    border = 50
    final = cv2.copyMakeBorder(
        marker_image, border, border, border, border,
        cv2.BORDER_CONSTANT, value=255
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, final)
    print(f"[OK] ArUco marker saved to: {output_path}")
    print(f"   -> Print at exactly 10cm x 10cm (100mm x 100mm)")
    print(f"   -> Marker ID: {marker_id}, Dictionary: DICT_4X4_50")


if __name__ == "__main__":
    generate_aruco_marker()
