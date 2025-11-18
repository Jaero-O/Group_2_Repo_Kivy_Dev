import unittest
import sqlite3
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the 'src' directory to the Python path
from src.app.core.database import DatabaseManager

class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        """Set up a new, in-memory database for each test."""
        # Use the synchronous flag built into DatabaseManager for predictable testing.
        # This makes all async methods run on the same thread, eliminating race conditions.
        self.db_manager = DatabaseManager(db_path=':memory:', synchronous=True)
        self.db_manager.initialize_database()

    def _add_tree_and_get_id(self, tree_name: str) -> int:
        """Helper method to synchronously add a tree and return its ID."""
        on_added_callback = MagicMock()
        self.db_manager.add_tree_async(tree_name, on_success_callback=on_added_callback)
        on_added_callback.assert_called_once()
        return on_added_callback.call_args[0][0]['id']

    def _add_record_and_get_id(self, tree_id: int, image_path: str) -> int:
        """Helper method to synchronously add a record and return its ID."""
        records_to_insert = [{"image_path": image_path, "disease_name": "Healthy", "severity_percentage": 0.0, "severity_name": "Healthy"}]
        self.db_manager.bulk_insert_records(records_to_insert, tree_id=tree_id)
        on_get_all = MagicMock()
        self.db_manager.get_records_for_tree_async(tree_id, on_success_callback=on_get_all)
        return on_get_all.call_args[0][0][0][0]['id']

    def tearDown(self):
        self.db_manager.close_connection()

    def test_initialize_database_creates_tables(self):
        """Test that all expected tables are created after initialization."""
        try:
            # Use the internal connection creator to inspect the schema
            with self.db_manager._create_connection() as conn:
                cursor = conn.cursor()
                
                # Check tbl_scan_record
                cursor.execute("SELECT id, tree_id, disease_id, severity_level_id, severity_percentage, image_path, scan_timestamp FROM tbl_scan_record")
                
                # Check tbl_tree
                cursor.execute("SELECT id, name, created_at FROM tbl_tree")
                
                # Check tbl_disease_lookup
                cursor.execute("SELECT id, name, description, symptoms, prevention FROM tbl_disease")

                # Check tbl_severity_lookup
                cursor.execute("SELECT id, name, description FROM tbl_severity_level")
                
        except sqlite3.Error as e:
            self.fail(f"Database schema verification failed: {e}")

    def test_add_and_get_tree_async(self):
        """Test adding a tree and retrieving all trees."""
        on_added_callback = MagicMock()
        on_get_all_callback = MagicMock()

        # Add trees
        self.db_manager.add_tree_async("Mango Tree 1", on_success_callback=on_added_callback)
        self.db_manager.add_tree_async("Mango Tree 2", on_success_callback=on_added_callback)

        # Get all trees
        self.db_manager.get_all_trees_async(on_success_callback=on_get_all_callback)

        # Check add_tree callbacks
        self.assertEqual(on_added_callback.call_count, 2)

        # Check get_all_trees callback
        on_get_all_callback.assert_called_once()
        all_trees = on_get_all_callback.call_args[0][0]
        self.assertEqual(len(all_trees), 2) # Now it should correctly find 2 trees
        tree_names = {t['name'] for t in all_trees}
        self.assertIn("Mango Tree 1", tree_names)
        self.assertIn("Mango Tree 2", tree_names)

    def test_save_and_get_record_async(self):
        """Test saving a single record and retrieving it asynchronously."""
        tree_id = self._add_tree_and_get_id("Test Tree")

        # --- Test: Save a record ---
        on_save_callback = MagicMock()
        self.db_manager.save_record_async(
            tree_id=tree_id,
            disease_id=1, # Anthracnose
            severity_level_id=2, # Early Stage (ID=2)
            severity_percentage=15.5,
            image_path='/path/to/image1.jpg',
            on_success_callback=on_save_callback
        )
        on_save_callback.assert_called_once_with(True)

        # --- Test: Get the record back ---
        on_get_callback = MagicMock()
        self.db_manager.get_records_for_tree_async(tree_id, on_success_callback=on_get_callback)

        on_get_callback.assert_called_once()
        
        # The callback receives a tuple (records, tree_name)
        records, tree_name = on_get_callback.call_args[0][0]
        self.assertEqual(tree_name, "Test Tree")
        self.assertEqual(len(records), 1)
        
        retrieved_record = records[0]
        self.assertEqual(retrieved_record['image_path'], '/path/to/image1.jpg')
        self.assertEqual(retrieved_record['disease_name'], 'Anthracnose')
        self.assertEqual(retrieved_record['severity_name'], 'Early Stage')
        self.assertAlmostEqual(retrieved_record['severity_percentage'], 15.5)

    def test_get_lookup_ids(self):
        """Test the get_lookup_ids method."""
        disease_id, severity_id = self.db_manager.get_lookup_ids("Anthracnose", "Early Stage")
        self.assertEqual(disease_id, 1)
        self.assertEqual(severity_id, 2)

        disease_id, severity_id = self.db_manager.get_lookup_ids("Healthy", "Healthy")
        self.assertEqual(disease_id, 2) # Based on INSERT order
        self.assertEqual(severity_id, 1) # Based on INSERT order

    def test_bulk_insert_and_clear_records(self):
        """Test bulk inserting records and clearing them."""
        tree_id = self._add_tree_and_get_id("Bulk Tree")
        
        records_to_insert = [
            {"image_path": "/path/bulk.jpg", "disease_name": "Anthracnose", "severity_percentage": 50.0, "severity_name": "Advanced Stage"},
        ]
        self.db_manager.bulk_insert_records(records_to_insert, tree_id=tree_id)
        
        # Verify insertion
        on_get_callback = MagicMock()
        self.db_manager.get_records_for_tree_async(tree_id, on_success_callback=on_get_callback)
        records, _ = on_get_callback.call_args.args[0]
        self.assertEqual(len(records), 1)

        # --- Test: Clear Records ---
        self.db_manager.clear_all_scan_records()

        on_get_after_clear = MagicMock()
        self.db_manager.get_records_for_tree_async(tree_id, on_success_callback=on_get_after_clear)
        records_after_clear, _ = on_get_after_clear.call_args[0][0]
        self.assertEqual(len(records_after_clear), 0)

    def test_get_record_by_id_async(self):
        """Test retrieving a single record by its ID."""
        tree_id = self._add_tree_and_get_id("Single Record Tree")
        inserted_record_id = self._add_record_and_get_id(tree_id, "/path/single.jpg")

        # --- Test: Get the record by its ID ---
        on_get_by_id = MagicMock()
        self.db_manager.get_record_by_id_async(inserted_record_id, on_success_callback=on_get_by_id)

        on_get_by_id.assert_called_once()
        retrieved_record = on_get_by_id.call_args[0][0]
        self.assertEqual(retrieved_record['id'], inserted_record_id)
        self.assertEqual(retrieved_record['disease_name'], 'Healthy')
        self.assertEqual(retrieved_record['image_path'], '/path/single.jpg')

    def test_initialize_database_connection_error(self):
        """Test that initialize_database raises an error if the DB connection fails."""
        # We patch 'sqlite3.connect' within the 'database' module where it's called.
        with patch('src.app.core.database.sqlite3.connect') as mock_connect:
            # Configure the mock to raise a database error upon connection attempt.
            mock_connect.side_effect = sqlite3.OperationalError("Unable to open database file")

            # We must create a new instance here because the one in setUp() is already initialized.
            # We expect the constructor to work, but initialization to fail.
            db_manager = DatabaseManager(db_path='/path/to/nonexistent.db')

            # Assert that calling initialize_database raises the expected exception.
            # The `assertRaises` context manager catches and verifies the exception.
            with self.assertRaises(sqlite3.OperationalError) as cm:
                db_manager.initialize_database()

            # Optionally, assert the error message for more specific testing.
            self.assertIn("Unable to open database file", str(cm.exception))

    def test_delete_tree_cascades_to_records(self):
        """Test that deleting a tree also deletes its associated scan records via ON DELETE CASCADE."""
        # --- 1. Setup: Add a tree and some records ---
        tree_id = self._add_tree_and_get_id("Cascade Test Tree")
        self._add_record_and_get_id(tree_id, "/path/cascade1.jpg")
        self._add_record_and_get_id(tree_id, "/path/cascade2.jpg")

        # --- 2. Verify initial state: Records exist ---
        on_get_before_delete = MagicMock()
        self.db_manager.get_records_for_tree_async(tree_id, on_success_callback=on_get_before_delete)
        on_get_before_delete.assert_called_once()
        records_before, _ = on_get_before_delete.call_args[0][0]
        self.assertEqual(len(records_before), 2, "Records should exist before deleting the tree.")

        # --- 3. Action: Delete the parent tree ---
        on_delete_callback = MagicMock()
        self.db_manager.delete_tree_async(tree_id, on_success_callback=on_delete_callback)
        on_delete_callback.assert_called_once_with(tree_id)

        # --- 4. Assert final state: Associated records are gone ---
        on_get_after_delete = MagicMock()
        self.db_manager.get_records_for_tree_async(tree_id, on_success_callback=on_get_after_delete)
        on_get_after_delete.assert_called_once()
        records_after, tree_name_after = on_get_after_delete.call_args[0][0]
        self.assertEqual(len(records_after), 0, "Scan records should be deleted after the parent tree is deleted.")
        self.assertEqual(tree_name_after, "Unknown Tree", "The tree name should be 'Unknown' as the tree no longer exists.")

    def test_add_duplicate_tree_name_fetches_existing(self):
        """Test that adding a tree with a duplicate name fetches the existing tree instead of failing."""
        # --- 1. Add a tree ---
        on_first_add = MagicMock()
        self.db_manager.add_tree_async("Duplicate Tree", on_success_callback=on_first_add)
        on_first_add.assert_called_once()
        original_tree_id = on_first_add.call_args[0][0]['id']

        # --- 2. Add the same tree again ---
        on_second_add = MagicMock()
        self.db_manager.add_tree_async("Duplicate Tree", on_success_callback=on_second_add)
        on_second_add.assert_called_once()
        duplicate_tree_id = on_second_add.call_args[0][0]['id']

        # --- 3. Assert that the ID is the same, proving it fetched the existing one ---
        self.assertEqual(original_tree_id, duplicate_tree_id, "Adding a duplicate tree should return the ID of the existing tree.")

        # --- 4. Verify that only one tree with that name exists in the DB ---
        on_get_all = MagicMock()
        self.db_manager.get_all_trees_async(on_success_callback=on_get_all)
        all_trees = on_get_all.call_args[0][0]
        filtered_trees = [t for t in all_trees if t['name'] == "Duplicate Tree"]
        self.assertEqual(len(filtered_trees), 1, "There should only be one tree with the duplicate name in the database.")

    def test_foreign_key_restrict_prevents_deletion(self):
        """Test that ON DELETE RESTRICT prevents deleting a disease that is in use."""
        # --- 1. Setup: Add a tree and a record that uses the 'Anthracnose' disease ---
        tree_id = self._add_tree_and_get_id("FK Test Tree")
        records_to_insert = [{"image_path": "/path/fk_test.jpg", "disease_name": "Anthracnose", "severity_percentage": 20.0, "severity_name": "Advanced Stage"}]
        self.db_manager.bulk_insert_records(records_to_insert, tree_id=tree_id)

        # --- 2. Action: Attempt to delete the 'Anthracnose' record from the lookup table ---
        # We expect this to fail due to the FOREIGN KEY constraint.
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db_manager._create_connection() as conn:
                # The 'Anthracnose' disease has ID 1 based on insertion order.
                conn.execute("DELETE FROM tbl_disease WHERE id = 1")
                conn.commit()
