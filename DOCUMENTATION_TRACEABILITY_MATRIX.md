# Documentation Traceability Matrix

**Purpose**: This document maps every USER_MANUAL.md requirement to the test(s) that validate it, enabling confident system modifications while maintaining compliance.

**Last Updated**: 2024-11-19

---

## USER_MANUAL.md Section 2.2: Scan Leaf Workflow

| Step | Requirement | Test(s) Validating |
|------|-------------|-------------------|
| **Step 1** | HomeScreen → 'scan_leaf' button → ScanScreen | `test_ui_flow_compliance.py::test_step1_home_to_scan_navigation` |
| **Step 2** | ScanScreen shows guidelines, 'Cancel' returns to Home | `test_ui_flow_compliance.py::test_step2_cancel_returns_to_home`<br>`test_ui_flow_compliance.py::test_step2_scan_screen_shows_guidelines` |
| **Step 3** | User selects image → ImageSelectionScreen → ScanningScreen | `test_ui_flow_compliance.py::test_step3_image_selection_navigates_to_scanning`<br>`test_scanning_flow.py::test_scanning_flow_navigates_and_sets_result`<br>`test_cancel_behavior.py::test_cancel_before_analysis_skips_navigation`<br>`simulate_flows.py::FLOW_7_cancellation` |
| **Step 4** | ScanningScreen performs analysis → navigates to ResultScreen (NOT CaptureResultScreen) | `test_ui_flow_compliance.py::test_step4_scanning_performs_analysis`<br>`test_scanning_flow.py::test_scanning_flow_navigates_and_sets_result`<br>`simulate_flows.py::FLOW_3_fresh_scan` |
| **Step 5** | ResultScreen displays disease_name, confidence, severity_name | `test_ui_flow_compliance.py::test_step5_result_screen_displays_analysis`<br>`test_integration.py::test_image_analysis` |
| **Step 6** | ResultScreen 'Save' button → SaveScreen | `test_ui_flow_compliance.py::test_step6_result_save_button_navigates_to_save_screen`<br>`simulate_flows.py::FLOW_3_fresh_scan` |
| **Step 7** | SaveScreen requires tree selection before saving | `test_ui_flow_compliance.py::test_step7_save_screen_tree_selection` |
| **Step 8** | SaveScreen 'Save' button persists record to database | `test_ui_flow_compliance.py::test_step8_save_button_persists_record`<br>`simulate_flows.py::FLOW_3_fresh_scan` |

---

## USER_MANUAL.md Section 2.3: View Saved Records Workflow

| Requirement | Test(s) Validating |
|-------------|-------------------|
| RecordsScreen loads trees from database | `test_ui_flow_compliance.py::test_records_screen_loads_trees` |
| Viewing saved record → ResultScreen with source_screen='records' | `simulate_flows.py::FLOW_2_view_saved_record` |
| Back navigation from saved record → RecordsScreen (not HomeScreen) | `simulate_flows.py::FLOW_2_view_saved_record`<br>`test_simulation_flows.py::test_simulation_core_flows` |

---

## USER_MANUAL.md Section 3.1: Mandatory Rules

| Rule | Requirement | Test(s) Validating |
|------|-------------|-------------------|
| **RULE 1** | No auto-save after scanning - user MUST explicitly click Save button | `test_ui_flow_compliance.py::test_rule1_no_auto_save_after_scanning`<br>`test_ui_flow_compliance.py::test_rule4_save_only_on_explicit_action`<br>`test_cancel_behavior.py::test_cancel_before_analysis_skips_navigation`<br>`simulate_flows.py::FLOW_7_cancellation` |
| **RULE 2** | Back/Cancel from unsaved result discards data - no persistence | `test_ui_flow_compliance.py::test_rule2_back_button_from_result_discards_unsaved`<br>`test_ui_flow_compliance.py::test_rule2_back_button_from_save_does_not_persist` |
| **RULE 3** | Screen navigation uses ScreenManager.current - analysis_result managed separately | `test_ui_flow_compliance.py::test_rule3_screen_manager_usage`<br>`test_scanning_flow.py::test_scanning_flow_navigates_and_sets_result`<br>`test_cancel_behavior.py::test_cancel_before_analysis_skips_navigation` |
| **RULE 4** | Save ONLY when user clicks Save button on SaveScreen | `test_ui_flow_compliance.py::test_rule4_save_only_on_explicit_action` |

---

## USER_MANUAL.md Section 3.3: Confidence & Severity Display

| Requirement | Test(s) Validating |
|-------------|-------------------|
| High confidence: ≥85% → Green checkmark | `test_ui_flow_compliance.py::test_high_confidence_display` |
| Moderate confidence: 60-84% → Yellow alert | `test_ui_flow_compliance.py::test_moderate_confidence_display` |
| Low confidence: <60% → Red warning | `test_ui_flow_compliance.py::test_low_confidence_display` |
| Healthy severity: 0.0-33.3 → Green "Early Detection" | `test_ui_flow_compliance.py::test_healthy_severity_range` |
| Early Stage severity: 33.4-66.6 → Yellow "Moderate Stage" | `test_ui_flow_compliance.py::test_early_stage_severity_range` |
| Advanced Stage severity: 66.7-100.0 → Red "Critical Stage" | `test_ui_flow_compliance.py::test_advanced_stage_severity_range` |

---

## USER_MANUAL.md Section 4: ML Pipeline Specifications

| Requirement | Test(s) Validating |
|-------------|-------------------|
| Section 4.1: ML predictor returns disease_name, confidence | `test_integration.py::test_image_analysis` |
| Section 4.2: disease_name required in ML output | `test_integration.py::test_image_analysis` |
| Section 4.3: Severity calculator computes severity_name from confidence | `test_integration.py::test_image_analysis` |

