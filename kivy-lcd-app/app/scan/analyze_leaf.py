# ============================================================
# LEAF ANALYZER MODULE  —  optimized
# ============================================================
#
# Fixes applied vs original:
#  #1  severity_percent key name (was severity_pct — broke DB save)
#  #2  segment_leaf() now only fallback; alpha mask used when available
#  #3  cm_per_pixel documented + calibration notes added
#  #4  No blind resize — works at native res, adjusts calibration if scaled
#  #5  severity_level now computed and returned in record
#  #6  CSV/JSON save to scan_dir, not random cwd
#  #7  GLCM: 4 angles, averaged — rotation-invariant texture
#  #8  GLCM: zeroed non-lesion pixels instead of mean-fill
#  #9  NDVI proxy renamed to GRVI (Green-Red Vegetation Index)
# #10  segment_lesion() catches dark anthracnose centers (near-black)
# #11  Severity thresholds follow CABI/EPPO disease assessment scale
# #12  sum_RGB dead code removed
# #13  GLCM now extracts energy, homogeneity, correlation too
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
#
# How to re-calibrate CM_PER_PIXEL:
# 1. Place a ruler under the camera at the exact scanning height.
# 2. Capture one frame at production resolution (2304x1296).
# 3. Count pixels spanning a known distance, e.g. 1 cm = N pixels.
# 4. Set CM_PER_PIXEL = 1.0 / N
#
# Current: 0.00651 cm/px = 1 px ~ 0.0651 mm
# Calibrated at: LensPosition=9, resolution 2304x1296
# Update this if camera height or zoom changes.
CM_PER_PIXEL       = 0.00651
MAX_ANALYSIS_WIDTH = 2000   # scale down only if wider than this; adjust calibration proportionally


# ============================================================
# SEVERITY SCALE  —  CABI/EPPO standard
# ============================================================
#
# CABI Crop Protection Compendium / EPPO Assessment Keys
# for foliar disease severity in tropical fruit crops:
#
#   0%           -> None
#   0 < x <= 5%  -> Trace
#   5 < x <= 25% -> Low
#  25 < x <= 50% -> Moderate
#       x  > 50% -> High
#
def severity_to_level(pct: float) -> str:
    if pct <= 0:   return "None"
    if pct <= 5:   return "Trace"
    if pct <= 25:  return "Low"
    if pct <= 50:  return "Moderate"
    return "High"


# ============================================================
# UTILITIES
# ============================================================

def area_cm2(pixels: int, cm_per_pixel: float) -> float:
    return pixels * (cm_per_pixel ** 2)


def segment_leaf(img_hsv: np.ndarray) -> np.ndarray:
    """
    HSV green segmentation. FALLBACK ONLY.
    Misses brown/yellow heavily diseased areas — use alpha mask when available.
    """
    mask = cv2.inRange(img_hsv, np.array([20, 40, 40]), np.array([90, 255, 255]))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))


def segment_lesion(img_hsv: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """
    Two-zone lesion detection — handles anthracnose and similar diseases.

    Zone A: Orange-brown margin (H 5-25) — the active lesion ring.
    Zone B: Dark necrotic center (any H, low S, very low V) — dead tissue core.

    The original single-range approach only caught Zone A, causing the dark
    centers to be excluded and severity to be consistently underestimated.
    Both zones are masked to the leaf area to prevent false positives.
    """
    # Zone A: orange-brown lesion margins
    mask_a = cv2.inRange(img_hsv, np.array([5, 30, 20]), np.array([25, 255, 160]))

    # Zone B: near-black necrotic centers (low saturation AND low value)
    mask_b = cv2.inRange(img_hsv, np.array([0, 0, 0]), np.array([180, 80, 60]))

    combined = cv2.bitwise_or(mask_a, mask_b)
    combined = cv2.bitwise_and(combined, leaf_mask)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN,  np.ones((3, 3), np.uint8))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return combined


