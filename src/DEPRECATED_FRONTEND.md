# Deprecated Frontend Directory (READY FOR REMOVAL)

The `src/app` directory previously contained an alternate/earlier version of the Kivy frontend.
This has been superseded by the canonical implementation located at:

```
kivy-lcd-app/app/
```

All new screen controllers, KV layouts, assets, and core logic must live under `kivy-lcd-app/app/`.

Migration Actions Completed:
- Verified `src/app/core` and `src/app/utils` contained no active code beyond `__pycache__`.
- Updated `README.md` to reflect the canonical structure.
- Added centralized severity thresholds (`ml/processing/severity_constants.py`).

Final Removal Instructions:
Search confirmation already performed (no matches for `src.app` or `src/app`). Directory contains only `__pycache__` folders.

Delete commands (PowerShell):
```
Remove-Item -Recurse -Force .\src\app
```

Post-removal checklist:
- Run: `python kivy-lcd-app\main.py` (ensure app launches)
- Git: commit the deletion with message `chore: remove deprecated static frontend`
- Update any internal documentation pointing to `src/app` (none remaining as of Nov 2025)

If you prefer archival instead of deletion, rename instead:
```
Rename-Item .\src\app legacy_frontend_2025-11
```
and add to `.gitignore` if not needed.

---
Created: stabilization cleanup (November 2025)
Updated: final removal ready (November 21 2025)
