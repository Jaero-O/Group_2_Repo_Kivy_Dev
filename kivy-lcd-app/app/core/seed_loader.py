import os
import csv
from typing import List, Dict

try:
    from .db import seed_lookups
except Exception:
    seed_lookups = None  # type: ignore

"""Seed loader for importing lookup tables (diseases, severity levels) from an external directory.

Expected CSV files (case-insensitive filename match):
  - diseases.csv   (columns: name, description, symptoms, prevention)
  - severity_levels.csv OR severity.csv (columns: name, description)

The loader ignores blank lines and trims whitespace. Missing optional columns default to empty strings.
Environment override:
  MANGOFY_SEED_PATH can specify a custom base directory.
"""

DISEASE_FILE_CANDIDATES = ["diseases.csv", "Diseases.csv", "DISEASES.csv"]
SEVERITY_FILE_CANDIDATES = ["severity_levels.csv", "severity.csv", "SeverityLevels.csv"]


def _read_csv(file_path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not os.path.exists(file_path):
        return rows
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            # Normalize keys -> lowercase
            normalized = {k.lower().strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            # Skip empty name rows
            if not normalized.get("name"):
                continue
            rows.append(normalized)
    return rows


def seed_from_path(base_path: str) -> Dict[str, int]:
    """Load CSV data from base_path and apply seeding via db.seed_lookups.

    Returns summary counts {"diseases": n, "severities": m}. If seeding backend unavailable returns zeros.
    """
    base_path = os.path.abspath(base_path)
    diseases: List[Dict[str, str]] = []
    severities: List[Dict[str, str]] = []

    for candidate in DISEASE_FILE_CANDIDATES:
        fp = os.path.join(base_path, candidate)
        if os.path.exists(fp):
            diseases = _read_csv(fp)
            break

    for candidate in SEVERITY_FILE_CANDIDATES:
        fp = os.path.join(base_path, candidate)
        if os.path.exists(fp):
            severities = _read_csv(fp)
            break

    if seed_lookups:
        # Map CSV dict keys to expected seed_lookups schema
        disease_rows = [
            {
                "name": d.get("name", ""),
                "description": d.get("description", ""),
                "symptoms": d.get("symptoms", ""),
                "prevention": d.get("prevention", ""),
            }
            for d in diseases
        ]
        severity_rows = [
            {
                "name": s.get("name", ""),
                "description": s.get("description", ""),
            }
            for s in severities
        ]
        seed_lookups(disease_rows, severity_rows)
    return {"diseases": len(diseases), "severities": len(severities)}


def seed_from_env() -> Dict[str, int]:
    path = os.getenv("MANGOFY_SEED_PATH", "")
    if not path:
        return {"diseases": 0, "severities": 0}
    return seed_from_path(path)


__all__ = ["seed_from_path", "seed_from_env"]
