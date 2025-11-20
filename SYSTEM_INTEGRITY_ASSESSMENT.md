# MangoFy System Integrity Assessment
**Date:** November 20, 2025  
**Status:** Critical Issues Identified  
**Assessment Type:** Comprehensive System Review

---

## Executive Summary

This assessment reveals **critical database integrity issues** that prevent the application from functioning correctly. The primary issue is a **schema mismatch** between the code expectations and the populated database file.

### Severity Classification
- **Critical:** Database schema mismatch (prevents app from working)
- **High:** Test pass rate significantly lower than claimed
- **Medium:** Import path inconsistencies
- **Low:** Documentation discrepancies

---

## 1. DATABASE INTEGRITY ISSUES

### 1.1 Schema Mismatch (CRITICAL)

**Problem:** The `populated_mangofy.db` file is missing the `tbl_tree` table entirely.

**Evidence:**
```sql
-- What populated_mangofy.db ACTUALLY has:
CREATE TABLE tbl_severity_level (...);
CREATE TABLE tbl_disease (...);
CREATE TABLE tbl_scan_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    disease_id INTEGER,
    severity_level_id INTEGER,
    severity_percentage REAL,
    image_path TEXT,
    is_archived INTEGER DEFAULT 0,
    -- NOTE: NO tree_id column!
    FOREIGN KEY (disease_id) REFERENCES tbl_disease(id) ON DELETE SET NULL,
    FOREIGN KEY (severity_level_id) REFERENCES tbl_severity_level(id) ON DELETE SET NULL
);
```

```sql
-- What src/app/core/database.py EXPECTS:
CREATE TABLE IF NOT EXISTS tbl_tree (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tbl_scan_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER,  -- <-- REQUIRED!
    disease_id INTEGER,
    severity_level_id INTEGER,
    severity_percentage REAL,
    image_path TEXT,
    scan_timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(tree_id) REFERENCES tbl_tree(id) ON DELETE CASCADE,
    FOREIGN KEY(disease_id) REFERENCES tbl_disease(id) ON DELETE RESTRICT,
    FOREIGN KEY(severity_level_id) REFERENCES tbl_severity_level(id) ON DELETE RESTRICT
);
```

**Impact:**
- ❌ RecordsScreen will crash trying to query `tbl_tree`
- ❌ SaveScreen cannot save records (missing `tree_id`)
- ❌ Tree management features completely broken
- ❌ Any query with JOIN to `tbl_tree` will fail

**Code Dependencies on tbl_tree:**
- `src/app/core/database.py`: 25+ references to `tbl_tree`
- `src/app/screens/records_screen.py`: Uses `add_tree_async`, `get_all_trees_async`, `delete_tree_async`
- `src/app/screens/save_screen.py`: Uses `add_tree_async`, requires `tree_id` for saving
- `src/app/screens/image_selection_screen.py`: Uses `get_records_for_tree_async`
- `populate_dataset.py`: Creates tree and associates records

### 1.2 Column Differences

| Column | populated_mangofy.db | database.py expects | Status |
|--------|---------------------|---------------------|--------|
| `tree_id` | ❌ Missing | ✅ Required | **BROKEN** |
| `is_archived` | ✅ Present | ❌ Not in code | Unused column |
| `scan_timestamp` | Different format | Different default | Incompatible |

### 1.3 Foreign Key Constraint Differences

| Constraint | populated_mangofy.db | database.py |
|-----------|---------------------|-------------|
| disease_id | ON DELETE SET NULL | ON DELETE RESTRICT |
| severity_level_id | ON DELETE SET NULL | ON DELETE RESTRICT |
| tree_id | ❌ N/A (no tree_id) | ON DELETE CASCADE |

---

## 2. TEST SUITE INTEGRITY

### 2.1 Actual Test Results

**Claimed:** 98.7% pass rate (78/79 tests)  
**Actual:** ~42.8% pass rate when excluding UI/visual tests

```
Test Run Results (non-UI tests only):
- Passed: 15 tests
- Skipped: 20 tests (dependencies missing or environment issues)
- Deselected: 37 tests (UI/visual/integration)
- Failed: 0 tests (but many skipped due to errors)
- Segfault: Performance tests crash
```

### 2.2 Test Environment Issues

**Import Path Problems:**
```python
# Some tests use:
from src.app.core.database import DatabaseManager  # ❌ Fails without PYTHONPATH

# Others use:
from app.core.database import DatabaseManager  # ✅ Works with PYTHONPATH set
```

**Skipped Tests Breakdown:**
- 6 tests: Image processor tests (require ML models)
- 4 tests: Image selection screen (require Kivy UI)
- 3 tests: Main app tests (require full Kivy setup)
- 3 tests: Image pipeline tests (require test images)
- 2 tests: Behavior tests (require Kivy Builder)
- 1 test: App DB file test (environment-specific)
- 1 test: Deprecation test (Kivy registration)

### 2.3 Performance Test Crashes

