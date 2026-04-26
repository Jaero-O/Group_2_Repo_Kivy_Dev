# AI ASSISTANT INSTRUCTIONS
## Mandatory Guidelines for AI Systems Working on MangoFy

**Document Type:** System Directive  
**Authority Level:** CRITICAL  
**Compliance:** MANDATORY  
**Date:** November 19, 2025

---

## ⚠️ CRITICAL DIRECTIVE FOR ALL AI ASSISTANTS ⚠️

**IF YOU ARE AN AI ASSISTANT (like GitHub Copilot, ChatGPT, Claude, etc.), YOU MUST READ AND FOLLOW THESE INSTRUCTIONS BEFORE PERFORMING ANY ACTION IN THIS REPOSITORY.**

---

## 1. PRIMARY DIRECTIVE

**BEFORE doing ANYTHING in this codebase:**

### Step 1: Read Documentation in This Order
1. ✅ **README.md** - Start here ALWAYS
2. ✅ **DOCUMENTATION_INDEX.md** - Understand documentation structure
3. ✅ **docs/SYSTEM_REQUIREMENTS.md** - Learn what the system should do
4. ✅ **docs/USER_MANUAL.md** - Learn how the system should behave
5. ✅ **COMPREHENSIVE_ASSESSMENT_REPORT.md** - Understand current state
6. ✅ **IMPLEMENTATION_COMPLETION_SUMMARY.md** - Understand recent changes

### Step 2: Understand Constraints
- All specifications are **DEFINITIVE**
- All UI flows are **MANDATORY**
- All navigation patterns are **FIXED**
- Test coverage must stay **≥90%**
- No changes without documentation compliance

### Step 3: Verify Understanding
Before making changes, ask yourself:
- Have I read the relevant documentation sections?
- Do I understand the intended behavior?
- Will my changes comply with documented specifications?
- Do I need to update documentation?

---

## 2. ABSOLUTE PROHIBITIONS

**YOU MUST NEVER:**

### ❌ Navigation Changes
- Change screen transitions without docs/USER_MANUAL.md approval
- Create alternative navigation paths
- Skip documented validation steps
- Modify back button behaviors

### ❌ Workflow Modifications
- Auto-save scans (user must explicitly choose "Save")
- Skip confirmation dialogs
- Bypass error handling
- Change state management patterns

### ❌ Database Changes
- Modify schema without DATABASE_DOCUMENTATION_PLAN.md update
- Remove foreign key constraints
- Change index definitions
- Bypass validation rules

### ❌ ML Pipeline Changes
- Modify preprocessing steps without authorization
- Change model input/output formats
- Skip normalization steps
- Alter severity calculation algorithms

### ❌ Documentation Violations
- Make changes without reading relevant docs
- Assume behavior not explicitly documented
- Implement features differently than specified
- Skip documentation updates

---

## 3. REQUIRED BEHAVIORS

**YOU MUST ALWAYS:**

### ✅ Reference Documentation
```python
# GOOD: References documentation
# Per docs/USER_MANUAL.md Section 2.2 Step 6:
# Save button must explicitly save record, not auto-save
def on_save_button(self):
    self.save_record()
    self.navigate_to_confirmation()

# BAD: No documentation reference
def on_analysis_complete(self):
    self.save_record()  # Auto-save - WRONG!
```

### ✅ Follow Patterns
- Use existing code patterns
- Match naming conventions
- Follow architecture layers
- Respect separation of concerns

### ✅ Maintain Quality
- Keep test coverage ≥90%
- Add tests for new features
- Fix broken tests before committing
- Ensure no deprecation warnings

### ✅ Update Documentation
- If changing UI → Update docs/USER_MANUAL.md
- If changing features → Update docs/SYSTEM_REQUIREMENTS.md
- If changing database → Update DATABASE_DOCUMENTATION_PLAN.md
- If changing behavior → Update README.md

---

## 4. CODE GENERATION RULES

### Rule 1: Always Check Existing Implementation
**BEFORE generating code:**
```python
# Step 1: Search for existing implementations
grep -r "similar_function" src/

# Step 2: Read existing code
read_file("src/app/screens/existing_screen.py")

# Step 3: Match patterns
# Use same structure, naming, error handling
```

### Rule 2: Reference Documentation in Comments
```python
# Per docs/USER_MANUAL.md Section 2.2 Step 4 (Result Screen):
# Confidence score display rules:
# - ≥85%: Green badge, "High Confidence"
# - 60-84%: Yellow badge, "Moderate Confidence"  
# - <60%: Red badge with warning
def get_confidence_badge_color(confidence):
    if confidence >= 0.85:
        return COLORS['success']
    elif confidence >= 0.60:
        return COLORS['warning']
    else:
        return COLORS['error']
```

### Rule 3: Follow Mandatory Patterns
```python
# MANDATORY PATTERN: Screen Navigation
# From docs/USER_MANUAL.md Section 3.1 Rule 3
class MyScreen(Screen):
    def navigate_to_next(self):
        # Use ScreenManager, not direct instantiation
        self.manager.current = 'next_screen_name'
        
    def go_back(self):
        # Follow documented back behavior
        self.manager.current = 'parent_screen_name'
```

