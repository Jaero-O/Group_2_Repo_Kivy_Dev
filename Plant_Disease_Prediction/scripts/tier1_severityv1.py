# ============================================================
# TIER 1 & 2: Complete Leaf Feature Extractor (with Inpainting)
# ============================================================

import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from skimage.feature import graycomatrix, graycoprops
from skimage.color import rgb2gray

# -------- SETTINGS --------
image_dir = "../../database/dataset/Anthracnose/" 
output_csv = "leaf_features_complete.csv"
cm_per_pixel = 0.01   # calibrate using a known reference

# -------- UTILITIES --------
def area_cm2(pixels, cm_per_pixel):
    return pixels * (cm_per_pixel ** 2)

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
    """Use OpenCV inpainting to reconstruct missing/damaged leaf areas."""
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
    """Calculates solidity, circularity, and aspect ratio."""
    if cv2.contourArea(contour) == 0:
        return 0, 0, 0, 0, 0
    
    # 1. Solidity: Area / Convex Hull Area
    solidity = float(leaf_area_px) / hull_area if hull_area > 0 else 0

    # 2. Circularity: 4*pi*Area / Perimeter^2
    perimeter = cv2.arcLength(contour, True)
    circularity = (4 * np.pi * leaf_area_px) / (perimeter ** 2) if perimeter > 0 else 0

    # 3. Aspect Ratio: Width / Height of Bounding Box
    _, _, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h if h > 0 else 0
    
    return solidity, circularity, aspect_ratio, perimeter, w, h

def calculate_vegetation_indices(img, mask):
    """Calculates NDVI and ExG using image BGR channels."""
    # Split BGR channels
    B, G, R = img[:,:,0].astype(float), img[:,:,1].astype(float), img[:,:,2].astype(float)
    
    # Normalize channels to 0-1 range (important for robust indices)
    sum_RGB = R + G + B
    r = np.divide(R, sum_RGB, out=np.zeros_like(R), where=sum_RGB!=0)
    g = np.divide(G, sum_RGB, out=np.zeros_like(G), where=sum_RGB!=0)
    
    # ExG (Excess Green) = 2G - R - B (often used with normalized channels: 2g - r - b)
    ExG_map = 2.0 * G - R - B
    
    # Simple NDVI for RGB: (G - R) / (G + R) (NDVI uses Near-Infrared, this is a proxy)
    sum_GR = G + R
    NDVI_proxy_map = np.divide(G - R, sum_GR, out=np.zeros_like(G), where=sum_GR!=0)
    
    # Apply mask and calculate mean values only for the leaf area
    ExG_mean = cv2.mean(ExG_map, mask=mask)[0]
    NDVI_mean = cv2.mean(NDVI_proxy_map, mask=mask)[0]
    
    return ExG_mean, NDVI_mean

def calculate_glcm_texture(img, mask):
    """Calculates GLCM texture features (Contrast, Dissimilarity) for the lesion area."""
    # Convert image to grayscale and scale to 8-bit for GLCM
    img_gray = (rgb2gray(img) * 255).astype(np.uint8)

    # Use a tight bounding box around the lesion mask to minimize computation
    y_coords, x_coords = np.where(mask == 255)
    if len(y_coords) == 0:
        return 0, 0

    y_min, y_max = np.min(y_coords), np.max(y_coords)
    x_min, x_max = np.min(x_coords), np.max(x_coords)
    
    lesion_patch = img_gray[y_min:y_max+1, x_min:x_max+1]
    lesion_mask_patch = mask[y_min:y_max+1, x_min:x_max+1]
    
    if lesion_patch.size == 0 or np.sum(lesion_mask_patch) == 0:
        return 0, 0
    
    # Apply a gentle blur to normalize noise before GLCM
    lesion_patch = cv2.GaussianBlur(lesion_patch, (3, 3), 0)
    
    # GLCM calculation (distance=1, angle=0 for simple texture)
    # GLCM works best on the lesion region's pixel values
    try:
        # Use only values within the mask to compute the matrix
        pixels_in_mask = lesion_patch[lesion_mask_patch > 0]
        
        # If there are not enough unique values, GLCM can fail.
        if len(np.unique(pixels_in_mask)) < 2:
            return 0, 0

        # Create a temporary image where everything outside the lesion is the average of the lesion
        temp_img = lesion_patch.copy()
        temp_img[lesion_mask_patch == 0] = np.mean(pixels_in_mask).astype(np.uint8)

        glcm = graycomatrix(temp_img, [1], [0], levels=256, symmetric=True, normed=True)
        
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        dissimilarity = graycoprops(glcm, 'dissimilarity')[0, 0]
        
        return contrast, dissimilarity
    except ValueError:
        return 0, 0