---

## USER_MANUAL.md Section 5.1: Performance Requirements

| Requirement | Test(s) Validating |
|-------------|-------------------|
| Analysis completes within 5 seconds on target hardware | `test_simulation_flows.py::test_simulation_stress_duration_reasonable` |

---

## Test Files Overview

### `tests/test_ui_flow_compliance.py` (22 tests)
**Purpose**: Comprehensive validation of all UI flows against USER_MANUAL.md  
**Coverage**:
- Scan Leaf Workflow (Steps 1-8): 9 tests
- Mandatory Rules 1-4: 5 tests  
- Confidence & Severity Display: 6 tests
- View Records Flow: 1 test
- Help/Info Flow: 1 test

**Status**: ✅ 22/22 passing (100%)

### `scripts/simulate_flows.py` + `tests/test_simulation_flows.py`
**Purpose**: Integration testing of all user workflows  
**Coverage**:
- FLOW 2: View saved record (Section 2.3)
- FLOW 3: Fresh scan workflow (Section 2.2 Steps 1-8)
- FLOW 7: Cancellation flow (Section 2.2 Step 3, RULE 1)
- Stress testing: Performance compliance (Section 5.1)

**Status**: ✅ 3/3 passing (1 skipped - mock limitation)

### `tests/test_scanning_flow.py`
**Purpose**: Validate ScanningScreen → ResultScreen navigation  
**Coverage**: Section 2.2 Step 4, RULE 3  
**Status**: ✅ 1/1 passing

### `tests/test_cancel_behavior.py`
**Purpose**: Validate cancel button behavior  
**Coverage**: Section 2.2 Step 3, RULE 1, RULE 3  
**Status**: ✅ 1/1 passing

### `tests/test_integration.py`
**Purpose**: Validate ML pipeline follows specifications  
**Coverage**: Section 4.1-4.3 (ML output structure)  
**Status**: ✅ 1/1 passing

---

## Total Test Coverage

- **Total Tests**: 28 (27 passing, 1 skipped)
- **Pass Rate**: 96.4% (27/28 excluding skipped)
- **Documentation Sections Validated**: 
  - Section 2.2: Scan Leaf Workflow ✅
  - Section 2.3: View Records Workflow ✅
  - Section 3.1: Mandatory Rules 1-4 ✅
  - Section 3.3: Confidence & Severity Display ✅
  - Section 4: ML Pipeline ✅
  - Section 5.1: Performance Requirements ✅

---

## How to Use This Matrix

### For Developers Making Changes:

1. **Before modifying UI flows**: Check which tests validate the screen you're changing
2. **After making changes**: Run the relevant test(s) to ensure compliance
3. **If test fails**: The assertion message will cite the specific USER_MANUAL.md section violated

### Example Workflow:

```bash
# Modifying ScanningScreen navigation logic
# 1. Check matrix: Section 2.2 Step 4 validated by test_scanning_flow.py

# 2. Make your changes to src/app/screens/scanning_screen.py

# 3. Run relevant tests
pytest tests/test_scanning_flow.py tests/test_ui_flow_compliance.py::test_step4_scanning_performs_analysis -v

# 4. If tests pass → change complies with USER_MANUAL.md ✅
# 5. If tests fail → assertion message shows which section violated
```

### For Updating Documentation:

If you modify `USER_MANUAL.md`:

1. **Identify affected sections** (e.g., changing Section 2.2 Step 5)
2. **Find tests validating that section** (use this matrix)
3. **Update tests** to match new documentation requirements
4. **Update this matrix** to reflect changes

---

## Verification Commands

```bash
# Run all UI flow compliance tests (22 tests)
pytest tests/test_ui_flow_compliance.py -v

# Run all simulation flows (3 tests)
pytest tests/test_simulation_flows.py -v

# Run all documentation-compliant tests (27 tests)
pytest tests/test_ui_flow_compliance.py tests/test_simulation_flows.py tests/test_scanning_flow.py tests/test_cancel_behavior.py tests/test_integration.py -v

# Run ONLY tests validating a specific section
# Example: Section 2.2 Step 4 (Scanning → Result navigation)
pytest tests/test_scanning_flow.py tests/test_ui_flow_compliance.py::test_step4_scanning_performs_analysis -v
```

---

## Compliance Enforcement

All tests now include explicit USER_MANUAL.md references:

- **Test docstrings**: State which manual sections the test validates
- **Assertion messages**: Cite specific sections when failures occur (e.g., "USER_MANUAL.md Section 2.2 Step 4: Must navigate to 'result'")
- **Flow comments**: simulate_flows.py comments link each flow to manual sections

This creates **bidirectional traceability**:
- **Manual → Tests**: Every requirement maps to test(s) validating it
- **Tests → Manual**: Every assertion states which requirement it validates

---

## Pre-Existing Failures (Not Documentation-Related)

The following tests have pre-existing failures unrelated to USER_MANUAL.md compliance:

- `test_main_app.py`: 6 failing tests (app lifecycle issues, not flow issues)

These failures do NOT indicate documentation violations and are tracked separately.

---

## Next Steps

To further enhance compliance enforcement:

1. **Add CI gate**: Require `test_ui_flow_compliance.py` to pass before merging PRs
2. **Documentation reviews**: When updating USER_MANUAL.md, mandate test updates
3. **Expand coverage**: Add tests for remaining sections (hardware specs, accessibility)
4. **Regression testing**: Run compliance suite on every commit

---

**For questions or to report compliance issues, see `DOCUMENTATION_COMPLIANCE_REPORT.md`**