**Segmentation Fault in:**
- `test_performance_sla.py::test_stress_avg_duration_sla`
- Occurs when running in headless mode
- Related to Kivy image texture loading

---

## 3. CODE-DATABASE ALIGNMENT

### 3.1 Documentation vs Reality

**docs/SYSTEM_REQUIREMENTS.md** defines:
```
FR-004: Tree Management
- FR-004.1: Create tree records with name, location, variety
- FR-004.2: Associate multiple scans with single tree
- FR-004.3: Display tree scan history
- FR-004.4: Calculate tree health score
- FR-004.5: Support tree deletion with cascade
```

**Status:** ❌ **CANNOT BE IMPLEMENTED** with current `populated_mangofy.db`

### 3.2 Code That Will Fail

**Records Screen (lines 1-300):**
```python
# Will crash when trying to load trees
def on_enter(self):
    db = app.db_manager
    db.get_all_trees_async(on_success_callback=self._populate_trees)
    # ❌ Query fails: no such table: tbl_tree
```

**Save Screen (lines 1-400):**
```python
def on_save(self):
    tree_id = self.selected_tree['id']  # Get tree ID
    app.db_manager.save_record_async(
        tree_id=tree_id,  # ❌ Column doesn't exist in populated DB
        disease_id=disease_id,
        # ...
    )
```

**Image Selection Screen:**
```python
def on_enter(self):
    tree_id = getattr(app, 'selected_tree_id', None)
    app.db_manager.get_records_for_tree_async(tree_id, ...)
    # ❌ Query with JOIN to tbl_tree will fail
```

---

## 4. ROOT CAUSE ANALYSIS

### 4.1 What Happened

The `populated_mangofy.db` file appears to have been created using an **older database initialization script** that:
1. Did NOT include `tbl_tree` table
2. Did NOT include `tree_id` foreign key in `tbl_scan_record`
3. Used different foreign key constraints
4. Added `is_archived` column not in current code

### 4.2 How Current Code Got Out of Sync

**Likely timeline:**
1. Initial version had simpler schema (no tree management)
2. Code was enhanced to add tree management feature
3. `database.py` was updated with new schema
4. `populated_mangofy.db` was NOT regenerated
5. Tests were written for new schema
6. Nobody tested with the populated database file

### 4.3 Why Tests Pass

**Database tests pass because:**
- They use in-memory databases (`:memory:`)
- They call `initialize_database()` which creates correct schema
- They never touch `populated_mangofy.db`

**UI tests are skipped because:**
- Headless environment can't render Kivy UI
- Missing test data/images
- Missing ML models

---

## 5. IMPACT ASSESSMENT

### 5.1 Features Completely Broken

❌ **Tree Management**
- Cannot create trees
- Cannot view tree list
- Cannot select tree for scanning
- Cannot view tree history
- Cannot delete trees

❌ **Save Functionality**
- Cannot save scan results (missing `tree_id`)
- Any save attempt will crash with SQL error

❌ **Records View**
- Cannot display records organized by tree
- Cannot navigate to tree's scan history

### 5.2 Features That Might Work

✅ **Disease Classification**
- Analysis code doesn't depend on database
- Can still run inference (if models exist)

⚠️ **Viewing Results**
- Can display results in ResultScreen
- Cannot save them to database

⚠️ **Basic Navigation**
- Welcome → Home → Scan screens work
- Cannot proceed past ResultScreen

### 5.3 User Experience Impact

**User Journey Breakdown:**
1. ✅ Launch app
2. ✅ Navigate to scan screen
3. ✅ Capture/select image
4. ✅ See analysis result
5. ❌ **CRASH** when trying to save
6. ❌ **CRASH** when viewing records

---

## 6. RECOMMENDED SOLUTIONS

### 6.1 Immediate Fix (Option A): Regenerate populated_mangofy.db

**Steps:**
1. Delete `populated_mangofy.db`
2. Run database initialization:
   ```python
   from app.core.database import DatabaseManager
   db = DatabaseManager('populated_mangofy.db', synchronous=True)
   db.initialize_database()
   ```
3. Re-populate with sample data using corrected `populate_dataset.py`
4. Verify schema matches code expectations

**Pros:** ✅ Aligns database with code, fixes all issues  
**Cons:** ⚠️ Loses any existing data in populated database

### 6.2 Alternative Fix (Option B): Update Code to Match DB

**Steps:**
1. Remove all `tbl_tree` references from code
2. Remove `tree_id` from `tbl_scan_record` INSERT statements
3. Update all screens to remove tree management
4. Update tests to match simplified schema

**Pros:** ✅ Keeps existing populated data  
**Cons:** ❌ Removes documented feature (FR-004), ❌ Breaks user manual

### 6.3 Migration Fix (Option C): Add Migration Script

**Steps:**
1. Detect schema version in database
2. Run migration to add `tbl_tree` table
3. Add `tree_id` column to `tbl_scan_record`
4. Create default tree and link existing records
5. Update foreign keys

**Pros:** ✅ Preserves data, ✅ Aligns with code  
**Cons:** ⚠️ More complex, takes more time