### Rule 4: Include Error Handling
```python
# MANDATORY: User-visible errors + structured logging
# From docs/USER_MANUAL.md Section 3.2 Rule 8
try:
    result = analyze_image(image_path)
except ModelNotFoundError as e:
    logger.error(f"Model not found: {e}", exc_info=True)
    self.show_error("⚠ ML model unavailable. Using basic detection.")
except Exception as e:
    logger.error(f"Analysis failed: {e}", exc_info=True)
    self.show_error("⚠ Analysis encountered an error. Please try again.")
```

---

## 5. TESTING REQUIREMENTS

**BEFORE suggesting code, verify:**

### Test Existence
```python
# For every new function, ask:
# - Does a test exist?
# - Should I create a test?
# - Will my change break existing tests?

# GOOD: Test-aware code suggestion
def calculate_severity(image_path):
    """Calculate severity percentage from leaf image.
    
    See tests/test_severity_calculator.py for test cases.
    Expected behavior documented in docs/SCANNING_CODE.pdf.
    """
    # Implementation...
```

### Test Coverage
```python
# After generating code, remind user to test:
# "Run tests to verify this change:"
# pytest tests/test_module.py -v
```

### Test Pass Rate
```python
# Current pass rate: 98.7% (78/79 tests)
# Your changes must maintain ≥90% pass rate
# Run full suite before committing:
# pytest tests/ -k "not visual" --tb=line -q
```

---

## 6. DOCUMENTATION AWARENESS

### When Suggesting UI Changes
**YOU MUST:**
1. Read `docs/USER_MANUAL.md` relevant sections
2. Quote specific section numbers
3. Verify compliance with documented flow
4. Note if documentation needs updating

**Example:**
```
I've reviewed docs/USER_MANUAL.md Section 2.2 (Scan Leaf Flow).
The documented behavior for ResultScreen is:
- Retake → Return to ScanScreen (discard result)
- View Info → Navigate to detailed view
- Save → Navigate to SaveScreen

Your request to add "Auto-Save" would violate Rule 1 
(No Auto-Save) from Section 3.1. 

Recommendation: Keep explicit Save button per documentation.
```

### When Suggesting Feature Changes
**YOU MUST:**
1. Check if feature exists in `docs/SYSTEM_REQUIREMENTS.md`
2. Verify it doesn't conflict with existing requirements
3. Note which FR/NFR numbers are affected
4. Suggest documentation updates

---

## 7. COMMON SCENARIOS

### Scenario 1: User Asks to Change Navigation
**User:** "Make the back button go directly to home from all screens"

**CORRECT RESPONSE:**
```
I've checked docs/USER_MANUAL.md Section 3.1 Rule 2 
(Back Button Behavior). The documented back button rules 
specify different behaviors for each screen:

- ResultScreen: Back → ScanScreen
- SaveScreen: Back → ResultScreen  
- RecordsScreen: Back → HomeScreen
- DetailView: Back → RecordsScreen

Changing all back buttons to go to HomeScreen would violate 
the documented navigation flow. 

Would you like me to:
1. Keep current behavior (recommended - follows documentation)
2. Update docs/USER_MANUAL.md first, then implement change
3. Discuss alternative approaches
```

### Scenario 2: User Asks to Add Auto-Save
**User:** "Automatically save scans after analysis"

**CORRECT RESPONSE:**
```
I've reviewed docs/USER_MANUAL.md Section 3.1 Rule 1 
(No Auto-Save) and Section 2.2 Step 6 (Save Screen).

The documentation explicitly states:
"Scanning should NOT persist records automatically. 
Persist only when the user chooses 'Save' in the Save flow."

This is a MANDATORY rule. Auto-saving would:
- Violate documented user workflow
- Remove user control over data persistence
- Conflict with the Save/Cancel pattern

To implement auto-save, you would need to:
1. Get stakeholder approval
2. Update docs/USER_MANUAL.md
3. Update docs/SYSTEM_REQUIREMENTS.md FR-005
4. Review impact on existing tests

Recommendation: Keep current explicit save workflow.
```

### Scenario 3: User Asks About Database Schema
**User:** "How do I add a new field to scan records?"

**CORRECT RESPONSE:**
```
I've checked DATABASE_DOCUMENTATION_PLAN.md and 
docs/SYSTEM_REQUIREMENTS.md Section 5.1.

Current tbl_scan_record schema is documented with:
- record_id (PK)
- tree_id (FK to tbl_tree)
- disease_id (FK to tbl_disease)
- image_path
- confidence
- severity
- scan_timestamp
- notes

To add a new field, you must:
1. Update DATABASE_DOCUMENTATION_PLAN.md with new field
2. Update docs/SYSTEM_REQUIREMENTS.md Section 5.1 table
3. Create migration script in scripts/
4. Update src/app/core/database.py:
   - Modify CREATE TABLE statement
   - Add migration check in _create_indexes()
5. Update tests/test_database.py
6. Update any affected screens

Would you like me to generate the migration script template?
```

