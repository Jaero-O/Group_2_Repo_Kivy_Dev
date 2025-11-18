import os
import sys
import tempfile

# Ensure src is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app.core.database import DatabaseManager


def test_mangofy_db_is_created_in_user_data_dir(tmp_path):
    user_dir = tmp_path / 'user_data'
    user_dir.mkdir()

    db_path = os.path.join(str(user_dir), 'mangofy.db')

    # Create the DB using DatabaseManager (synchronous mode for tests)
    mgr = DatabaseManager(db_path=db_path, synchronous=True)
    mgr.initialize_database()
    mgr.close_connection()

    assert os.path.exists(db_path)
    # Clean up
    try:
        os.remove(db_path)
    except Exception:
        pass