---

## 7. TESTING RECOMMENDATIONS

### 7.1 Add Schema Validation Tests

```python
def test_database_schema_matches_expectations():
    """Verify populated database has required schema."""
    conn = sqlite3.connect('populated_mangofy.db')
    cursor = conn.cursor()
    
    # Check tbl_tree exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_tree'")
    assert cursor.fetchone() is not None, "tbl_tree table missing!"
    
    # Check tree_id column exists in tbl_scan_record
    cursor.execute("PRAGMA table_info(tbl_scan_record)")
    columns = [row[1] for row in cursor.fetchall()]
    assert 'tree_id' in columns, "tree_id column missing!"
```

### 7.2 Add Integration Tests

```python
def test_app_can_load_populated_database():
    """Verify app can actually use populated_mangofy.db."""
    db = DatabaseManager('populated_mangofy.db')
    
    # Should be able to get trees
    trees = db.get_all_trees_async()
    assert trees is not None
    
    # Should be able to save with tree_id
    db.save_record_async(tree_id=1, disease_id=1, ...)
```

### 7.3 Pre-commit Hooks

Add check to verify:
1. Schema definition in `database.py`
2. Schema in `populated_mangofy.db`
3. Schema in documentation

All three must match!

---

## 8. PRIORITY ACTION ITEMS

### Immediate (Before Any Code Changes)
1. ✅ **Backup current populated_mangofy.db**
2. ✅ **Document exact schema differences**
3. ✅ **Identify all affected code paths**

### High Priority (Fix Core Functionality)
1. 🔥 **Decide on solution approach** (Option A, B, or C)
2. 🔥 **Fix database schema mismatch**
3. 🔥 **Verify all screens can load/save data**
4. 🔥 **Run full integration test with real database**

### Medium Priority (Improve Quality)
1. ⚠️ **Fix import path inconsistencies**
2. ⚠️ **Add schema validation tests**
3. ⚠️ **Update test documentation with actual pass rate**
4. ⚠️ **Fix performance test segfaults**

### Low Priority (Nice to Have)
1. 📝 **Add migration system for future schema changes**
2. 📝 **Automate populated database generation**
3. 📝 **Add pre-commit schema validation**

---

## 9. CONCLUSION

The MangoFy application has **solid architectural foundations** but suffers from a **critical database integrity issue** that prevents core functionality from working. The codebase is well-structured, tests are comprehensive, but the `populated_mangofy.db` file was created with an incompatible schema.

**Recommended Immediate Action:** **Option A** (Regenerate populated database)
- Fastest path to working system
- Aligns database with documented requirements
- Enables full feature testing
- Minimal code changes required

**Estimated Fix Time:** 1-2 hours  
**Risk Level:** Low (if backup is taken first)  
**Business Impact:** Critical - app currently cannot save data

---

## Appendix A: Complete Schema Comparison

### Expected Schema (from database.py)
```sql
CREATE TABLE tbl_tree (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE tbl_disease (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    description TEXT,
    symptoms TEXT,
    prevention TEXT
);

CREATE TABLE tbl_severity_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    description TEXT
);

CREATE TABLE tbl_scan_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id INTEGER,
    disease_id INTEGER,
    severity_level_id INTEGER,
    severity_percentage REAL,
    image_path TEXT,
    scan_timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(tree_id) REFERENCES tbl_tree(id) ON DELETE CASCADE,
    FOREIGN KEY(disease_id) REFERENCES tbl_disease(id) ON DELETE RESTRICT,
    FOREIGN KEY(severity_level_id) REFERENCES tbl_severity_level(id) ON DELETE RESTRICT
);
```

### Actual Schema (populated_mangofy.db)
```sql
-- tbl_tree: MISSING ENTIRELY

CREATE TABLE tbl_disease (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    symptoms TEXT,
    prevention TEXT
);

CREATE TABLE tbl_severity_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE tbl_scan_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    disease_id INTEGER,
    severity_level_id INTEGER,
    severity_percentage REAL,
    image_path TEXT,
    is_archived INTEGER DEFAULT 0,  -- Extra column
    FOREIGN KEY (disease_id) REFERENCES tbl_disease(id) ON DELETE SET NULL,
    FOREIGN KEY (severity_level_id) REFERENCES tbl_severity_level(id) ON DELETE SET NULL
);
```

### Key Differences Summary
| Aspect | Expected | Actual | Impact |
|--------|----------|--------|--------|
| `tbl_tree` table | ✅ Required | ❌ Missing | **CRITICAL** |
| `tbl_scan_record.tree_id` | ✅ Required | ❌ Missing | **CRITICAL** |
| `tbl_scan_record.is_archived` | ❌ Not in code | ✅ Present | Unused |
| FK cascade behavior | RESTRICT/CASCADE | SET NULL | Different semantics |
| Timestamp defaults | `datetime('now')` | `CURRENT_TIMESTAMP` | Format difference |

---

**Assessment Complete**  
**Next Step:** Choose fix option and implement solution