---

## 8. ERROR DETECTION

**YOU SHOULD FLAG when you see:**

### 🚨 Documentation Violations
```python
# VIOLATION: Auto-save after analysis
# This violates docs/USER_MANUAL.md Section 3.1 Rule 1
def on_analysis_complete(self, result):
    self.db.save_record(result)  # ❌ NO!
    self.show_result(result)
    
# CORRECT: Only save when user explicitly chooses
def on_save_button(self):
    self.db.save_record(self.current_result)  # ✅ YES
```

### 🚨 Navigation Pattern Breaks
```python
# VIOLATION: Direct screen instantiation
# Violates docs/USER_MANUAL.md Section 3.1 Rule 3
def navigate_to_result(self):
    result_screen = ResultScreen()  # ❌ NO!
    
# CORRECT: Use ScreenManager
def navigate_to_result(self):
    self.manager.current = 'result_screen'  # ✅ YES
```

### 🚨 Missing Error Handling
```python
# VIOLATION: Silent failures
# Violates docs/USER_MANUAL.md Section 3.2 Rule 8
def analyze_image(self, path):
    return model.predict(path)  # ❌ NO! No error handling
    
# CORRECT: User-visible errors + logging
def analyze_image(self, path):
    try:
        return model.predict(path)
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        self.show_error("⚠ Analysis encountered an error")
        return default_result()  # ✅ YES
```

---

## 9. RESPONSE TEMPLATES

### When User Request Violates Documentation
```
⚠️ DOCUMENTATION VIOLATION DETECTED

Your request to [describe request] would violate:
- Document: [document name]
- Section: [section number]
- Rule: [rule description]

Current documented behavior:
[Quote relevant section]

Your proposed change:
[Describe change]

Conflict:
[Explain conflict]

Recommendations:
1. [Option 1 - follow docs]
2. [Option 2 - update docs first]
3. [Option 3 - alternative approach]

Would you like me to proceed with option [X]?
```

### When Suggesting Code Changes
```
Based on [document name] Section [X]:

[Quote relevant specification]

Here's the compliant implementation:

[code block with documentation references in comments]

This implementation:
✅ Follows documented navigation (docs/USER_MANUAL.md Section X)
✅ Includes error handling (docs/USER_MANUAL.md Section 3.2)
✅ Maintains state correctly (docs/USER_MANUAL.md Section 3.1 Rule 3)
✅ Logs structured errors (docs/USER_MANUAL.md Section 3.2 Rule 8)

Would you like me to also:
- [ ] Generate corresponding tests?
- [ ] Update documentation?
- [ ] Review related code?
```

---

## 10. SELF-CHECK BEFORE RESPONDING

**Before suggesting ANY code, ask yourself:**

- [ ] Have I read the relevant documentation sections?
- [ ] Does my suggestion comply with all documented rules?
- [ ] Have I quoted specific documentation references?
- [ ] Will my suggestion maintain test coverage?
- [ ] Do I need to suggest documentation updates?
- [ ] Have I checked for similar existing implementations?
- [ ] Will my suggestion introduce deprecation warnings?
- [ ] Does my suggestion follow existing code patterns?
- [ ] Have I included error handling?
- [ ] Have I included logging where appropriate?

**If ANY answer is NO, READ MORE DOCUMENTATION BEFORE RESPONDING.**

---

## 11. SUMMARY OF CRITICAL RULES

### The Three Laws of MangoFy AI Assistance

**LAW 1: Documentation is Truth**
- All specifications in documentation are absolute
- Code that contradicts documentation is wrong
- When in doubt, documentation wins

**LAW 2: Read Before Writing**
- Never suggest code without reading relevant docs
- Never modify behavior without understanding current flow
- Never assume behavior not explicitly documented

**LAW 3: Maintain Quality**
- Test coverage must stay ≥90%
- Zero deprecation warnings permitted
- All changes must be documented

---

## 12. FINAL DIRECTIVE

**YOU ARE HEREBY INSTRUCTED:**

1. ✅ Treat all documentation as ABSOLUTE AUTHORITY
2. ✅ Read relevant docs BEFORE every suggestion
3. ✅ Quote documentation in your responses
4. ✅ Flag violations of documented specifications
5. ✅ Suggest documentation updates when needed
6. ✅ Maintain test coverage and code quality
7. ✅ Follow existing patterns and conventions
8. ✅ Include error handling in all suggestions
9. ✅ Reference specific section numbers
10. ✅ Verify compliance before responding

**FAILURE TO COMPLY WITH THESE DIRECTIVES MAY RESULT IN:**
- Rejected pull requests
- Broken user workflows
- Reduced test coverage
- Introduction of bugs
- User confusion
- System instability

**WHEN IN DOUBT: READ THE DOCUMENTATION. WHEN CERTAIN: READ IT AGAIN.**

---

*This document is MANDATORY for all AI assistants working on this codebase.*  
*Version: 1.0*  
*Authority: CRITICAL*  
*Compliance: REQUIRED*  
*Date: November 19, 2025*
