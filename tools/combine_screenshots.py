#!/usr/bin/env python3
"""
Simple helper to combine two screenshots side-by-side.
Usage:
  python tools/combine_screenshots.py current.png target.png out.png

Installs: requires Pillow (`pip install pillow`) in your virtualenv.
"""
import sys
from PIL import Image


def scale_to_height(im, target_h):
    w = int(im.width * (target_h / im.height))
    return im.resize((w, target_h), Image.LANCZOS)


def combine(a_path, b_path, out_path, spacing=12, bg=(255,255,255)):
    a = Image.open(a_path).convert('RGBA')
    b = Image.open(b_path).convert('RGBA')
    target_h = max(a.height, b.height)
    a2 = scale_to_height(a, target_h)
    b2 = scale_to_height(b, target_h)
    total_w = a2.width + b2.width + spacing
    out = Image.new('RGBA', (total_w, target_h), bg + (255,))
    out.paste(a2, (0,0), a2)
    out.paste(b2, (a2.width + spacing, 0), b2)
    # Save as PNG
    out.convert('RGB').save(out_path, 'PNG')
    print(f"Combined image saved to: {out_path}")


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python tools/combine_screenshots.py <current.png> <target.png> <out.png>')
        sys.exit(1)
    combine(sys.argv[1], sys.argv[2], sys.argv[3])
