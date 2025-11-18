import sqlite3
import os
import threading
from contextlib import closing, contextmanager
from kivy.clock import mainthread, Clock

class DatabaseManager:
    def __init__(self, db_path, synchronous=False):
        self.db_path = db_path
        self.synchronous = synchronous
        self._sync_conn = None  # Stores a single connection for synchronous operations
        self._local = threading.local() # Thread-local storage for connections

        if not synchronous:
            # In a real app, set WAL mode once for the DB file for better concurrency.
            # This is persistent.
            try:
                with closing(sqlite3.connect(self.db_path)) as conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.commit()
            except sqlite3.Error as e:
                print(f"Warning: Could not set WAL mode on {self.db_path}: {e}")

    def _create_new_connection(self):
        """
        Creates and returns a new, optimized SQLite connection.
        This is a helper for _create_connection and __init__.
        """
        # Let sqlite3.connect raise an exception if it fails.
        # This will be caught by the calling method (e.g., initialize_database).
        conn = sqlite3.connect(self.db_path, timeout=15) # Set a timeout for locked db
        conn.row_factory = sqlite3.Row # Allow column access by name
        # --- RPi OPTIMIZATIONS ---
        # 1. Performance: Batch commits, safe from corruption (Session-specific)
        conn.execute("PRAGMA synchronous=NORMAL;")
        # 2. Integrity: Enforce foreign key constraints (Session-specific)
        conn.execute("PRAGMA foreign_keys=ON;")
        # 3. Performance: Set a reasonable in-memory cache (Session-specific, -4000 = 4MB)
        conn.execute("PRAGMA cache_size=-4000;")
        return conn

    def _create_connection(self):
        """DEPRECATED. Use the `connection` context manager instead."""
        # This method is kept for backward compatibility with some test helpers,
        # but new code should use the context manager.
        if self.synchronous:
            if self._sync_conn is None:
                self._sync_conn = self._create_new_connection()
            return self._sync_conn
        return self._create_new_connection()

    @contextmanager
    def connection(self):
        """Provides a thread-safe database connection as a context manager."""
        if self.synchronous:
            if self._sync_conn is None:
                self._sync_conn = self._create_new_connection()
            yield self._sync_conn
        else:
            # Use thread-local storage to manage connections per thread
            if not hasattr(self._local, 'conn'):
                self._local.conn = self._create_new_connection()
            try:
                yield self._local.conn
            finally:
                self._local.conn.close()
                del self._local.conn

    def close_connection(self):
        """Closes the synchronous connection if it exists."""
        if self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None

    def _add_column_if_not_exists(self, cursor, table_name, column_name, column_definition):
        """
        Helper function to add a column to a table if it doesn't already exist.
        This is useful for simple database schema migrations.
        """
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        if column_name not in columns:
            print(f"Column '{column_name}' not found in '{table_name}'. Adding it...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
            print(f"Column '{column_name}' added successfully.")
        else:
            print(f"Column '{column_name}' already exists in '{table_name}'.")




    def initialize_database(self):
        """
        Creates all necessary tables and populates lookup data if tables are empty.
        Safe to call on every app startup.
        """
        print("Initializing database...")
        try:
            with self.connection() as conn:
                c = conn.cursor()

                # --- Create Tables (if they don't exist) ---
                # Tree Table (Parent for Scan Records)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS tbl_tree (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
                
                # Severity Level Table (Lookup)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS tbl_severity_level (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT
                    );
                ''')

                # Disease Table (Lookup)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS tbl_disease (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        symptoms TEXT,
                        prevention TEXT
                    );
                ''')

                # Scan Record Table (Main Data)
                c.execute('''
                    CREATE TABLE IF NOT EXISTS tbl_scan_record (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        tree_id INTEGER,
                        disease_id INTEGER,
                        severity_level_id INTEGER,
                        severity_percentage REAL,
                        image_path TEXT,
                        is_archived INTEGER DEFAULT 0,
                        FOREIGN KEY (tree_id) REFERENCES tbl_tree(id) ON DELETE CASCADE,
                        FOREIGN KEY (disease_id) REFERENCES tbl_disease(id) ON DELETE RESTRICT,
                        FOREIGN KEY (severity_level_id) REFERENCES tbl_severity_level(id) ON DELETE RESTRICT
                    );
                ''')

                # --- Create Indexes for faster queries ---
                c.execute("CREATE INDEX IF NOT EXISTS idx_scan_record_timestamp ON tbl_scan_record(scan_timestamp);")
                c.execute("CREATE INDEX IF NOT EXISTS idx_scan_record_tree_id ON tbl_scan_record(tree_id);")
                c.execute("CREATE INDEX IF NOT EXISTS idx_scan_record_disease_id ON tbl_scan_record(disease_id);")
                c.execute("CREATE INDEX IF NOT EXISTS idx_scan_record_severity_id ON tbl_scan_record(severity_level_id);")

                # --- Populate Lookup Data (if empty) ---
                # Check if disease table is empty before populating
                c.execute("SELECT COUNT(id) FROM tbl_disease")
                if c.fetchone()[0] == 0:
                    c.execute("""
                        INSERT INTO tbl_disease (name, description, symptoms, prevention) VALUES
                        ('Anthracnose', 
                         'A common fungal disease affecting mangoes, caused by Colletotrichum gloeosporioides. It primarily affects fruits, leaves, and flowers.',
                         'Dark, sunken, irregular-shaped spots on fruits and leaves. Can cause blossom blight.',
                         'Prune infected branches, apply appropriate fungicides, and ensure good air circulation.'),
                        ('Healthy', 
                         'The plant shows no signs of disease or pest infestation.',
                         'No visible spots, discoloration, or wilting.',
                         'Maintain good agricultural practices, proper irrigation, and nutrient management.'),
                        ('Other Disease',
                         'A placeholder for diseases not specifically classified in this database.',
                         'Symptoms may vary widely depending on the specific disease.',
                         'Consult agricultural experts for diagnosis and treatment options.')
                    """)

                # Check if severity level table is empty before populating
                c.execute("SELECT COUNT(id) FROM tbl_severity_level")
                if c.fetchone()[0] == 0:
                    c.execute("""
                        INSERT INTO tbl_severity_level (name, description) VALUES
                        ('Healthy', 'No visible signs of infection.'),
                        ('Early Stage', 'Minor lesions, less than 10% of the surface area is affected.'),
                        ('Advanced Stage', 'Significant lesions, 10% or more of the surface area is affected.')
                    """)
                
                # Commit all changes
                conn.commit()
                print("Database initialized and lookup data populated.")

        except sqlite3.Error as e:
            print(f"CRITICAL: Failed to initialize database: {e}")
            # Re-raise the exception so the main app can catch it and stop.
            raise


    def _send_callback_to_main_thread(self, callback, *args):
        """Helper to schedule a callback on Kivy's main thread."""
        if callback:
            if self.synchronous:
                callback(*args)  # In sync mode, call directly for immediate testing.
            else:
                Clock.schedule_once(lambda dt: callback(*args))

    def save_record_async(self, disease_id, severity_level_id, severity_percentage, image_path, tree_id=None, on_success_callback=None, on_error_callback=None):
        """Asynchronously saves a new scan record to the database."""
        if self.synchronous:
            self._threaded_save_record(disease_id, severity_level_id, severity_percentage, image_path, tree_id, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_save_record,
                             args=(disease_id, severity_level_id, severity_percentage, image_path, tree_id, on_success_callback, on_error_callback)).start()

    def _threaded_save_record(self, disease_id, severity_level_id, severity_percentage, image_path, tree_id, on_success_callback, on_error_callback):
        """Internal method to run the DB insert operation in a separate thread."""
        try:
            with self.connection() as conn:
                conn.execute(
                    'INSERT INTO tbl_scan_record (tree_id, disease_id, severity_level_id, severity_percentage, image_path) VALUES (?, ?, ?, ?, ?)',
                    (tree_id, disease_id, severity_level_id, severity_percentage, image_path)
                )
                conn.commit()
                self._send_callback_to_main_thread(on_success_callback, True)
        except sqlite3.IntegrityError as e:
            print(f"Database Error (save_record): {e}")
            self._send_callback_to_main_thread(on_error_callback, f"Integrity Error: {e}")
        except Exception as e:
            print(f"Error saving record: {e}")
            self._send_callback_to_main_thread(on_error_callback, f"General Error: {e}")

    def get_lookup_ids(self, disease_name, severity_name, conn=None):
        disease_id = None
        severity_level_id = None
        
        # If no connection is provided, create a temporary one.
        # Otherwise, use the existing connection provided.
        # This logic is complex. A better way is to ensure the caller manages the connection.
        # For now, we'll adapt it to the new context manager if no conn is passed.
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT id FROM tbl_disease WHERE name = ?", (disease_name,))
                row = c.fetchone()
                if row: disease_id = row['id']
                c.execute("SELECT id FROM tbl_severity_level WHERE name = ?", (severity_name,))
                row = c.fetchone()
                if row: severity_level_id = row['id']
                return disease_id, severity_level_id
            except Exception as e:
                print(f"Error getting lookup IDs: {e}")
                return None, None
        else: # No connection passed, use the context manager
            try:
                with self.connection() as new_conn:
                    return self.get_lookup_ids(disease_name, severity_name, conn=new_conn)
            except Exception as e:
                print(f"Error getting lookup IDs in new connection: {e}")
                return None, None


    def get_disease_and_severity_details(self, disease_name: str, severity_name: str) -> dict:
        """
        Fetches detailed descriptions for a given disease and severity level name.

        Args:
            disease_name (str): The name of the disease (e.g., 'Anthracnose').
            severity_name (str): The name of the severity level (e.g., 'Early Stage').

        Returns:
            dict: A dictionary containing the details, or an empty dict if not found.
        """
        details = {}
        try:
            with self.connection() as conn:
                cursor = conn.cursor()

                # Fetch disease details
                cursor.execute(
                    "SELECT description, symptoms, prevention FROM tbl_disease WHERE name = ?",
                    (disease_name,)
                )
                disease_row = cursor.fetchone()
                if disease_row:
                    details['disease_description'] = disease_row['description']
                    details['disease_symptoms'] = disease_row['symptoms']
                    details['disease_prevention'] = disease_row['prevention']

                # Fetch severity details only if a severity_name is provided
                if severity_name:
                    cursor.execute(
                        "SELECT description FROM tbl_severity_level WHERE name = ?",
                        (severity_name,)
                    )
                    severity_row = cursor.fetchone()
                    if severity_row:
                        details['severity_description'] = severity_row['description']
                return details
        except Exception as e:
            print(f"Error fetching disease/severity details for '{disease_name}', '{severity_name}': {e}")
            return {}

    def get_all_records_async(self, on_success_callback, on_error_callback=None):
        if self.synchronous:
            self._threaded_get_all_records(on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_get_all_records,
                            args=(on_success_callback, on_error_callback)).start()

    def _threaded_get_all_records(self, on_success_callback, on_error_callback):
        try:
            with self.connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT
                        r.id,
                        r.scan_timestamp,
                        r.severity_percentage,
                        r.image_path,
                        d.name as disease_name,
                        s.name as severity_name
                    FROM tbl_scan_record r
                    LEFT JOIN tbl_disease d ON r.disease_id = d.id
                    LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                    WHERE r.is_archived = 0
                    ORDER BY r.scan_timestamp DESC
                """)
                records = [dict(row) for row in c.fetchall()]
                self._send_callback_to_main_thread(on_success_callback, records)
        except Exception as e:
            print(f"Error getting all records: {e}")
            if on_error_callback:
                self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def get_records_for_tree_async(self, tree_id, on_success_callback, on_error_callback=None):
        """Asynchronously gets all scan records for a specific tree."""
        if self.synchronous:
            self._threaded_get_records_for_tree(tree_id, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_get_records_for_tree,
                             args=(tree_id, on_success_callback, on_error_callback)).start()

    def _threaded_get_records_for_tree(self, tree_id, on_success_callback, on_error_callback):
        """Worker thread to fetch records for a tree."""
        try:
            with self.connection() as conn:
                c = conn.cursor()
                # First, get the tree name
                c.execute("SELECT name FROM tbl_tree WHERE id = ?", (tree_id,))
                tree_row = c.fetchone()
                tree_name = tree_row['name'] if tree_row else "Unknown Tree"

                # Then, get all associated records
                c.execute("""
                    SELECT
                        r.id, r.scan_timestamp, r.severity_percentage, r.image_path,
                        d.name as disease_name, s.name as severity_name
                    FROM tbl_scan_record r
                    LEFT JOIN tbl_disease d ON r.disease_id = d.id
                    LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                    WHERE r.tree_id = ? AND r.is_archived = 0
                    ORDER BY r.scan_timestamp DESC
                """, (tree_id,))
                records = [dict(row) for row in c.fetchall()]
                self._send_callback_to_main_thread(on_success_callback, (records, tree_name))
        except Exception as e:
            print(f"Error getting records for tree {tree_id}: {e}")
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def get_record_by_id_async(self, record_id, on_success_callback, on_error_callback=None):
        """Asynchronously retrieves a single scan record by its ID."""
        if self.synchronous:
            self._threaded_get_record_by_id(record_id, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_get_record_by_id,
                             args=(record_id, on_success_callback, on_error_callback)).start()

    def _threaded_get_record_by_id(self, record_id, on_success_callback, on_error_callback):
        """Worker thread to fetch a single record by its ID."""
        try:
            with self.connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT
                        r.id,
                        r.scan_timestamp,
                        r.severity_percentage,
                        r.image_path,
                        d.name as disease_name,
                        s.name as severity_name
                    FROM tbl_scan_record r
                    LEFT JOIN tbl_disease d ON r.disease_id = d.id
                    LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                    WHERE r.id = ?
                """, (record_id,))
                record = c.fetchone()
                if record:
                    self._send_callback_to_main_thread(on_success_callback, dict(record))
                else:
                    raise Exception(f"No record found with ID {record_id}")
        except Exception as e:
            error_msg = f"Error getting record by ID {record_id}: {e}"
            print(error_msg)
            if on_error_callback:
                self._send_callback_to_main_thread(on_error_callback, error_msg)

    def bulk_insert_records(self, records_data: list, tree_id: int = None):
        """
        Synchronously inserts multiple scan records into the database.
        This method is intended for bulk operations like dataset population.
        
        Args:
            records_data: A list of dictionaries, where each dictionary contains
                          the necessary record data.
            tree_id (int, optional): The ID of the tree to associate all records with.
                                     Defaults to None.
        """
        if not records_data:
            print("No records to insert.")
            return

        print(f"Attempting to insert {len(records_data)} records in bulk...")
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                
                # Prepare data for insertion
                data_to_insert = []
                for record in records_data:
                    disease_name = record.get("disease_name")
                    severity_name = record.get("severity_name")
                    severity_percentage = record.get("severity_percentage")
                    image_path = record.get("image_path")

                    if not all([disease_name, severity_name, image_path is not None]):
                        print(f"Skipping record due to missing data: {record}")
                        continue

                    disease_id, severity_level_id = self.get_lookup_ids(disease_name, severity_name, conn=conn)

                    if disease_id is None or severity_level_id is None:
                        print(f"Warning: Could not find DB IDs for disease '{disease_name}' or severity '{severity_name}'. Skipping record.")
                        continue
                    
                    data_to_insert.append((tree_id, disease_id, severity_level_id, severity_percentage, image_path))

                if data_to_insert:
                    cursor.executemany(
                        'INSERT INTO tbl_scan_record (tree_id, disease_id, severity_level_id, severity_percentage, image_path) VALUES (?, ?, ?, ?, ?)',
                        data_to_insert
                    )
                    conn.commit()
                    print(f"Successfully inserted {len(data_to_insert)} records.")
                else:
                    print("No valid records to insert after lookup.")

        except sqlite3.IntegrityError as e:
            print(f"Database Error (bulk_insert_records): Integrity Error: {e}")
        except Exception as e:
            print(f"Error during bulk record insertion: {e}")

    def archive_record_async(self, record_id, archive=True, on_success_callback=None, on_error_callback=None):
        """Asynchronously archives or un-archives a record by its ID."""
        if self.synchronous:
            self._threaded_archive_record(record_id, archive, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_archive_record,
                             args=(record_id, archive, on_success_callback, on_error_callback)).start()

    def _threaded_archive_record(self, record_id, archive, on_success_callback, on_error_callback):
        """Internal method to run the DB archive/un-archive operation in a separate thread."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE tbl_scan_record SET is_archived = ? WHERE id = ?', (1 if archive else 0, record_id))
                conn.commit()
                if cursor.rowcount > 0:
                    self._send_callback_to_main_thread(on_success_callback, record_id)
                else:
                    raise Exception(f"No record found with ID {record_id} to archive/un-archive.")
        except Exception as e:
            print(f"Error archiving record ID {record_id}: {e}")
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def update_record_async(self, record_id, new_data: dict, on_success_callback=None, on_error_callback=None):
        """
        Asynchronously updates an existing scan record.
        `new_data` is a dictionary with keys matching column names to update.
        e.g., {'disease_id': 1, 'severity_percentage': 25.5}
        """
        if self.synchronous:
            self._threaded_update_record(record_id, new_data, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_update_record,
                             args=(record_id, new_data, on_success_callback, on_error_callback)).start()

    def _threaded_update_record(self, record_id, new_data, on_success_callback, on_error_callback):
        """Internal method to run the DB update operation in a separate thread."""
        if not new_data:
            self._send_callback_to_main_thread(on_error_callback, "Error: No data provided for update.")
            return

        set_clause = ', '.join([f"{key} = ?" for key in new_data.keys()])
        values = list(new_data.values()) + [record_id]

        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'UPDATE tbl_scan_record SET {set_clause} WHERE id = ?', values)
                conn.commit()
                self._send_callback_to_main_thread(on_success_callback, record_id)
        except Exception as e:
            print(f"Error updating record ID {record_id}: {e}")
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def delete_record_async(self, record_id, on_success_callback=None, on_error_callback=None):
        """Asynchronously deletes a record by its ID."""
        if self.synchronous:
            self._threaded_delete_record(record_id, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_delete_record,
                             args=(record_id, on_success_callback, on_error_callback)).start()

    def _threaded_delete_record(self, record_id, on_success_callback, on_error_callback):
        """Internal method to run the DB delete operation in a separate thread."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tbl_scan_record WHERE id = ?', (record_id,))
                conn.commit()
                if cursor.rowcount > 0:
                    self._send_callback_to_main_thread(on_success_callback, record_id)
                else:
                    raise Exception(f"No record found with ID {record_id} to delete.")
        except Exception as e:
            print(f"Error deleting record ID {record_id}: {e}")
            if on_error_callback:
                self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def clear_all_scan_records(self):
        """
        Synchronously deletes all records from tbl_scan_record and resets the
        autoincrement counter for that table.
        WARNING: This is a destructive operation and cannot be undone.
        """
        print("WARNING: Deleting all records from tbl_scan_record...")
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tbl_scan_record;')
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='tbl_scan_record';")
                conn.commit()
                print("All scan records have been deleted and the ID counter has been reset.")
        except Exception as e:
            print(f"Error clearing all scan records: {e}")

    # --- Tree Management Methods ---

    def add_tree_async(self, tree_name, on_success_callback=None, on_error_callback=None):
        """Asynchronously adds a new tree or fetches it if it already exists."""
        if self.synchronous:
            self._threaded_add_tree(tree_name, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_add_tree,
                             args=(tree_name, on_success_callback, on_error_callback)).start()

    def _threaded_add_tree(self, tree_name, on_success_callback, on_error_callback):
        """Worker thread to add or fetch a tree."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO tbl_tree (name) VALUES (?)', (tree_name,))
                new_id = cursor.lastrowid
                conn.commit()
                self._send_callback_to_main_thread(on_success_callback, {'id': new_id, 'name': tree_name})
        except sqlite3.IntegrityError as e:
            # This error means the tree name already exists due to the UNIQUE constraint.
            # We fetch the existing tree instead of failing.
            with self.connection() as conn: # Use the connection context manager to ensure a valid state
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM tbl_tree WHERE name = ?", (tree_name,))
                row = cursor.fetchone()
                self._send_callback_to_main_thread(on_success_callback, dict(row) if row else None)
        except Exception as e:
            self._send_callback_to_main_thread(on_error_callback, f"Error adding tree: {e}")

    def add_tree_sync(self, tree_name: str) -> int:
        """
        Synchronously adds a tree and returns its ID. If the tree exists,
        it fetches and returns the existing ID. For use in scripts or tests.
        """
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO tbl_tree (name) VALUES (?)', (tree_name,))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM tbl_tree WHERE name = ?", (tree_name,))
                row = cursor.fetchone()
                return row['id'] if row else None
        except Exception as e:
            print(f"Error in add_tree_sync: {e}")
            return None

    def get_all_trees_async(self, on_success_callback, on_error_callback=None):
        """Asynchronously gets all trees from the database."""
        if self.synchronous:
            self._threaded_get_all_trees(on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_get_all_trees,
                             args=(on_success_callback, on_error_callback)).start()

    def _threaded_get_all_trees(self, on_success_callback, on_error_callback):
        try:
            with self.connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, name FROM tbl_tree ORDER BY name ASC")
                trees = [dict(row) for row in c.fetchall()]
                self._send_callback_to_main_thread(on_success_callback, trees)
        except Exception as e:
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def update_tree_name_async(self, tree_id, new_name, on_success_callback=None, on_error_callback=None):
        """Asynchronously updates a tree's name."""
        if self.synchronous:
            self._threaded_update_tree_name(tree_id, new_name, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_update_tree_name,
                             args=(tree_id, new_name, on_success_callback, on_error_callback)).start()

    def _threaded_update_tree_name(self, tree_id, new_name, on_success_callback, on_error_callback):
        try:
            with self.connection() as conn:
                conn.execute('UPDATE tbl_tree SET name = ? WHERE id = ?', (new_name, tree_id))
                conn.commit()
                self._send_callback_to_main_thread(on_success_callback, tree_id, new_name)
        except Exception as e:
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")

    def delete_tree_async(self, tree_id, on_success_callback=None, on_error_callback=None):
        """Asynchronously deletes a tree and all its associated scan records (due to ON DELETE CASCADE)."""
        if self.synchronous:
            self._threaded_delete_tree(tree_id, on_success_callback, on_error_callback)
        else:
            threading.Thread(target=self._threaded_delete_tree,
                             args=(tree_id, on_success_callback, on_error_callback)).start()

    def _threaded_delete_tree(self, tree_id, on_success_callback, on_error_callback):
        try:
            with self.connection() as conn:
                conn.execute('DELETE FROM tbl_tree WHERE id = ?', (tree_id,))
                conn.commit()
                self._send_callback_to_main_thread(on_success_callback, tree_id)
        except Exception as e:
            self._send_callback_to_main_thread(on_error_callback, f"Error: {e}")
