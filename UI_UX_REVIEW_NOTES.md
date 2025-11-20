# UI / UX Review Notes (Scanning & Capture Flow)

## Current Flow Summary
1. User selects or captures image (single or multi-frame stitched).
2. App sets `analysis_image_path` and navigates to `scanning` screen.
3. `ScanningScreen` performs optional preprocessing (exposure normalization, resize) then model inference and severity calculation in a background thread.
4. Dynamic staged progress updates (Preparing → Pre-processing → Loading model → Analyzing disease → Computing severity → Finalizing → Done) shown via label + progress bar.
5. Navigation to `capture_result` with LCD-sized or processed image preview.

## Positive Improvements
- Deterministic navigation & analysis result attachment validated by tests.
- Multi-frame stitching increases context for disease detection.
- Preprocessing pipeline (exposure normalization + LCD resize) improves visual consistency and downstream model readiness.
- Dynamic progress stages provide clearer feedback than a static bar.
- Placeholder image fallback prevents hard failures on absent camera hardware, maintaining user flow.
- Expanded test suite (smoke, performance, stress, pipeline) reduces regression risk.

## Observed UX Issues / Gaps
1. Preview Continuity: User cannot see an immediate transitional thumbnail on `ScanningScreen`; only textual progress appears. (No miniature of the captured frame.)
2. Progress Granularity: Stage jumps are coarse and not tied to measured durations; may appear artificial if analysis is fast (bar races to 100%).
3. Cancellation: No option to abort scanning if user realizes the capture is incorrect (e.g., wrong leaf, blurred image). Requires full cycle + back navigation.
4. Error Transparency: Failures in preprocessing or analysis silently revert to default "Healthy" result; user receives no indication an error occurred.
5. Accessibility: Progress bar and label rely on color + small text; need validation for contrast and size (already partial contrast test, but not dynamic UI sizing).
6. Result Transition: Navigation to result screen is immediate after final stage; lacks subtle delay or animation to confirm completion (could feel abrupt).
7. Multi-frame Capture Feedback: During multi-frame stitching capture, user doesn't see per-frame acquisition status (progress only appears after navigation to scanning).
8. Performance Perception: On fast systems, progress stages may flash too quickly; on slow systems, model load might stall without sub-stage feedback.
9. Fallback Disclosure: When placeholder is used, user is not explicitly informed that a non-real capture was analyzed.
10. Severity Context: Severity percentages shown without explanatory scale or guidance (e.g., what thresholds trigger particular treatment actions).

## Recommended Improvements (Prioritized)
1. Add Cancel/Back button on `ScanningScreen` to abort analysis (soft kill flag + navigation to capture).  
2. Display a small static preview thumbnail of the target image beside the progress indicator for continuity.  
3. Implement error state messaging: if analysis falls back to default result due to internal exception, show a warning icon/text ("Analysis fallback: using default healthy result").  
4. Tie progress values to actual timing or sub-operation durations (e.g., measure preprocessing, model load, inference time; interpolate smoothly).  
5. Add optional micro-stages: e.g., "Allocating model", "Preparing tensors", "Inferring", "Post-processing" for slower runs.  
6. Expose a per-frame count indicator during multi-frame capture (e.g., overlay 'Frame 2/4 captured').  
7. Provide explicit placeholder notice: if image source path contains 'placeholder', show a subtle banner ("Camera unavailable – using sample image").  
8. Add slight fade or transition when moving from scanning to result screen to reduce abruptness.  
9. Expand accessibility: increase font size, ensure progress bar color contrast, and add optional auditory cue (if platform permits) when analysis completes.  
10. Add severity scale legend (Healthy / Mild / Moderate / Severe) with percentage ranges on `capture_result` screen.  

## Quick Wins (Low Effort / High Impact)
- Cancel button + flag check in background thread.  
- Thumbnail display on scanning screen using the existing `analysis_image_path`.  
- Placeholder usage banner (string match + Label).  
- Severity scale legend (static widget addition).  
- Fallback error indicator (set flag when exception captured).  

## Medium Effort
- Timing-based progress interpolation (requires measurement + smoothing).  
- Multi-frame acquisition feedback (needs capture thread UI callbacks).  
- Animated transition (KV + Animation).  

## Longer Term / Advanced
- Real-time inference progress (model instrumentation).  
- User-configurable verbosity level (compact vs detailed stages).  
- Retry capture option on result screen (returns to capture retaining prior settings).  
- Localization support for progress messages.  

## Dependencies & Considerations
- Cancel needs thread-safe flag; inference must periodically check for cancellation (or rely on short inference time).  
- Error transparency requires distinguishing between model absence and inference failure.  
- Multi-frame feedback may require restructuring capture to iterate + yield frames to UI.  
- Accessibility enhancements should reference WCAG contrast ratios already partially covered by existing test.  

## Proposed Next Implementation Sequence
1. Add cancel mechanism + button (flag + early navigation).  
2. Add thumbnail & placeholder banner.  
3. Add severity legend.  
4. Implement fallback error indicator messaging.  
5. Instrument timing of preprocessing / inference and map to progress interpolation.  

## Test Additions Suggested
- Cancel behavior test (sets flag; ensures navigation back to capture, no result modification).  
- Placeholder banner visibility test (mock placeholder path).  
- Fallback error indicator test (force analyze_image exception).  
- Severity legend presence test (UI element text).  
- Progress interpolation test (assert monotonic increments and final value 100).  

## Risks
- Overcomplicating progress may add perceived latency if artificial delays introduced.  
- Cancellation mid-inference could leave partially updated app state; ensure cleanup.  
- Additional UI elements risk clutter; maintain visual hierarchy.  

## Summary
Dynamic progress improves clarity, but user agency (cancel), transparency (error & placeholder notices), and continuity (thumbnail, multi-frame feedback) remain areas for enhancement. Prioritizing cancel, thumbnail, and severity context yields immediate UX improvements with modest engineering overhead.
