# ============================================================
# LEAF ANALYZER MODULE - INTEGRATED VERSION
# ============================================================

import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from skimage.feature import graycomatrix, graycoprops
from skimage.color import rgb2gray
import json

# ============================================================
# SETTINGS
# ============================================================
output_csv = "leaf_features.csv"
cm_per_pixel = 0.00651  # calibration factor (adjust for your setup)


# ============================================================
# UTILITIES
# ============================================================
def area_cm2(pixels, cm_per_pixel):
    return pixels * (cm_per_pixel ** 2)

def area_mm2(pixels, cm_per_pixel):
    """Convert pixel area to mm²"""
    return pixels * (cm_per_pixel ** 2) * 100  # cm² to mm²

def segment_leaf(img_hsv):
    lower = np.array([20, 40, 40])
    upper = np.array([90, 255, 255])
    mask = cv2.inRange(img_hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
    return mask

def segment_lesion(img_hsv, leaf_mask):
    lower = np.array([5, 30, 0])
    upper = np.array([25, 255, 160])
    mask = cv2.inRange(img_hsv, lower, upper)
    mask = cv2.bitwise_and(mask, leaf_mask)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    return mask

def reconstruct_leaf_inpaint(img, leaf_mask):
    holes = cv2.bitwise_not(leaf_mask)
    holes = cv2.morphologyEx(holes, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return leaf_mask, 0, img

    largest_contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(largest_contour)
    hull_mask = np.zeros_like(leaf_mask)
    cv2.drawContours(hull_mask, [hull], -1, 255, -1)
    inpaint_mask = cv2.bitwise_and(holes, hull_mask)

    missing_px = cv2.countNonZero(inpaint_mask)
    hull_area = cv2.countNonZero(hull_mask)
    damage_pct_inpaint = (missing_px / hull_area * 100) if hull_area > 0 else 0

    inpainted_img = cv2.inpaint(img, inpaint_mask, 5, cv2.INPAINT_TELEA)
    reconstructed_mask = cv2.bitwise_or(leaf_mask, inpaint_mask)
    return reconstructed_mask, damage_pct_inpaint, inpainted_img

def calculate_geometry_features(contour, leaf_area_px, hull_area):
    if cv2.contourArea(contour) == 0:
        return 0, 0, 0
    solidity = float(leaf_area_px) / hull_area if hull_area > 0 else 0
    perimeter = cv2.arcLength(contour, True)
    circularity = (4 * np.pi * leaf_area_px) / (perimeter ** 2) if perimeter > 0 else 0
    _, _, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h if h > 0 else 0
    return solidity, circularity, aspect_ratio

def calculate_vegetation_indices(img, mask):
    B, G, R = img[:,:,0].astype(float), img[:,:,1].astype(float), img[:,:,2].astype(float)
    sum_RGB = R + G + B
    ExG_map = 2.0 * G - R - B
    sum_GR = G + R
    NDVI_proxy_map = np.divide(G - R, sum_GR, out=np.zeros_like(G), where=sum_GR!=0)
    ExG_mean = cv2.mean(ExG_map, mask=mask)[0]
    NDVI_mean = cv2.mean(NDVI_proxy_map, mask=mask)[0]
    return ExG_mean, NDVI_mean

def calculate_glcm_texture(img, mask):
    img_gray = (rgb2gray(img) * 255).astype(np.uint8)
    y_coords, x_coords = np.where(mask == 255)
    if len(y_coords) == 0:
        return 0, 0
    y_min, y_max = np.min(y_coords), np.max(y_coords)
    x_min, x_max = np.min(x_coords), np.max(x_coords)
    lesion_patch = img_gray[y_min:y_max+1, x_min:x_max+1]
    lesion_mask_patch = mask[y_min:y_max+1, x_min:x_max+1]
    if lesion_patch.size == 0 or np.sum(lesion_mask_patch) == 0:
        return 0, 0
    lesion_patch = cv2.GaussianBlur(lesion_patch, (3, 3), 0)
    try:
        pixels_in_mask = lesion_patch[lesion_mask_patch > 0]
        if len(np.unique(pixels_in_mask)) < 2:
            return 0, 0
        temp_img = lesion_patch.copy()
        temp_img[lesion_mask_patch == 0] = np.mean(pixels_in_mask).astype(np.uint8)
        glcm = graycomatrix(temp_img, [1], [0], levels=256, symmetric=True, normed=True)
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        dissimilarity = graycoprops(glcm, 'dissimilarity')[0, 0]
        return contrast, dissimilarity
    except ValueError:
        return 0, 0


# ============================================================
# CORE FUNCTION — PIPELINE-READY
# ============================================================
def analyze_leaf(image_input, leaf_id=None, save_to_csv=True, save_json=True):
    """
    Analyze leaf image and return comprehensive features.
    
    Args:
        image_input: Path to image file or numpy array
        leaf_id: Optional leaf identifier
        save_to_csv: Save results to CSV
        save_json: Save results to JSON
    
    Returns:
        (record: dict, visualization_img: np.ndarray)
        Record contains all features needed for pipeline integration
    """
    
    if leaf_id is None:
        leaf_id = int(datetime.now().timestamp())

    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
        filename = Path(image_input).name
    elif isinstance(image_input, np.ndarray):
        img = image_input
        filename = "leaf_image_array.jpg"
    else:
        raise ValueError("image_input must be a file path or numpy array")

    if img is None:
        print("Error: Unable to read image.")
        return None, None

    img = cv2.resize(img, (800, int(img.shape[0]*800/img.shape[1])))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    leaf_mask = segment_leaf(hsv)
    lesion_mask = segment_lesion(hsv, leaf_mask)
    leaf_mask_recon, damage_pct_inpaint, inpainted_img = reconstruct_leaf_inpaint(img, leaf_mask)

    leaf_contours, _ = cv2.findContours(leaf_mask_recon, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lesion_contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not leaf_contours:
        print(f"Warning: No leaf contour found for {filename}")
        return None, None

    largest_contour = max(leaf_contours, key=cv2.contourArea)
    leaf_area_px = cv2.countNonZero(leaf_mask_recon)
    lesion_area_px = cv2.countNonZero(lesion_mask)
    severity_pct = (lesion_area_px / leaf_area_px * 100) if leaf_area_px > 0 else 0
    lesion_count = len(lesion_contours)
    mean_lesion_size_px = (lesion_area_px / lesion_count) if lesion_count > 0 else 0
    hull = cv2.convexHull(largest_contour)
    hull_area = cv2.contourArea(hull)
    solidity, circularity, aspect_ratio = calculate_geometry_features(largest_contour, leaf_area_px, hull_area)
    leaf_mean = cv2.mean(img, mask=leaf_mask_recon)[:3]
    lesion_mean = cv2.mean(img, mask=lesion_mask)[:3]
    color_ratio_G = (lesion_mean[1] / leaf_mean[1]) if leaf_mean[1] > 0 else 0
    ExG_mean, NDVI_proxy_mean = calculate_vegetation_indices(img, leaf_mask_recon)
    glcm_contrast, glcm_dissimilarity = calculate_glcm_texture(img, lesion_mask)

    # Calculate areas in different units
    leaf_area_cm2_val = area_cm2(leaf_area_px, cm_per_pixel)
    lesion_area_cm2_val = area_cm2(lesion_area_px, cm_per_pixel)
    leaf_area_mm2_val = area_mm2(leaf_area_px, cm_per_pixel)
    lesion_area_mm2_val = area_mm2(lesion_area_px, cm_per_pixel)

    # ============================================================
    # CREATE RECORD (PIPELINE & DB COMPATIBLE)
    # ============================================================
    record = {
        # Identifiers
        "leaf_id": leaf_id,
        "date_processed": datetime.now().isoformat(),
        
        # Areas - cm²
        "leaf_area_cm2": leaf_area_cm2_val,
        "lesion_area_cm2": lesion_area_cm2_val,
        
        # Areas - mm² (for pipeline compatibility)
        "total_leaf_area_mm2": leaf_area_mm2_val,
        "lesion_area_mm2": lesion_area_mm2_val,
        
        # Severity
        "severity_percentage": severity_pct,  # Pipeline expects this key
        "severity_pct": severity_pct,  # Keep for backward compatibility
        
        # Lesion metrics
        "lesion_count": lesion_count,
        "mean_lesion_size_px": mean_lesion_size_px,
        
        # Color features
        "leaf_mean_r": leaf_mean[2],
        "leaf_mean_g": leaf_mean[1],
        "leaf_mean_b": leaf_mean[0],
        "lesion_mean_r": lesion_mean[2],
        "lesion_mean_g": lesion_mean[1],
        "lesion_mean_b": lesion_mean[0],
        "lesion_to_leaf_color_ratio_g": color_ratio_G,
        
        # Vegetation indices
        "exg_mean": ExG_mean,
        "ndvi_proxy_mean": NDVI_proxy_mean,
        
        # Geometry
        "leaf_solidity": solidity,
        "leaf_circularity": circularity,
        "leaf_aspect_ratio": aspect_ratio,
        
        # Damage
        "damage_pct_inpaint": damage_pct_inpaint,
        
        # Texture
        "lesion_glcm_contrast": glcm_contrast,
        "lesion_glcm_dissimilarity": glcm_dissimilarity
    }

    # ============================================================
    # SAVE OPTIONS
    # ============================================================
    if save_to_csv:
        file_exists = Path(output_csv).is_file()
        pd.DataFrame([record]).to_csv(output_csv, mode='a', header=not file_exists, index=False)
    
    if save_json:
        with open("leaf_analysis_results.json", "a") as f:
            json.dump(record, f)
            f.write("\n")

    # ============================================================
    # CREATE VISUALIZATION (Optional)
    # ============================================================
    vis_img = img.copy()
    # Draw leaf contour in green
    cv2.drawContours(vis_img, [largest_contour], -1, (0, 255, 0), 2)
    # Draw lesion areas in red
    vis_img[lesion_mask > 0] = (0, 0, 255)
    
    # Add text overlay
    cv2.putText(vis_img, f"Severity: {severity_pct:.1f}%", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(vis_img, f"Lesions: {lesion_count}", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return record, vis_img


# ============================================================
# SIMPLIFIED SEVERITY COMPUTATION (For pipeline compatibility)
# ============================================================
def compute_severity_with_areas(image_path):
    """
    Compute severity percentage with area measurements.
    Returns tuple: (severity_pct, total_leaf_area_mm2, lesion_area_mm2)
    
    This function is called by the pipeline when it needs just severity data.
    """
    record, _ = analyze_leaf(image_path, save_to_csv=False, save_json=False)
    
    if record is None:
        return 0.0, 0.0, 0.0
    
    return (
        record["severity_percentage"],
        record["total_leaf_area_mm2"],
        record["lesion_area_mm2"]
    )


def compute_severity(image_path):
    """
    Legacy function - compute only severity percentage.
    Kept for backward compatibility.
    """
    severity, _, _ = compute_severity_with_areas(image_path)
    return severity


# ============================================================
# SQL HELPER
# ============================================================
def record_to_sql(record, table_name="leaf_features"):
    """Generate SQL INSERT statement from record"""
    cols = ", ".join(record.keys())
    placeholders = ", ".join(["%s"] * len(record))
    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders});"
    values = tuple(record.values())
    return sql, values


# ============================================================
# CLI ENTRY POINT (for testing)
# ============================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_leaf.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    record, vis_img = analyze_leaf(image_path)
    
    if record:
        print("\n" + "="*60)
        print("LEAF ANALYSIS RESULTS")
        print("="*60)
        print(json.dumps(record, indent=2))
        print("="*60)
        
        if vis_img is not None:
            output_path = f"leaf_analysis_{record['leaf_id']}.jpg"
            cv2.imwrite(output_path, vis_img)
            print(f"\nVisualization saved to: {output_path}")
    else:
        print("Analysis failed.")
        sys.exit(1)
