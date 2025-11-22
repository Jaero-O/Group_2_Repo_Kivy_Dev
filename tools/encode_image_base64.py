#!/usr/bin/env python3
"""Encode an image (PNG/JPG) to base64 for transport in text.

Usage:
  python tools/encode_image_base64.py screenshots/current_result.png > current_result.b64.txt
Optional env vars:
  OUTPUT_JPEG=1    -> Convert to JPEG (quality 70) before encoding to shrink size.
  JPEG_QUALITY=85  -> Override quality.
"""
import sys, os, base64
from io import BytesIO
from PIL import Image

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/encode_image_base64.py <image_path>")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(2)

    im = Image.open(path)
    buf = BytesIO()
    if os.environ.get('OUTPUT_JPEG') == '1':
        quality = int(os.environ.get('JPEG_QUALITY', '70'))
        im.convert('RGB').save(buf, format='JPEG', quality=quality, optimize=True)
        ext = 'jpeg'
    else:
        im.save(buf, format=im.format or 'PNG')
        ext = (im.format or 'PNG').lower()

    b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    print(f"BEGIN_BASE64:{ext}")
    # Wrap lines to 120 chars for readability
    for i in range(0, len(b64), 120):
        print(b64[i:i+120])
    print("END_BASE64")

if __name__ == '__main__':
    main()
