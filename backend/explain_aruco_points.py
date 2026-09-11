"""
Generates an annotated diagram of the ArUco marker clearly labeling:
- The 4 outer corners of the white padding (W1, W2, W3, W4)
- The 4 outer corners of the BLACK square that OpenCV DETECTS (P0, P1, P2, P3)
"""
import os
import cv2
import numpy as np

def generate_annotated_marker():
    output_dir = os.path.join(os.path.dirname(__file__), "demo_samples")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate ArUco marker
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 400
    marker_img = np.zeros((marker_size, marker_size), dtype=np.uint8)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, 0, marker_size, marker_img, 1)

    # Add white border
    border = 100
    final = cv2.copyMakeBorder(
        marker_img, border, border, border, border,
        cv2.BORDER_CONSTANT, value=255
    )
    h, w = final.shape
    canvas = cv2.cvtColor(final, cv2.COLOR_GRAY2BGR)

    # Expand canvas horizontally to add detailed labels and arrows
    pad_left = 150
    pad_right = 450
    pad_top = 100
    pad_bottom = 120
    full_canvas = np.full((h + pad_top + pad_bottom, w + pad_left + pad_right, 3), 250, dtype=np.uint8)
    full_canvas[pad_top:pad_top+h, pad_left:pad_left+w] = canvas

    # Offset calculations
    # Black square corners in full_canvas coordinates:
    # Top-Left, Top-Right, Bottom-Right, Bottom-Left
    p0 = (pad_left + border, pad_top + border)
    p1 = (pad_left + border + marker_size, pad_top + border)
    p2 = (pad_left + border + marker_size, pad_top + border + marker_size)
    p3 = (pad_left + border, pad_top + border + marker_size)

    # White padding corners:
    w0 = (pad_left, pad_top)
    w1 = (pad_left + w, pad_top)
    w2 = (pad_left + w, pad_top + h)
    w3 = (pad_left, pad_top + h)

    # Draw white outer bounding box in dotted grey
    cv2.rectangle(full_canvas, w0, w2, (180, 180, 180), 2)

    # Draw detected green box on the outer edge of the black square
    cv2.rectangle(full_canvas, p0, p2, (0, 200, 0), 4)

    # Draw circles on the 4 DETECTED points (Green filled circles)
    pts = [p0, p1, p2, p3]
    labels = ["P0 (Top-Left)", "P1 (Top-Right)", "P2 (Bottom-Right)", "P3 (Bottom-Left)"]
    offsets = [(-110, -15), (15, -15), (15, 25), (-110, 25)]

    for i, pt in enumerate(pts):
        cv2.circle(full_canvas, pt, 10, (0, 0, 255), -1) # Red center
        cv2.circle(full_canvas, pt, 14, (0, 200, 0), 3)  # Green outer ring
        ox, oy = offsets[i]
        cv2.putText(full_canvas, f"P{i}", (pt[0] + ox, pt[1] + oy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 0), 2)

    # Draw circles on the 4 White Border points (Grey circles)
    w_pts = [w0, w1, w2, w3]
    for i, pt in enumerate(w_pts):
        cv2.circle(full_canvas, pt, 7, (120, 120, 120), -1)
        cv2.putText(full_canvas, f"W{i}", (pt[0] - 20, pt[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 100), 2)

    # Dimension line showing 100 mm across the black square
    dim_y = pad_top + border + marker_size + 45
    cv2.line(full_canvas, (p0[0], dim_y), (p1[0], dim_y), (200, 50, 0), 2)
    cv2.line(full_canvas, (p0[0], dim_y - 10), (p0[0], dim_y + 10), (200, 50, 0), 2)
    cv2.line(full_canvas, (p1[0], dim_y - 10), (p1[0], dim_y + 10), (200, 50, 0), 2)
    cv2.putText(full_canvas, "<---- 100 mm (10 cm) ---->", (p0[0] + 35, dim_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 50, 0), 2)

    # Explanatory Side Panel
    panel_x = pad_left + w + 30
    cv2.putText(full_canvas, "POINT BREAKDOWN", (panel_x, pad_top + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
    
    cv2.putText(full_canvas, "[X] 4 DETECTED CORNERS:", (panel_x, pad_top + 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 160, 0), 2)
    cv2.putText(full_canvas, "- P0: Top-Left Black Corner", (panel_x + 15, pad_top + 105),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (40, 40, 40), 1)
    cv2.putText(full_canvas, "- P1: Top-Right Black Corner", (panel_x + 15, pad_top + 135),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (40, 40, 40), 1)
    cv2.putText(full_canvas, "- P2: Bottom-Right Black Corner", (panel_x + 15, pad_top + 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (40, 40, 40), 1)
    cv2.putText(full_canvas, "- P3: Bottom-Left Black Corner", (panel_x + 15, pad_top + 195),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (40, 40, 40), 1)

    cv2.putText(full_canvas, "==> OpenCV detects P0, P1, P2, P3", (panel_x + 15, pad_top + 235),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 130, 0), 2)
    cv2.putText(full_canvas, "    Distance (P0 to P1) = Exactly 100 mm", (panel_x + 15, pad_top + 265),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (200, 50, 0), 2)

    cv2.putText(full_canvas, "[O] 4 IGNORED CORNERS (Quiet Zone):", (panel_x, pad_top + 325),
                cv2.FONT_HERSHEY_SIMPLEX, 0.68, (120, 120, 120), 2)
    cv2.putText(full_canvas, "- W0, W1, W2, W3: Outer White Border", (panel_x + 15, pad_top + 355),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (80, 80, 80), 1)
    cv2.putText(full_canvas, "- Purpose: Contrast buffer so the black", (panel_x + 15, pad_top + 385),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1)
    cv2.putText(full_canvas, "  square is easily found by OpenCV.", (panel_x + 15, pad_top + 410),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1)

    out_file = os.path.join(output_dir, "aruco_corners_explained.jpg")
    cv2.imwrite(out_file, full_canvas)
    print(f"[OK] Generated explanation image: {out_file}")

if __name__ == "__main__":
    generate_annotated_marker()
