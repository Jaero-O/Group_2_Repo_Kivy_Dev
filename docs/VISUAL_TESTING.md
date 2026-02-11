# Visual UI Regression & Masking Workflow

This document summarizes the tooling implemented to compare runtime Kivy screens against Figma design references while accounting for dynamic regions (records lists, analysis result panels, etc.).

## Reference Screens
- Canonical design images live in `screenshots/references/<screen>.png`.
- `result.png` promoted from a dynamic capture when a Figma asset was unavailable.
- Adoption script `tools/adopt_figma_references.py` standardizes naming.

## Capturing Current Screens
Two modes:
- Static capture: run app with env `AUTO_CAPTURE_ALL_SCREENS=1` (outputs to `screenshots/current`).
- Dynamic capture: `python tools/capture_current_dynamic.py --out screenshots/current_alt` populates a tree, record, and selects an analysis image before triggering multi-screen capture to `screenshots/current_alt`.

Environment flags used by capture sequence in `main.py`:
```
AUTO_CAPTURE_ALL_SCREENS=1
ALL_SCREENS_OUTPUT_DIR=<target dir>
EXIT_AFTER_CAPTURE=1
```

## Mask Configuration
Dynamic regions (scrolling lists, changing analysis output) inflate pixel diffs. A JSON mask file defines rectangles to ignore:
`screenshots/mask_config.json`
```json
{
  "welcome": [{"x":0, "y":600, "w":480, "h":200}],
  "scan": [{"x":0, "y":400, "w":480, "h":300}],
  "scanning": [{"x":0, "y":300, "w":480, "h":350}],
  "result": [{"x":0, "y":350, "w":480, "h":450}],
  "records": [{"x":0, "y":180, "w":480, "h":620}],
  "image_selection": [{"x":0, "y":250, "w":480, "h":550}]
}
```
Each rectangle is excluded from differing pixel counts and mean absolute diff calculations.

## Visual Regression Tool
`tools/visual_regression.py` features:
- Groups multiple captured variants per screen, choosing the best match (lowest percent diff).
- Applies masks (`--mask-config`) and generates overlay images (`--diff-dir`).
- Optional SSIM metric (`--enable-ssim`) for perceptual similarity.
- Outputs JSON summary with masked vs effective pixel counts.

Example run:
```
python tools/visual_regression.py \
  --current-dir screenshots/current_alt \
  --reference-dir screenshots/references \
  --mask-config screenshots/mask_config.json \
  --diff-dir screenshots/diff_overlays_alt \
  --enable-ssim \
  --ignore-screens loading \
  --threshold 0.25 \
  --output screenshots/references/visual_metrics_masked_alt.json
```

## Diff Overlays
Generated per screen in the specified diff directory:
- Red pixels: differing (unmasked).
- Dimmed pixels: masked areas (ignored for metrics).
Use these overlays to visually inspect concentrated divergence (layout shifts, color palette differences).

## Heatmaps
Enable with `--heatmap-dir` to produce `<screen>_heatmap.png` images:
- Color gradient encodes magnitude of RGB difference (blue→cyan→yellow→red).
- Masked regions appear dark.
Helps pinpoint intensity of divergence beyond binary differing pixels.

## Artifact Bundling
Use `tools/bundle_visual_artifacts.py` to package regression outputs:
```
python tools/bundle_visual_artifacts.py \
  --metrics screenshots/references/visual_metrics_masked_alt.json \
  --diff-dir screenshots/diff_overlays_alt \
  --heatmap-dir screenshots/heatmaps_alt \
  --references-dir screenshots/references \
  --current-dir screenshots/current_alt \
  --output artifacts/visual_regression_bundle.zip
```
Integrate into CI post-test step to archive for inspection.

## Interpreting Metrics
- `percent_diff`: fraction of differing unmasked pixels; high values (>0.9) indicate major layout/color divergence.
- `mean_abs_diff_per_channel`: average absolute RGB difference; helps isolate palette differences even when masked regions shrink effective pixel set.
- `masked_pixel_count` vs `effective_pixel_count`: ensures comparisons remain fair when large dynamic areas are excluded.
- `ssim`: perceptual structural similarity (closer to 1.0 means more similar). Useful when raw pixel diffs are inflated by anti-aliasing or subtle font rendering differences.

