import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, Callable, List, Dict, Tuple
import shutil
from pathlib import Path
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = ':memory:', synchronous: bool = False):
        self.db_path = db_path
        self.synchronous = synchronous
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

    @contextmanager
    def _create_connection(self):
        """Context manager that yields a sqlite3.Connection. Connection
        is created lazily (not in __init__) so tests can patch sqlite3.connect
        before initialize_database() is called.
        """
        with self._lock:
            if self._conn is None:
                # Create a single connection and reuse it. Tests rely on
                # consistent in-memory behavior when db_path=':memory:'.
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.execute('PRAGMA foreign_keys = ON;')
            try:
                yield self._conn
            finally:
                # Do not close here; allow explicit close_connection()
                pass

    def initialize_database(self):
        with self._create_connection() as conn:
            cur = conn.cursor()
            # Create tables
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS tbl_tree (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                '''
            )

            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS tbl_disease (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    symptoms TEXT,
                    prevention TEXT
                )
                '''
            )

            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS tbl_severity_level (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT
                )
                '''
            )

            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS tbl_scan_record (
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
                )
                '''
            )

            # Seed lookup data in a deterministic order matching tests.
            # Diseases: 1 -> Anthracnose, 2 -> Healthy
            cur.execute("INSERT OR IGNORE INTO tbl_disease (id, name, description, symptoms, prevention) VALUES (1, 'Anthracnose', '', '', '')")
            cur.execute("INSERT OR IGNORE INTO tbl_disease (id, name, description, symptoms, prevention) VALUES (2, 'Healthy', '', '', '')")

            # Severity levels: 1 -> Healthy, 2 -> Early Stage, 3 -> Advanced Stage
            cur.execute("INSERT OR IGNORE INTO tbl_severity_level (id, name, description) VALUES (1, 'Healthy', '')")
            cur.execute("INSERT OR IGNORE INTO tbl_severity_level (id, name, description) VALUES (2, 'Early Stage', '')")
            cur.execute("INSERT OR IGNORE INTO tbl_severity_level (id, name, description) VALUES (3, 'Advanced Stage', '')")

            conn.commit()
            
            # Create performance indexes
            self._create_indexes(cur)
            conn.commit()
            
            logger.info("Database initialization complete")
    
    def _create_indexes(self, cursor):
        """Create indexes on frequently queried columns for better performance."""
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tree_name ON tbl_tree(name)')
            
            # Check if created_at column exists before creating index
            cursor.execute("PRAGMA table_info(tbl_tree)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'created_at' in columns:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tree_created ON tbl_tree(created_at)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_tree ON tbl_scan_record(tree_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_disease ON tbl_scan_record(disease_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_timestamp ON tbl_scan_record(scan_timestamp)')
            logger.debug("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")

    @contextmanager
    def connection(self):
        """Public context manager exposed for tests that need direct SQL access.
        Wraps the internal lazy connection creator and ensures a row factory
        that allows dict-like access (row['col']).
        """
        with self._create_connection() as conn:
            if conn.row_factory is None:
                conn.row_factory = sqlite3.Row
            yield conn

    def close_connection(self):
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    # --- Helper methods for synchronous/asynchronous behavior ---
    def _maybe_async(self, func: Callable, *args, **kwargs):
        if self.synchronous:
            return func(*args, **kwargs)
        else:
            t = threading.Thread(target=func, args=args, kwargs=kwargs)
            t.daemon = True
            t.start()

    # --- Public API used by tests and app ---
    def add_tree_async(self, name: str, on_success_callback: Optional[Callable] = None):
        def _add():
            with self._create_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT id FROM tbl_tree WHERE name = ?', (name,))
                row = cur.fetchone()
                if row:
                    tree_id = row[0]
                else:
                    cur.execute('INSERT INTO tbl_tree (name) VALUES (?)', (name,))
                    conn.commit()
                    tree_id = cur.lastrowid
                result = {'id': tree_id, 'name': name}
                if on_success_callback:
                    on_success_callback(result)
                return result
        return self._maybe_async(_add)

    def add_tree_sync(self, name: str) -> int:
        """Synchronous helper used by integration tests and scripts."""
        with self._create_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT id FROM tbl_tree WHERE name = ?', (name,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute('INSERT INTO tbl_tree (name) VALUES (?)', (name,))
            conn.commit()
            return cur.lastrowid

    def get_all_trees_async(self, on_success_callback: Optional[Callable] = None):
        def _get_all():
            with self._create_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT id, name, created_at FROM tbl_tree')
                rows = cur.fetchall()
                out = [{'id': r[0], 'name': r[1], 'created_at': r[2]} for r in rows]
                if on_success_callback:
                    on_success_callback(out)
                return out
        return self._maybe_async(_get_all)

    def get_lookup_ids(self, disease_name: str, severity_name: str) -> Tuple[int, int]:
        with self._create_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT id FROM tbl_disease WHERE name = ?', (disease_name,))
            d = cur.fetchone()
            disease_id = d[0] if d else None
            cur.execute('SELECT id FROM tbl_severity_level WHERE name = ?', (severity_name,))
            s = cur.fetchone()
            severity_id = s[0] if s else None
            # If a lookup is missing, insert it to preserve behavior in tests that
            # expect missing lookups to be created implicitly.
            if disease_id is None:
                cur.execute('INSERT INTO tbl_disease (name) VALUES (?)', (disease_name,))
                conn.commit()
                disease_id = cur.lastrowid
            if severity_id is None:
                cur.execute('INSERT INTO tbl_severity_level (name) VALUES (?)', (severity_name,))
                conn.commit()
                severity_id = cur.lastrowid
            return disease_id, severity_id

    def bulk_insert_records(self, records: List[Dict], tree_id: int):
        with self._create_connection() as conn:
            cur = conn.cursor()
            for rec in records:
                disease_name = rec.get('disease_name', 'Healthy')
                severity_name = rec.get('severity_name', 'Healthy')
                severity_percentage = rec.get('severity_percentage', 0.0)
                image_path = rec.get('image_path')
                disease_id, severity_id = self.get_lookup_ids(disease_name, severity_name)
                cur.execute(
                    'INSERT INTO tbl_scan_record (tree_id, disease_id, severity_level_id, severity_percentage, image_path) VALUES (?, ?, ?, ?, ?)',
                    (tree_id, disease_id, severity_id, severity_percentage, image_path)
                )
            conn.commit()

    def get_records_for_tree_async(self, tree_id: int, on_success_callback: Optional[Callable] = None):
        def _get():
            with self._create_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT id, name FROM tbl_tree WHERE id = ?', (tree_id,))
                tr = cur.fetchone()
                tree_name = tr[1] if tr else 'Unknown Tree'

                cur.execute(
                    '''
                    SELECT r.id, r.image_path, r.severity_percentage,
                           d.name as disease_name, s.name as severity_name
                    FROM tbl_scan_record r
                    LEFT JOIN tbl_disease d ON r.disease_id = d.id
                    LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                    WHERE r.tree_id = ?
                    ORDER BY r.id ASC
                    ''',
                    (tree_id,)
                )
                rows = cur.fetchall()
                out = []
                for r in rows:
                    out.append({
                        'id': r[0],
                        'image_path': r[1],
                        'severity_percentage': r[2],
                        'disease_name': r[3],
                        'severity_name': r[4],
                    })
                if on_success_callback:
                    on_success_callback((out, tree_name))
                return out, tree_name
        return self._maybe_async(_get)

    def save_record_async(self, tree_id: int, disease_id: int, severity_level_id: int, severity_percentage: float, image_path: str, on_success_callback: Optional[Callable] = None):
        def _save():
            with self._create_connection() as conn:
                cur = conn.cursor()
                cur.execute('INSERT INTO tbl_scan_record (tree_id, disease_id, severity_level_id, severity_percentage, image_path) VALUES (?, ?, ?, ?, ?)',
                            (tree_id, disease_id, severity_level_id, severity_percentage, image_path))
                conn.commit()
                if on_success_callback:
                    on_success_callback(True)
                return True
        return self._maybe_async(_save)

    def get_record_by_id_async(self, record_id: int, on_success_callback: Optional[Callable] = None):
        def _get():
            with self._create_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    '''
                    SELECT r.id, r.image_path, r.severity_percentage, d.name as disease_name
                    FROM tbl_scan_record r
                    LEFT JOIN tbl_disease d ON r.disease_id = d.id
                    WHERE r.id = ?
                    ''',
                    (record_id,)
                )
                r = cur.fetchone()
                if not r:
                    result = None
                else:
                    result = {'id': r[0], 'image_path': r[1], 'severity_percentage': r[2], 'disease_name': r[3]}
                if on_success_callback:
                    on_success_callback(result)
                return result
        return self._maybe_async(_get)

    def delete_tree_async(self, tree_id: int, on_success_callback: Optional[Callable] = None):
        def _del():
            with self._create_connection() as conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM tbl_tree WHERE id = ?', (tree_id,))
                conn.commit()
                if on_success_callback:
                    on_success_callback(tree_id)
                return tree_id
        return self._maybe_async(_del)

    def clear_all_scan_records(self):
        with self._create_connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM tbl_scan_record')
            conn.commit()
    
    def backup_database(self, backup_dir: Optional[str] = None) -> Optional[str]:
        """Create a backup of the database file.
        
        Args:
            backup_dir: Directory to store backup. If None, uses user data directory.
        
        Returns:
            Path to backup file if successful, None otherwise.
        """
        if self.db_path == ':memory:':
            logger.warning("Cannot backup in-memory database")
            return None
        
        try:
            # Determine backup directory
            if backup_dir is None:
                import os
                if os.name == 'nt':  # Windows
                    backup_dir = Path(os.environ.get('APPDATA', '')) / 'mangofy' / 'backups'
                else:  # Linux/Mac
                    backup_dir = Path.home() / '.local' / 'share' / 'mangofy' / 'backups'
            else:
                backup_dir = Path(backup_dir)
            
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"mangofy_backup_{timestamp}.db"
            backup_path = backup_dir / backup_filename
            
            # Ensure connection is flushed
            with self._lock:
                if self._conn:
                    self._conn.commit()
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
            
            # Clean old backups (keep last 10)
            self._cleanup_old_backups(backup_dir, keep=10)
            
            return str(backup_path)
        
        except Exception as e:
            logger.error(f"Database backup failed: {e}", exc_info=True)
            return None
    
    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 10):
        """Remove old backup files, keeping only the most recent ones.
        
        Args:
            backup_dir: Directory containing backups
            keep: Number of backups to keep
        """
        try:
            backups = sorted(
                backup_dir.glob('mangofy_backup_*.db'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backups[keep:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup.name}")
        
        except Exception as e:
            logger.warning(f"Could not cleanup old backups: {e}")
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from a backup file.
        
        Args:
            backup_path: Path to backup file
        
        Returns:
            True if successful, False otherwise.
        """
        if self.db_path == ':memory:':
            logger.warning("Cannot restore to in-memory database")
            return False
        
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Close existing connection
            self.close_connection()
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from: {backup_path}")
            
            # Reinitialize connection
            self.initialize_database()
            return True
        
        except Exception as e:
            logger.error(f"Database restore failed: {e}", exc_info=True)
            return False