def reconstruct_leaf_inpaint(img, leaf_mask):
    """
    Estimate physically damaged/missing tissue via convex hull comparison.
    Note: mango leaf margins are slightly wavy so the hull is a minor
    over-estimate of the original boundary. Acceptable for the relative
    damage_pct_inpaint metric; leaf_area_cm2 always uses the actual mask.
    """
    holes = cv2.bitwise_not(leaf_mask)
    holes = cv2.morphologyEx(holes, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(leaf_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return leaf_mask, 0.0, img

    largest  = max(contours, key=cv2.contourArea)
    hull     = cv2.convexHull(largest)
    hull_mask = np.zeros_like(leaf_mask)
    cv2.drawContours(hull_mask, [hull], -1, 255, -1)

    inpaint_mask       = cv2.bitwise_and(holes, hull_mask)
    missing_px         = cv2.countNonZero(inpaint_mask)
    hull_area          = cv2.countNonZero(hull_mask)
    damage_pct_inpaint = (missing_px / hull_area * 100) if hull_area > 0 else 0.0

    inpainted_img      = cv2.inpaint(img, inpaint_mask, 5, cv2.INPAINT_TELEA)
    reconstructed_mask = cv2.bitwise_or(leaf_mask, inpaint_mask)
    return reconstructed_mask, damage_pct_inpaint, inpainted_img


def calculate_geometry_features(contour, leaf_area_px, hull_area):
    if cv2.contourArea(contour) == 0:
        return 0.0, 0.0, 0.0
    solidity     = float(leaf_area_px) / hull_area if hull_area > 0 else 0.0
    perimeter    = cv2.arcLength(contour, True)
    circularity  = (4 * np.pi * leaf_area_px) / (perimeter ** 2) if perimeter > 0 else 0.0
    _, _, w, h   = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h if h > 0 else 0.0
    return solidity, circularity, aspect_ratio


def calculate_vegetation_indices(img, mask):
    """
    ExG  = 2G - R - B           (Excess Green Index — leaf health proxy)
    GRVI = (G - R) / (G + R)    (Green-Red Vegetation Index)

    Note: previously labelled ndvi_proxy. True NDVI needs a NIR channel
    which a standard RGB camera does not have. GRVI is the correct name.
    """
    B = img[:, :, 0].astype(float)
    G = img[:, :, 1].astype(float)
    R = img[:, :, 2].astype(float)
    # FIX #12: removed unused sum_RGB
    ExG_map  = 2.0 * G - R - B
    sum_GR   = G + R
    GRVI_map = np.divide(G - R, sum_GR, out=np.zeros_like(G), where=sum_GR != 0)
    return cv2.mean(ExG_map, mask=mask)[0], cv2.mean(GRVI_map, mask=mask)[0]


def calculate_glcm_texture(img, mask):
    """
    GLCM texture on lesion pixels only.

    FIX #7: 4 angles (0, 45, 90, 135 deg) averaged -> rotation-invariant.
    FIX #8: non-lesion pixels zeroed, not mean-filled -> preserves real signal.
    FIX #13: returns 5 properties: contrast, dissimilarity, energy,
             homogeneity, correlation.

    Returns (contrast, dissimilarity, energy, homogeneity, correlation)
    """
    img_gray         = (rgb2gray(img) * 255).astype(np.uint8)
    y_coords, x_coords = np.where(mask == 255)
    if len(y_coords) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    y_min, y_max = int(np.min(y_coords)), int(np.max(y_coords))
    x_min, x_max = int(np.min(x_coords)), int(np.max(x_coords))
    patch      = img_gray[y_min:y_max + 1, x_min:x_max + 1]
    mask_patch = mask[y_min:y_max + 1, x_min:x_max + 1]

    if patch.size == 0 or np.sum(mask_patch) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    patch = cv2.GaussianBlur(patch, (3, 3), 0)

    try:
        px = patch[mask_patch > 0]
        if len(np.unique(px)) < 2:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        # FIX #8: zero non-lesion pixels
        temp = np.zeros_like(patch)
        temp[mask_patch > 0] = patch[mask_patch > 0]

        # FIX #7: 4 angles
        angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
        glcm   = graycomatrix(temp, distances=[1], angles=angles,
                              levels=256, symmetric=True, normed=True)

        contrast      = float(np.mean(graycoprops(glcm, 'contrast')))
        dissimilarity = float(np.mean(graycoprops(glcm, 'dissimilarity')))
        energy        = float(np.mean(graycoprops(glcm, 'energy')))
        homogeneity   = float(np.mean(graycoprops(glcm, 'homogeneity')))
        correlation   = float(np.mean(graycoprops(glcm, 'correlation')))
        return contrast, dissimilarity, energy, homogeneity, correlation

    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 0.0


# ============================================================
# CORE FUNCTION
# ============================================================

def analyze_leaf(
    image_input,
    leaf_id=None,
    save_to_csv=True,
    save_json=True,
    scan_dir=None,
    leaf_mask_override=None
):
    """
    Analyze a mango leaf image and return a DB-aligned feature record.

    Parameters
    ----------
    image_input        : str | Path | np.ndarray
    leaf_id            : int, optional  (default: current Unix timestamp)
    save_to_csv        : bool
    save_json          : bool
    scan_dir           : str | Path | None  — output directory for CSV/JSON
    leaf_mask_override : np.ndarray | None
        uint8 binary mask (255=leaf, 0=background).
        Pass the alpha channel from the bg-removed PNG.
        Skips HSV green segmentation — correctly handles brown/diseased areas.
    """
    if leaf_id is None:
        leaf_id = int(datetime.now().timestamp())

    # FIX #6
    base_dir  = Path(scan_dir) if scan_dir else Path(".")
    csv_path  = base_dir / "leaf_features.csv"
    json_path = base_dir / "leaf_analysis_results.json"

    # Load
    if isinstance(image_input, (str, Path)):
        img, filename = cv2.imread(str(image_input)), Path(image_input).name
    elif isinstance(image_input, np.ndarray):
        img, filename = image_input.copy(), "array.jpg"
    else:
        raise ValueError("image_input must be a file path or numpy array")

    if img is None:
        print(f"[analyze_leaf] Cannot read '{image_input}'")
        return None, None

    # FIX #3 + #4: resolution-aware calibration — no blind resize
    h0, w0                 = img.shape[:2]
    effective_cm_per_pixel = CM_PER_PIXEL

    if w0 > MAX_ANALYSIS_WIDTH:
        scale                  = MAX_ANALYSIS_WIDTH / w0
        img                    = cv2.resize(img, (MAX_ANALYSIS_WIDTH, int(h0 * scale)),
                                            interpolation=cv2.INTER_AREA)
        effective_cm_per_pixel = CM_PER_PIXEL / scale
        print(f"[analyze_leaf] Scaled {w0}->{img.shape[1]}px | "
              f"cm_per_pixel {CM_PER_PIXEL:.6f}->{effective_cm_per_pixel:.6f}")
        if leaf_mask_override is not None:
            leaf_mask_override = cv2.resize(leaf_mask_override,
                                            (img.shape[1], img.shape[0]),
                                            interpolation=cv2.INTER_NEAREST)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # FIX #2: alpha mask preferred over HSV green
    if leaf_mask_override is not None:
        _, leaf_mask = cv2.threshold(leaf_mask_override, 127, 255, cv2.THRESH_BINARY)
        leaf_mask    = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE,
                                        np.ones((5, 5), np.uint8))
    else:
        print("[analyze_leaf] No alpha mask provided — using HSV fallback")
        leaf_mask = segment_leaf(hsv)

    # FIX #10: two-zone lesion segmentation
    lesion_mask = segment_lesion(hsv, leaf_mask)

    leaf_mask_recon, damage_pct_inpaint, inpainted_img = \
        reconstruct_leaf_inpaint(img, leaf_mask)

    leaf_contours,   _ = cv2.findContours(leaf_mask_recon, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
    lesion_contours, _ = cv2.findContours(lesion_mask,     cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

    if not leaf_contours:
        print(f"[analyze_leaf] No leaf contour found in '{filename}'")
        return None, None

    largest             = max(leaf_contours, key=cv2.contourArea)
    leaf_area_px        = cv2.countNonZero(leaf_mask_recon)
    lesion_area_px      = cv2.countNonZero(lesion_mask)
    severity_pct        = (lesion_area_px / leaf_area_px * 100) if leaf_area_px > 0 else 0.0
    lesion_count        = len(lesion_contours)
    mean_lesion_size_px = (lesion_area_px / lesion_count) if lesion_count > 0 else 0.0

    hull_area   = cv2.contourArea(cv2.convexHull(largest))
    solidity, circularity, aspect_ratio = calculate_geometry_features(
        largest, leaf_area_px, hull_area
    )

    leaf_mean     = cv2.mean(img, mask=leaf_mask_recon)[:3]
    lesion_mean   = cv2.mean(img, mask=lesion_mask)[:3]
    color_ratio_G = (lesion_mean[1] / leaf_mean[1]) if leaf_mean[1] > 0 else 0.0

    exg_mean, grvi_mean = calculate_vegetation_indices(img, leaf_mask_recon)

    (glcm_contrast, glcm_dissimilarity,
     glcm_energy, glcm_homogeneity,
     glcm_correlation) = calculate_glcm_texture(img, lesion_mask)

    # ── Record — DB-aligned ───────────────────────────────────────────────────
    record = {
        "leaf_id":                       leaf_id,
        "date_processed":                datetime.now().isoformat(),
        # Area
        "leaf_area_cm2":                 area_cm2(leaf_area_px,   effective_cm_per_pixel),
        "lesion_area_cm2":               area_cm2(lesion_area_px, effective_cm_per_pixel),
        # Severity (CABI/EPPO)
        "severity_percent":              severity_pct,             # FIX #1 (legacy compatibility)
        "severity_percentage":           severity_pct,             # DB and UI schema key
        "severity_level":                severity_to_level(severity_pct),  # FIX #5 + #11
        # Lesion
        "lesion_count":                  lesion_count,
        "mean_lesion_size_px":           mean_lesion_size_px,
        # Color
        "leaf_mean_r":                   float(leaf_mean[2]),
        "leaf_mean_g":                   float(leaf_mean[1]),
        "leaf_mean_b":                   float(leaf_mean[0]),
        "lesion_mean_r":                 float(lesion_mean[2]),
        "lesion_mean_g":                 float(lesion_mean[1]),
        "lesion_mean_b":                 float(lesion_mean[0]),
        "lesion_to_leaf_color_ratio_g":  color_ratio_G,
        # Vegetation indices
        "exg_mean":                      exg_mean,
        "ndvi_proxy_mean":               grvi_mean,    # FIX #9: align with DB schema
        "grvi_mean":                     grvi_mean,
        # Shape
        "leaf_solidity":                 solidity,
        "leaf_circularity":              circularity,
        "leaf_aspect_ratio":             aspect_ratio,
        # Physical damage
        "damage_pct_inpaint":            damage_pct_inpaint,
        # GLCM texture (5 props, 4-angle average)
        "lesion_glcm_contrast":          glcm_contrast,
        "lesion_glcm_dissimilarity":     glcm_dissimilarity,
        "lesion_glcm_energy":            glcm_energy,       # FIX #13
        "lesion_glcm_homogeneity":       glcm_homogeneity,  # FIX #13
        "lesion_glcm_correlation":       glcm_correlation,  # FIX #13
    }

    # FIX #6
    if save_to_csv:
        exists = csv_path.is_file()
        pd.DataFrame([record]).to_csv(csv_path, mode='a', header=not exists, index=False)
    if save_json:
        with open(json_path, "a") as f:
            json.dump(record, f, indent=2)
            f.write("\n")

    return record, inpainted_img


# ============================================================
# SQL HELPER
# ============================================================
def record_to_sql(record: dict, table_name: str = "leaf_features") -> tuple:
    cols  = ", ".join(record.keys())
    ph    = ", ".join(["%s"] * len(record))
    return f"INSERT INTO {table_name} ({cols}) VALUES ({ph});", tuple(record.values())
