# Mangofy App: Database Documentation Screenshots Guide

This document outlines the specific screenshots to capture for each step of the database implementation report, tailored to the Mangofy Kivy application's SQLite backend.

---

### STEP 2: Database Creation and Configuration

**Objective:** Show that the SQLite database and its tables are created correctly as defined in the code.

*   **Screenshot 2.1: Schema Definition Code**
    *   **What to capture:** The `initialize_database` method within `app/core/database.py`.
    *   **Why:** This shows the `CREATE TABLE` SQL statements for `tbl_disease`, `tbl_severity_level`, and `tbl_scan_record`, proving how the schema is defined. Highlight these statements.

*   **Screenshot 2.2: Database Initialization Output**
    *   **What to capture:** The terminal or console output when the application starts for the first time.
    *   **Why:** The output `Initializing database...` and `Database initialized and lookup data populated.` confirms that the creation code was executed successfully.

*   **Screenshot 2.3: Verified Database Structure**
    *   **What to capture:** Use a database viewer tool (like DB Browser for SQLite or a VS Code extension) to open the `mangofy.db` file. Show the list of created tables.
    *   **Why:** This provides visual, third-party verification that the tables exist as expected.

---

### STEP 3: Data Population

**Objective:** Demonstrate that the database tables have been populated with both initial lookup data and sample scan records.

*   **Screenshot 3.1: Bulk Population Script Execution**
    *   **What to capture:** The terminal output after running the `populate_dataset.py` script.
    *   **Why:** The output shows the script finding image files and the confirmation message `Successfully inserted X records`, proving the bulk insertion process worked.

*   **Screenshot 3.2: Populated Lookup Tables**
    *   **What to capture:** In a database viewer, show the content of `tbl_disease` and `tbl_severity_level` tables.
    *   **Why:** This verifies that the essential lookup data (e.g., 'Anthracnose', 'Healthy', 'Early Stage') was inserted during initialization.

*   **Screenshot 3.3: Populated Scan Records Table**
    *   **What to capture:** In a database viewer, show the rows of the `tbl_scan_record` table after running the population script.
    *   **Why:** This confirms that the dataset was successfully processed and stored as scan records, with correct foreign keys and data.

---

### STEP 4: CRUD Operations

**Objective:** Provide evidence of Create, Read, Update, and Delete operations functioning within the application.

*   **Screenshot 4.1 (Create):**
    *   **What to capture:** The `ResultScreen` of the app showing an analysis result, then the `SaveScreen` after the "Save" button is pressed, showing the success modal.
    *   **Why:** This demonstrates the "Create" operation from the user's perspective, ending in a new record being saved.

*   **Screenshot 4.2 (Read):**
    *   **What to capture:** The `RecordsScreen` of the app, displaying a list of previously saved scan records.
    *   **Why:** This shows the "Read" operation, where data is fetched from the database and displayed to the user.

*   **Screenshot 4.3 (Update):**
    *   **What to capture:** Since there is no UI for updating, show the `archive_record_async` method in `app/core/database.py` and a "before-and-after" view in a database browser where a record's `is_archived` field changes from `0` to `1`.
    *   **Why:** This demonstrates the "Update" operation by modifying an existing record's state.

*   **Screenshot 4.4 (Delete):**
    *   **What to capture:** On the `RecordsScreen`, show a record selected, the "Delete" button pressed, the confirmation modal, and finally the records list refreshed with the item gone.
    *   **Why:** This demonstrates the "Delete" operation and its confirmation flow within the UI.

---

### STEP 5: Relationship and Integrity Testing

**Objective:** Prove that the foreign key relationships between tables are enforced.

*   **Screenshot 5.1: Foreign Key Constraint Code**
    *   **What to capture:** The `_create_connection` method in `app/core/database.py`, highlighting the line `conn.execute("PRAGMA foreign_keys=ON;")`.
    *   **Why:** This shows that foreign key enforcement is actively enabled for every database connection.

*   **Screenshot 5.2: Integrity Test Output**
    *   **What to capture:** Using a database tool, attempt to `DELETE` a row from `tbl_disease` that is currently referenced by a record in `tbl_scan_record`. Capture the resulting foreign key constraint error.
    *   **Why:** This is direct proof that the database prevents the deletion of parent records (like a disease type) while child records (scan results) still depend on them, ensuring data integrity.

---

### STEP 6: Indexing and Query Optimization

**Objective:** Show that indexes have been created to improve query performance.

*   **Screenshot 6.1: Index Creation Code**
    *   **What to capture:** The `initialize_database` method in `app/core/database.py`, highlighting the `CREATE INDEX` statements.
    *   **Why:** This shows the specific columns (`scan_timestamp`, `disease_id`, etc.) that are being indexed.

*   **Screenshot 6.2: EXPLAIN QUERY PLAN Output**
    *   **What to capture:** In a database tool, run `EXPLAIN QUERY PLAN SELECT * FROM tbl_scan_record WHERE disease_id = ?;`. Capture the output.
    *   **Why:** The result should show that the query uses the index (e.g., `SEARCH TABLE tbl_scan_record USING INDEX idx_scan_record_disease_id`), proving the index is effective for lookups.

---

### STEP 7: System Integration

**Objective:** Demonstrate that the database is functionally integrated with the application's UI.

*   **Screenshot 7.1: Saving a Result (Integration)**
    *   **What to capture:** A composite image showing the `ResultScreen` with analysis data, the call to `db_manager.save_record_async` in `app/screens/result_screen.py`, and the resulting new row in the `tbl_scan_record` table viewed in a DB browser.
    *   **Why:** This provides an end-to-end view of how the front-end UI triggers a database write operation.

*   **Screenshot 7.2: Displaying Records (Integration)**
    *   **What to capture:** A composite image showing the `RecordsScreen` displaying data, the call to `db_manager.get_all_records_async` in `app/screens/records_screen.py`, and the corresponding rows in the database.
    *   **Why:** This shows the reverse: how data from the database is fetched and rendered in the UI.

---

### STEP 8: Validation, Backup, and Export

**Objective:** Show how the database can be backed up and validated.

*   **Screenshot 8.1: Database Backup**
    *   **What to capture:** A file explorer window showing the `mangofy.db` file being copied to a "backups" folder.
    *   **Why:** For SQLite, a backup is a simple file copy. This screenshot demonstrates the process. The file is located in the path provided by `App.get_running_app().user_data_dir`.

*   **Screenshot 8.2: Database Export to SQL**
    *   **What to capture:** Using a database tool, show the command or UI option to export the database to an `.sql` file (e.g., `.dump` command in the SQLite CLI) and the first few lines of the resulting SQL file.
    *   **Why:** This demonstrates a standard method for exporting the database schema and data into a universal format.