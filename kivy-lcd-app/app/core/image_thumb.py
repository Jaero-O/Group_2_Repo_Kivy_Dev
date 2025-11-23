import os
from typing import Tuple, Optional
from PIL import Image

DEFAULT_MAX_SIZE: Tuple[int, int] = (150, 150)  # Updated to 150x150 per specifications


def _derive_thumbnail_path(image_path: str) -> str:
    base_dir = os.path.dirname(image_path)
    name, ext = os.path.splitext(os.path.basename(image_path))
    thumbs_dir = os.path.join(base_dir, "thumbs")
    os.makedirs(thumbs_dir, exist_ok=True)
    # Normalize extension to jpg for thumbnails
    return os.path.join(thumbs_dir, f"{name}_thumb.jpg")


def generate_thumbnail(image_path: str, thumb_path: Optional[str] = None,
                       max_size: Tuple[int, int] = DEFAULT_MAX_SIZE) -> Optional[str]:
    """
    Generate (or reuse) a thumbnail for the provided image path.
    Returns the thumbnail file path or None if generation failed.
    - Ensures aspect ratio is preserved.
    - Converts mode to RGB.
    - Saves as JPEG with moderate quality.
    - Default size: 150x150px per UI specifications.
    """
    if not image_path or not os.path.isfile(image_path):
        return None
    try:
        thumb_path = thumb_path or _derive_thumbnail_path(image_path)
        # Always regenerate if source is newer (or thumbnail missing)
        if os.path.isfile(thumb_path) and os.path.getmtime(thumb_path) >= os.path.getmtime(image_path):
            return thumb_path
        with Image.open(image_path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            # Use thumbnail to preserve aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            # If RGBA, composite over white background
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            img.save(thumb_path, format="JPEG", quality=85, optimize=True)
        return thumb_path
    except Exception as e:
        print(f"[thumbnail] Generation failed for {image_path}: {e}")
        return None