## Incremental UI Alignment Strategy
1. Prioritize high-visibility flow screens: `welcome`, `scanning`, `result`.
2. Update KV styling (fonts, colors) and component spacing to move diff overlays from full-screen red blocks toward localized discrepancies.
3. Re-run dynamic capture + regression after each batch of changes.
4. Tune masks only for truly dynamic content; avoid masking static layout issues.

## Adding / Adjusting Masks
Keep mask regions minimal:
- Prefer multiple smaller rectangles over one large catch-all.
- Re-run regression and confirm percent diff decreases where expected.
- Document rationale inline in the JSON using comments (temporarily) if needed; remove comments before CI usage (JSON does not support comments).

## Troubleshooting
- Placeholder `result.png` replaced by promoting a runtime capture; ensure eventual Figma design parity.
- If CLI args are consumed by Kivy, set `KIVY_NO_ARGS=1` before importing Kivy (already handled in dynamic capture script).
- Repeated screen names during capture indicate multiple instantiations; confirm screen registration logic in `main.py` does not duplicate widgets when rebuilding.

## Future Enhancements
- Add perceptual diff (SSIM) for more robust similarity scoring.
- Optional tolerance map (heatmap) summarizing diff density per quadrant.
- CI integration with threshold gates and artifact upload of failing overlays.
  (SSIM added; heatmap + artifact upload remain pending.)

---
Last updated: 2025-11-19# Visual UI Testing

This document describes the workflow for capturing and comparing Kivy screen renders against reference images.

## 1. Capture All Screens
Set environment variables before launching `main.py`:

```
$env:AUTO_CAPTURE_ALL_SCREENS='1'
$env:ALL_SCREENS_OUTPUT_DIR='screenshots/current'
$env:EXIT_AFTER_CAPTURE='1'
python main.py
```

The app will iterate each registered screen, save `<screen_name>.png` into `screenshots/current`, then exit.

## 2. Provide Reference Images
Place reference PNGs into `screenshots/references` using the naming convention:

```
welcome.png
result.png
scan.png
records.png
... etc
```
Spaces should be replaced with underscores and lowercased (the comparison script applies this rule to current captures).

## 3. Run Batch Visual Comparison
Execute:

```
python tools/visual_regression.py --current-dir screenshots/current --reference-dir screenshots/references --output visual_metrics.json --threshold 0.25
```

Output example:
```
{
  "threshold": 0.25,
  "total_screens": 10,
  "processed": 8,
  "missing_references": ["guide","about_us"],
  "metrics": [ ... per-screen diff metrics ... ],
  "failures": ["result"]
}
```

Key metrics:
- `percent_diff`: Fraction (0–1) of pixels differing in RGBA channels.
- `mean_abs_diff_per_channel`: Average absolute difference per color channel.
- `status`: `pass` if `percent_diff <= threshold` else `fail`.

Adjust `--threshold` or env var `VIS_REG_THRESHOLD` to tune sensitivity.

## 4. Visual Regression Test (Optional)
Guarded unit test file: `tests/test_visual_regression.py`.
Enable during local runs or CI with:
```
$env:RUN_VISUAL_TESTS='1'
python -m unittest tests.test_visual_regression
```
If references for `welcome` and `result` are missing, the test auto-skips.

Set stricter threshold via:
```
$env:VIS_TEST_THRESHOLD='0.20'
```

## 5. Updating References
After intentional UI changes:
1. Capture fresh current screenshots.
2. Manually review differences.
3. Replace affected reference PNGs with new approved versions.
4. Re-run regression to confirm all `status` values are `pass`.

## 6. Troubleshooting
- Large `percent_diff` often indicates size mismatch; ensure consistent window size (use existing window setup defaults).
- Dynamic content (timestamps, randomized data) will inflate diffs—mask or standardize inputs before capture.
- Missing references appear under `missing_references`; create those PNGs or remove from evaluation scope.

## 7. Extending
Potential enhancements:
- Add structural layout metrics (widget bounding boxes) to reduce pixel noise sensitivity.
- Implement region-based diff (e.g., isolate content card and ignore background).
- Include tolerance masks for dynamic text areas.

## 8. Non-Destructive Design
The capture logic is isolated behind env vars (`AUTO_CAPTURE_ALL_SCREENS`). Normal app execution is unaffected unless the flag is set, preserving system integrity.

---
Maintainer: Visual testing utilities added November 2025.
