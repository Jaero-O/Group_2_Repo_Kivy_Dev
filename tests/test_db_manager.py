import os
import sys
import tempfile

# Ensure `src` is importable when running tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from app.core.database import DatabaseManager


def test_database_manager_basic_flow():
    # Create a temporary DB file in the workspace
    tmp_db = os.path.join(ROOT, 'test_mangofy.db')
    # Ensure no leftover
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    mgr = DatabaseManager(db_path=tmp_db, synchronous=True)
    # Should create tables without raising
    mgr.initialize_database()

    # Add a tree and verify it exists
    new_id = mgr.add_tree_sync('UnitTestTree')
    assert isinstance(new_id, int)

    with mgr.connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM tbl_tree WHERE id = ?', (new_id,))
        row = cur.fetchone()
        assert row is not None
        assert row['name'] == 'UnitTestTree'

    # Clean up
    mgr.close_connection()
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