# -------- MAIN LOOP --------
records = []

for path in Path(image_dir).glob("*.jpg"):
    img = cv2.imread(str(path))
    if img is None:
        continue

    # Resize for consistent feature comparison and speed
    img = cv2.resize(img, (800, int(img.shape[0]*800/img.shape[1])))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # --- segmentation ---
    leaf_mask = segment_leaf(hsv)
    lesion_mask = segment_lesion(hsv, leaf_mask)

    # --- reconstruction (inpainting) ---
    leaf_mask_recon, damage_pct_inpaint, inpainted_img = reconstruct_leaf_inpaint(img, leaf_mask)

    # Find contours on reconstructed leaf and lesions
    leaf_contours, _ = cv2.findContours(leaf_mask_recon, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lesion_contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not leaf_contours:
        continue
    largest_contour = max(leaf_contours, key=cv2.contourArea)

    # --- TIER 1 BASE METRICS ---
    leaf_area_px = cv2.countNonZero(leaf_mask_recon)
    lesion_area_px = cv2.countNonZero(lesion_mask)
    leaf_area_cm2 = area_cm2(leaf_area_px, cm_per_pixel)
    lesion_area_cm2 = area_cm2(lesion_area_px, cm_per_pixel)
    severity_pct = (lesion_area_px / leaf_area_px * 100) if leaf_area_px > 0 else 0
    lesion_count = len(lesion_contours) # TIER 2
    
    # --- TIER 1 Mean Lesion Size ---
    mean_lesion_size_px = (lesion_area_px / lesion_count) if lesion_count > 0 else 0

    # --- TIER 2 SHAPE METRICS ---
    hull = cv2.convexHull(largest_contour)
    hull_area = cv2.contourArea(hull)
    
    solidity, circularity, aspect_ratio, perimeter, bounding_w, bounding_h = \
        calculate_geometry_features(largest_contour, leaf_area_px, hull_area)
    
    # TIER 1 Color Stats
    leaf_mean = cv2.mean(img, mask=leaf_mask_recon)[:3]
    lesion_mean = cv2.mean(img, mask=lesion_mask)[:3]
    
    # TIER 2 Color Ratio
    # We use Green channel as it is most sensitive for stress in this color space
    leaf_G = leaf_mean[1]
    lesion_G = lesion_mean[1]
    color_ratio_G = (lesion_G / leaf_G) if leaf_G > 0 else 0
    
    # --- TIER 2 Vegetative Indices ---
    ExG_mean, NDVI_proxy_mean = calculate_vegetation_indices(img, leaf_mask_recon)

    # --- TIER 2 Texture Features (on Lesion) ---
    glcm_contrast, glcm_dissimilarity = calculate_glcm_texture(img, lesion_mask)


    # --- save record ---
    records.append({
        # CORE IDENTIFIERS
        "filename": path.name,

        # TIER 1: AREA & SEVERITY
        "leaf_area_cm2": leaf_area_cm2,
        "lesion_area_cm2": lesion_area_cm2,
        "severity_pct": severity_pct,
        
        # TIER 1 & 2: COLOR STATS
        "leaf_mean_B": leaf_mean[0],
        "leaf_mean_G": leaf_mean[1],
        "leaf_mean_R": leaf_mean[2],
        "lesion_mean_B": lesion_mean[0],
        "lesion_mean_G": lesion_mean[1],
        "lesion_mean_R": lesion_mean[2],
        "lesion_to_leaf_color_ratio_G": color_ratio_G,
        
        # TIER 2: INDICES
        "ExG_mean": ExG_mean,
        "NDVI_proxy_mean": NDVI_proxy_mean,
        
        # TIER 2: LESION COUNT/SIZE
        "lesion_count": lesion_count,
        "mean_lesion_size_px": mean_lesion_size_px,

        # TIER 2: SHAPE & RECONSTRUCTION
        "leaf_solidity": solidity,
        "leaf_circularity": circularity,
        "leaf_aspect_ratio": aspect_ratio,
        "damage_pct_inpaint": damage_pct_inpaint,
        
        # TIER 2: TEXTURE
        "lesion_glcm_contrast": glcm_contrast,
        "lesion_glcm_dissimilarity": glcm_dissimilarity,
    })

    # --- visualization (optional, for debugging) ---
    overlay = inpainted_img.copy()
    cv2.putText(overlay, f"Severity: {severity_pct:.1f}% | Solidity: {solidity:.2f} | Count: {lesion_count}", 
                (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    cv2.imshow("Complete Leaf Analysis", overlay)
    cv2.waitKey(1)

cv2.destroyAllWindows()

# -------- SAVE --------
df = pd.DataFrame(records)
df.to_csv(output_csv, index=False)
print("✅ Complete Tier 1 & 2 extraction (with inpainting) complete.")
print("\n--- Example Data Output ---\n")

# Utility function for the digestible report
def get_digestible_report(row):
    report = f"🌿 **Leaf Feature Report: {row['filename']}** 🌿\n"
    report += "--------------------------------------------------\n"
    
    # 1. Severity & Impact
    report += "## 📈 Health & Severity (Tier 1)\n"
    report += f"* **% Severity:** **{row['severity_pct']:.2f}%**\n"
    report += f"* **Lesion Area:** {row['lesion_area_cm2']:.2f} cm²\n"
    report += f"* **Leaf Area (Recon):** {row['leaf_area_cm2']:.2f} cm²\n"
    
    report += "\n## 🦠 Lesion Analysis (Tier 1 & 2)\n"
    report += f"* **Lesion Count:** {int(row['lesion_count'])}\n"
    report += f"* **Mean Lesion Size:** {row['mean_lesion_size_px']:.2f} px (Captures spread quality)\n"
    
    # 2. Stress/Health Indicators
    report += "\n## 🧪 Stress Indicators (Tier 2 Indices)\n"
    report += f"* **ExG (Excess Green):** {row['ExG_mean']:.2f} (Higher is greener/healthier)\n"
    report += f"* **NDVI Proxy:** {row['NDVI_proxy_mean']:.2f} (Health/Vigor index)\n"
    report += f"* **Lesion-Leaf Color Ratio (G):** {row['lesion_to_leaf_color_ratio_G']:.2f} (Stress intensity)\n"
    
    # 3. Shape & Damage Assessment
    report += "\n## 📐 Shape & Damage (Tier 2 Geometry)\n"
    report += f"* **Leaf Solidity:** {row['leaf_solidity']:.3f} (Deviation from convex hull. Lower = more holes/damage)\n"
    report += f"* **Circularity:** {row['leaf_circularity']:.3f} (How close to a circle. Ideal leaf $\approx 0.3-0.5$)\n"
    report += f"* **Aspect Ratio:** {row['leaf_aspect_ratio']:.2f} (Width/Height. Captures elongation)\n"
    report += f"* **Inpainting Repair %:** {row['damage_pct_inpaint']:.1f}% (Estimated area reconstructed)\n"
    
    # 4. Texture for ML
    report += "\n## ✨ Texture (ML Features)\n"
    report += f"* **GLCM Contrast:** {row['lesion_glcm_contrast']:.2f} (Local variation. High value = rough/varied lesion texture)\n"
    report += f"* **GLCM Dissimilarity:** {row['lesion_glcm_dissimilarity']:.2f} (Measures distance in intensity pairs)\n"
    
    return report

# --- Main loop and save section remains the same, but I added the call to the report function ---
if not df.empty:
    first_leaf = df.iloc[0]
    print(get_digestible_report(first_leaf))