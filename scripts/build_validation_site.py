#!/usr/bin/env python3
"""Build a static site for the expert validation sheet.

This copies the generated expert sheet to docs/index.html so it can be
published via GitHub Pages.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_HTML = PROJECT_ROOT / "data" / "exports" / "validation_sheet_EXPERT.html"
DOCS_DIR = PROJECT_ROOT / "docs"
TARGET_HTML = DOCS_DIR / "index.html"
NOJEKYLL = DOCS_DIR / ".nojekyll"


def main() -> int:
    if not SOURCE_HTML.exists():
        print(f"Missing source HTML: {SOURCE_HTML}")
        print("Run scripts/generate_validation_sheet.py first.")
        return 2

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_HTML.write_text(SOURCE_HTML.read_text(encoding="utf-8"), encoding="utf-8")
    NOJEKYLL.write_text("", encoding="utf-8")

    print(f"Built site: {TARGET_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
