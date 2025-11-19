import unittest, os, sys, sqlite3, tempfile, shutil

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.core.database import DatabaseManager

class TestDatabaseMigration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'migrate.db')
        # Pre-create DB with a row
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE tbl_tree (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
        conn.execute("INSERT INTO tbl_tree (name) VALUES ('PreExisting')")
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initialize_preserves_existing_rows(self):
        mgr = DatabaseManager(db_path=self.db_path, synchronous=True)
        # Call initialize (should add missing tables without dropping existing tree rows)
        mgr.initialize_database()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('SELECT name FROM tbl_tree')
            names = [r[0] for r in cur.fetchall()]
        self.assertIn('PreExisting', names, 'Existing data lost during initialization')

if __name__ == '__main__':
    unittest.main()
