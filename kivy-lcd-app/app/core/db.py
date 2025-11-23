import os
import sqlite3
from contextlib import closing
from typing import Optional, List, Dict, Any, Callable
import threading
import time
from functools import wraps
from kivy.clock import Clock

# Environment overrides
_DB_PATH = os.getenv("MANGOFY_DB_PATH", os.path.join(os.getcwd(), "mangofy.db"))

PRAGMAS = [
    "PRAGMA foreign_keys=ON;",
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
]

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS tbl_tree (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        location TEXT,
        variety TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_disease (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        symptoms TEXT,
        prevention TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_severity_level (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tbl_scan_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tree_id INTEGER REFERENCES tbl_tree(id) ON DELETE CASCADE,
        disease_id INTEGER REFERENCES tbl_disease(id) ON DELETE SET NULL,
        severity_level_id INTEGER REFERENCES tbl_severity_level(id) ON DELETE SET NULL,
        severity_percentage REAL,
        confidence_score REAL,
        total_leaf_area REAL,
        lesion_area REAL,
        image_path TEXT,
        thumbnail_path TEXT,
        notes TEXT,
        scan_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        is_archived INTEGER DEFAULT 0
    );
    """,
    # Indices
    "CREATE INDEX IF NOT EXISTS idx_scan_record_timestamp ON tbl_scan_record(scan_timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_record_tree ON tbl_scan_record(tree_id);",
    "CREATE INDEX IF NOT EXISTS idx_record_disease ON tbl_scan_record(disease_id);",
    "CREATE INDEX IF NOT EXISTS idx_record_severity ON tbl_scan_record(severity_level_id);",
    # Performance indexes for common WHERE clauses (added 2025-11-22)
    "CREATE INDEX IF NOT EXISTS idx_scan_archived ON tbl_scan_record(is_archived);",
    "CREATE INDEX IF NOT EXISTS idx_scan_tree_archived ON tbl_scan_record(tree_id, is_archived);",
    "CREATE INDEX IF NOT EXISTS idx_scan_archived_timestamp ON tbl_scan_record(is_archived, scan_timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_tree_name ON tbl_tree(name);",
]


# ---------- Connection Pooling ---------- #

class ConnectionPool:
    """Simple connection pool for SQLite to reuse connections across queries."""
    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.pool: List[sqlite3.Connection] = []
        self.lock = threading.Lock()
        self.in_use: Dict[int, sqlite3.Connection] = {}
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from pool or create new one."""
        with self.lock:
            if self.pool:
                conn = self.pool.pop()
            else:
                conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
                with closing(conn.cursor()) as cur:
                    for stmt in PRAGMAS:
                        cur.execute(stmt)
            self.in_use[id(conn)] = conn
            return conn
    
    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return connection to pool."""
        with self.lock:
            conn_id = id(conn)
            if conn_id in self.in_use:
                del self.in_use[conn_id]
            if len(self.pool) < self.max_connections:
                self.pool.append(conn)
            else:
                conn.close()
    
    def close_all(self) -> None:
        """Close all pooled connections."""
        with self.lock:
            for conn in self.pool:
                conn.close()
            for conn in self.in_use.values():
                conn.close()
            self.pool.clear()
            self.in_use.clear()

# Global connection pool
_connection_pool = ConnectionPool(max_connections=5)

def get_connection() -> sqlite3.Connection:
    """Get a connection from the pool."""
    return _connection_pool.get_connection()

def return_connection(conn: sqlite3.Connection) -> None:
    """Return a connection to the pool."""
    _connection_pool.return_connection(conn)

# ---------- Result Caching ---------- #

class CacheEntry:
    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.time() + ttl
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class ResultCache:
    """Simple TTL-based cache for database query results."""
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            entry = self.cache.get(key)
            if entry and not entry.is_expired():
                return entry.value
            elif entry:
                del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: float = 60.0) -> None:
        with self.lock:
            self.cache[key] = CacheEntry(value, ttl)
    
    def invalidate(self, pattern: Optional[str] = None) -> None:
        """Invalidate cache entries matching pattern (or all if None)."""
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self.cache[k]

# Global result cache
_result_cache = ResultCache()

def cached_query(cache_key: str, ttl: float = 60.0):
    """Decorator to cache query results with TTL."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and args
            full_key = f"{cache_key}:{args}:{kwargs}"
            
            # Check cache
            result = _result_cache.get(full_key)
            if result is not None:
                return result
            
            # Execute query
            result = func(*args, **kwargs)
            
            # Cache result
            _result_cache.set(full_key, result, ttl)
            return result
        return wrapper
    return decorator

def invalidate_cache(pattern: Optional[str] = None) -> None:
    """Invalidate cached results."""
    _result_cache.invalidate(pattern)

# ---------- Async Query Infrastructure ---------- #

def async_query(callback: Optional[Callable] = None):
    """Decorator to execute database queries in background thread.
    
    Args:
        callback: Optional function to call with result on UI thread.
                 If provided, wrapper returns None immediately.
                 If not provided, wrapper executes synchronously (fallback).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if callback is None:
                # Synchronous execution (backward compatibility)
                return func(*args, **kwargs)
            
            def background_task():
                try:
                    result = func(*args, **kwargs)
                    # Schedule callback on UI thread
                    Clock.schedule_once(lambda dt: callback(result), 0)
                except Exception as e:
                    # Schedule error callback on UI thread
                    Clock.schedule_once(lambda dt: callback(None, error=str(e)), 0)
            
            # Start background thread
            thread = threading.Thread(target=background_task, daemon=True)
            thread.start()
            return None  # Return immediately
        
        return wrapper
    return decorator


def init_db() -> None:
    """Initialize database schema (idempotent)."""
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            for stmt in SCHEMA_STATEMENTS:
                cur.executescript(stmt) if stmt.strip().startswith("CREATE TABLE") else cur.execute(stmt)
        conn.commit()
    finally:
        return_connection(conn)

    # Perform any post-initialization upgrades (cascade / notes column)
    ensure_schema_upgrades()

def ensure_schema_upgrades() -> None:
    """Apply non-destructive schema upgrades:
    - Add notes column if missing
    - Migrate tbl_scan_record to ON DELETE CASCADE for tree_id if older RESTRICT definition present.
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            # Check columns in tbl_scan_record
            cur.execute("PRAGMA table_info(tbl_scan_record);")
            cols = {row[1] for row in cur.fetchall()}
            
            # Add missing columns
            if "notes" not in cols:
                try:
                    cur.execute("ALTER TABLE tbl_scan_record ADD COLUMN notes TEXT;")
                except sqlite3.OperationalError:
                    pass
            if "thumbnail_path" not in cols:
                try:
                    cur.execute("ALTER TABLE tbl_scan_record ADD COLUMN thumbnail_path TEXT;")
                except sqlite3.OperationalError:
                    pass
            if "confidence_score" not in cols:
                try:
                    cur.execute("ALTER TABLE tbl_scan_record ADD COLUMN confidence_score REAL;")
                except sqlite3.OperationalError:
                    pass
            if "total_leaf_area" not in cols:
                try:
                    cur.execute("ALTER TABLE tbl_scan_record ADD COLUMN total_leaf_area REAL;")
                except sqlite3.OperationalError:
                    pass
            if "lesion_area" not in cols:
                try:
                    cur.execute("ALTER TABLE tbl_scan_record ADD COLUMN lesion_area REAL;")
                except sqlite3.OperationalError:
                    pass
            
            # Check columns in tbl_tree
            cur.execute("PRAGMA table_info(tbl_tree);")
            tree_cols = {row[1] for row in cur.fetchall()}
            if "location" not in tree_cols:
                try:
                    cur.execute("ALTER TABLE tbl_tree ADD COLUMN location TEXT;")
                except sqlite3.OperationalError:
                    pass
            if "variety" not in tree_cols:
                try:
                    cur.execute("ALTER TABLE tbl_tree ADD COLUMN variety TEXT;")
                except sqlite3.OperationalError:
                    pass

            # Check foreign key behavior for tree_id
            cur.execute("PRAGMA foreign_key_list(tbl_scan_record);")
            fk_rows = cur.fetchall()
            needs_migration = False
            for fk in fk_rows:
                if fk[2] == "tbl_tree" and fk[6].upper() == "RESTRICT":
                    needs_migration = True
                    break

            if needs_migration:
                # Rename old table
                cur.execute("ALTER TABLE tbl_scan_record RENAME TO _tbl_scan_record_old;")
                # Create new table with correct schema including new columns
                cur.executescript(
                    """
                    CREATE TABLE tbl_scan_record (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tree_id INTEGER REFERENCES tbl_tree(id) ON DELETE CASCADE,
                        disease_id INTEGER REFERENCES tbl_disease(id) ON DELETE SET NULL,
                        severity_level_id INTEGER REFERENCES tbl_severity_level(id) ON DELETE SET NULL,
                        severity_percentage REAL,
                        confidence_score REAL,
                        total_leaf_area REAL,
                        lesion_area REAL,
                        image_path TEXT,
                        thumbnail_path TEXT,
                        notes TEXT,
                        scan_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        is_archived INTEGER DEFAULT 0
                    );
                    """
                )
                # Recreate indices
                cur.execute("CREATE INDEX IF NOT EXISTS idx_scan_record_timestamp ON tbl_scan_record(scan_timestamp);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_record_tree ON tbl_scan_record(tree_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_record_disease ON tbl_scan_record(disease_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_record_severity ON tbl_scan_record(severity_level_id);")
                # Copy data with default NULL for new columns
                try:
                    cur.execute("INSERT INTO tbl_scan_record(id, tree_id, disease_id, severity_level_id, severity_percentage, confidence_score, total_leaf_area, lesion_area, image_path, thumbnail_path, notes, scan_timestamp, is_archived) SELECT id, tree_id, disease_id, severity_level_id, severity_percentage, NULL, NULL, NULL, image_path, thumbnail_path, notes, scan_timestamp, is_archived FROM _tbl_scan_record_old;")
                except sqlite3.OperationalError:
                    cur.execute("INSERT INTO tbl_scan_record(id, tree_id, disease_id, severity_level_id, severity_percentage, confidence_score, total_leaf_area, lesion_area, image_path, thumbnail_path, scan_timestamp, is_archived) SELECT id, tree_id, disease_id, severity_level_id, severity_percentage, NULL, NULL, NULL, image_path, NULL, scan_timestamp, is_archived FROM _tbl_scan_record_old;")
                cur.execute("DROP TABLE _tbl_scan_record_old;")
        conn.commit()
    finally:
        return_connection(conn)

# ---------- CRUD Helpers ---------- #

def insert_tree(name: str, location: Optional[str] = None, variety: Optional[str] = None) -> int:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("INSERT OR IGNORE INTO tbl_tree(name, location, variety) VALUES (?, ?, ?)", (name, location, variety))
            conn.commit()
            # Return id (fetch existing if IGNORE triggered)
            cur.execute("SELECT id FROM tbl_tree WHERE name=?", (name,))
            row = cur.fetchone()
            # Invalidate tree-related caches
            invalidate_cache('list_trees')
            invalidate_cache('get_all_tree_names')
            return int(row[0]) if row else -1
    finally:
        return_connection(conn)


def insert_disease(name: str, description: str = "", symptoms: str = "", prevention: str = "") -> int:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT OR IGNORE INTO tbl_disease(name, description, symptoms, prevention) VALUES (?,?,?,?)",
                (name, description, symptoms, prevention)
            )
            conn.commit()
            cur.execute("SELECT id FROM tbl_disease WHERE name=?", (name,))
            row = cur.fetchone()
            # Invalidate disease cache
            invalidate_cache('list_diseases')
            return int(row[0]) if row else -1
    finally:
        return_connection(conn)


def insert_severity_level(name: str, description: str = "") -> int:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT OR IGNORE INTO tbl_severity_level(name, description) VALUES (?,?)",
                (name, description)
            )
            conn.commit()
            cur.execute("SELECT id FROM tbl_severity_level WHERE name=?", (name,))
            row = cur.fetchone()
            return int(row[0]) if row else -1
    finally:
        return_connection(conn)


def insert_scan_record(tree_id: int, disease_id: Optional[int], severity_level_id: Optional[int],
                        severity_percentage: float, image_path: str, thumbnail_path: Optional[str] = None,
                        notes: Optional[str] = None, confidence_score: Optional[float] = None,
                        total_leaf_area: Optional[float] = None, lesion_area: Optional[float] = None) -> int:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT INTO tbl_scan_record(tree_id, disease_id, severity_level_id, severity_percentage, 
                                             confidence_score, total_leaf_area, lesion_area,
                                             image_path, thumbnail_path, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (tree_id, disease_id, severity_level_id, severity_percentage, 
                 confidence_score, total_leaf_area, lesion_area,
                 image_path, thumbnail_path, notes)
            )
            conn.commit()
            # Invalidate scan count caches
            invalidate_cache('get_all_tree_scan_counts')
            invalidate_cache('count_scans_for_tree')
            invalidate_cache('count_unassigned_scans')
            return int(cur.lastrowid)
    finally:
        return_connection(conn)


def get_recent_scans(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                  SELECT r.id, r.scan_timestamp, r.severity_percentage, r.image_path, r.thumbnail_path,
                       d.name AS disease_name, s.name AS severity_name, t.name AS tree_name
                FROM tbl_scan_record r
                LEFT JOIN tbl_disease d ON r.disease_id = d.id
                LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                LEFT JOIN tbl_tree t ON r.tree_id = t.id
                WHERE r.is_archived = 0
                ORDER BY r.scan_timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cur.fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "scan_timestamp": row[1],
                    "severity_percentage": row[2],
                    "image_path": row[3],
                    "thumbnail_path": row[4],
                    "disease_name": row[5],
                    "severity_name": row[6],
                    "tree_name": row[7],
                })
            return result
    finally:
        return_connection(conn)


def archive_scan(scan_id: int) -> None:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE tbl_scan_record SET is_archived=1 WHERE id=?", (scan_id,))
            conn.commit()
            # Invalidate scan count caches
            invalidate_cache('get_all_tree_scan_counts')
            invalidate_cache('count_scans_for_tree')
    finally:
        return_connection(conn)

# ---------- New Helper APIs (Trees & Scans) ---------- #

@cached_query(cache_key='list_trees', ttl=60.0)
def list_trees() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, name, created_at FROM tbl_tree ORDER BY created_at DESC;")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]
    finally:
        return_connection(conn)

@cached_query(cache_key='get_all_tree_names', ttl=60.0)
def get_all_tree_names() -> List[str]:
    """Get list of all tree names for uniqueness validation.
    
    Returns:
        List of tree names
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT name FROM tbl_tree ORDER BY name;")
            rows = cur.fetchall()
            return [r[0] for r in rows]
    finally:
        return_connection(conn)

@cached_query(cache_key='list_diseases', ttl=60.0)
def list_diseases() -> List[Dict[str, Any]]:
    """Fetch all diseases from the database.
    
    Returns:
        List of disease dictionaries with id and name
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, name FROM tbl_disease ORDER BY name;")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1]} for r in rows]
    finally:
        return_connection(conn)

def get_tree_by_name(name: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, name, created_at FROM tbl_tree WHERE name=?", (name,))
            row = cur.fetchone()
            return {"id": row[0], "name": row[1], "created_at": row[2]} if row else None
    finally:
        return_connection(conn)

def update_tree_name(tree_id: int, new_name: str) -> bool:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE tbl_tree SET name=? WHERE id=?", (new_name, tree_id))
            conn.commit()
            # Invalidate tree caches
            invalidate_cache('list_trees')
            invalidate_cache('get_all_tree_names')
            return cur.rowcount > 0
    finally:
        return_connection(conn)

def delete_tree(tree_id: int) -> bool:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("DELETE FROM tbl_tree WHERE id=?", (tree_id,))
            conn.commit()
            # Invalidate tree and scan count caches
            invalidate_cache('list_trees')
            invalidate_cache('get_all_tree_names')
            invalidate_cache('get_all_tree_scan_counts')
            invalidate_cache('count_scans_for_tree')
            return cur.rowcount > 0
    finally:
        return_connection(conn)

def count_scans_for_tree(tree_id: int) -> int:
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT COUNT(*) FROM tbl_scan_record WHERE tree_id=? AND is_archived=0", (tree_id,))
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        return_connection(conn)


@cached_query(cache_key='get_all_tree_scan_counts', ttl=30.0)
def get_all_tree_scan_counts() -> Dict[int, int]:
    """Get scan counts for all trees in a single query (optimized for bulk loading).
    
    Returns:
        Dict mapping tree_id -> count of scans
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("""
                SELECT tree_id, COUNT(*) 
                FROM tbl_scan_record 
                WHERE is_archived=0 
                GROUP BY tree_id
            """)
            rows = cur.fetchall()
            return {row[0]: row[1] for row in rows}
    finally:
        return_connection(conn)

@cached_query(cache_key='count_unassigned_scans', ttl=30.0)
def count_unassigned_scans() -> int:
    """Count scans not associated with any tree.
    
    Returns:
        Number of scans with tree_id = NULL
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT COUNT(*) FROM tbl_scan_record WHERE tree_id IS NULL AND is_archived=0;")
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        return_connection(conn)

def get_scans_filtered(tree_id: Optional[int] = None, disease_name: Optional[str] = None, 
                      start_date: Optional[str] = None, end_date: Optional[str] = None,
                      limit: Optional[int] = None, offset: int = 0,
                      order_by: str = 'scan_timestamp', order_dir: str = 'DESC') -> List[Dict[str, Any]]:
    """Fetch scans with enhanced filtering options including date ranges and sorting.
    
    Args:
        tree_id: Filter by tree (None for all trees, or pass explicit None to get unassigned)
        disease_name: Filter by disease name
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of records to return
        offset: Number of records to skip
        order_by: Column to sort by ('scan_timestamp' or 'severity_percentage')
        order_dir: Sort direction ('ASC' or 'DESC')
    
    Returns:
        List of scan dictionaries
    """
    filters = ["r.is_archived=0"]
    params: List[Any] = []
    
    if tree_id is not None:
        filters.append("r.tree_id=?")
        params.append(tree_id)
    
    if disease_name:
        filters.append("d.name=?")
        params.append(disease_name)
    
    if start_date:
        filters.append("r.scan_timestamp >= ?")
        params.append(start_date)
    
    if end_date:
        filters.append("r.scan_timestamp <= ?")
        params.append(end_date + " 23:59:59")
    
    where_clause = " WHERE " + " AND ".join(filters)
    
    # Validate order_by to prevent SQL injection
    valid_order_columns = {'scan_timestamp': 'r.scan_timestamp', 'severity_percentage': 'r.severity_percentage'}
    order_column = valid_order_columns.get(order_by, 'r.scan_timestamp')
    order_direction = 'ASC' if order_dir.upper() == 'ASC' else 'DESC'
    
    limit_clause = f" LIMIT {limit} OFFSET {offset}" if limit is not None else ""
    
    sql = f"""
        SELECT r.id, r.scan_timestamp, r.severity_percentage, r.image_path, r.thumbnail_path, r.notes,
               d.name AS disease_name, s.name AS severity_name, t.name AS tree_name
        FROM tbl_scan_record r
        LEFT JOIN tbl_disease d ON r.disease_id = d.id
        LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
        LEFT JOIN tbl_tree t ON r.tree_id = t.id
        {where_clause}
        ORDER BY {order_column} {order_direction}
        {limit_clause}
    """
    
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "scan_timestamp": row[1],
                    "severity_percentage": row[2],
                    "image_path": row[3],
                    "thumbnail_path": row[4],
                    "notes": row[5],
                    "disease_name": row[6] or "Unknown",
                    "severity_name": row[7] or "Unknown",
                    "tree_name": row[8] or "Unassigned"
                })
            return result
    finally:
        return_connection(conn)

def get_scans(tree_id: Optional[int] = None, window_days: Optional[int] = None, disease: Optional[str] = None, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetch scans filtered by optional tree, timeframe (days), and disease name.
    
    Args:
        limit: Maximum number of records to return (for pagination)
        offset: Number of records to skip (for pagination)
    """
    filters = ["r.is_archived=0"]
    params: List[Any] = []
    if tree_id is not None:
        filters.append("r.tree_id=?")
        params.append(tree_id)
    if window_days is not None:
        filters.append("r.scan_timestamp >= datetime('now', ?)")
        params.append(f"-{window_days} days")
    if disease is not None:
        filters.append("d.name=?")
        params.append(disease)
    where_clause = " WHERE " + " AND ".join(filters) if filters else ""
    limit_clause = f" LIMIT {limit} OFFSET {offset}" if limit is not None else ""
    sql = f"""
        SELECT r.id, r.scan_timestamp, r.severity_percentage, r.image_path, r.thumbnail_path, r.notes,
               d.name AS disease_name, s.name AS severity_name, t.name AS tree_name
        FROM tbl_scan_record r
        LEFT JOIN tbl_disease d ON r.disease_id = d.id
        LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
        LEFT JOIN tbl_tree t ON r.tree_id = t.id
        {where_clause}
        ORDER BY r.scan_timestamp DESC
        {limit_clause}
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "scan_timestamp": row[1],
                    "severity_percentage": row[2],
                    "image_path": row[3],
                    "thumbnail_path": row[4],
                    "notes": row[5],
                    "disease_name": row[6],
                    "severity_name": row[7],
                    "tree_name": row[8],
                })
            return result
    finally:
        return_connection(conn)


def get_scan_detail(scan_id: int) -> Optional[Dict[str, Any]]:
    """Get full details for a single scan record.
    
    Args:
        scan_id: The scan record ID
        
    Returns:
        Dictionary with all scan details including confidence score, or None if not found
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("""
                SELECT r.id, r.scan_timestamp, r.severity_percentage, r.confidence_score,
                       r.total_leaf_area, r.lesion_area,
                       r.image_path, r.thumbnail_path, r.notes, 
                       r.tree_id, r.disease_id, r.severity_level_id,
                       d.name AS disease_name, d.description AS disease_description,
                       d.symptoms AS disease_symptoms, d.prevention AS disease_prevention,
                       s.name AS severity_name, s.description AS severity_description,
                       t.name AS tree_name
                FROM tbl_scan_record r
                LEFT JOIN tbl_disease d ON r.disease_id = d.id
                LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
                LEFT JOIN tbl_tree t ON r.tree_id = t.id
                WHERE r.id = ?
            """, (scan_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "scan_timestamp": row[1],
                "severity_percentage": row[2] or 0.0,
                "confidence_score": row[3] or 85.0,  # Use stored value or placeholder
                "total_leaf_area": row[4] or 0.0,
                "lesion_area": row[5] or 0.0,
                "image_path": row[6],
                "thumbnail_path": row[7],
                "notes": row[8],
                "tree_id": row[9],
                "disease_id": row[10],
                "severity_level_id": row[11],
                "disease_name": row[12] or "Unknown",
                "disease_description": row[13] or "",
                "disease_symptoms": row[14] or "",
                "disease_prevention": row[15] or "",
                "severity_name": row[16] or "Unknown",
                "severity_description": row[17] or "",
                "tree_name": row[18] or "Unknown",
            }
    finally:
        return_connection(conn)


def delete_scan_record(scan_id: int) -> bool:
    """Delete a scan record and its associated image files.
    
    Args:
        scan_id: The scan record ID to delete
        
    Returns:
        True if deletion succeeded, False otherwise
    """
    conn = get_connection()
    try:
        with closing(conn.cursor()) as cur:
            # First, get the image paths to delete files
            cur.execute("SELECT image_path, thumbnail_path FROM tbl_scan_record WHERE id=?", (scan_id,))
            row = cur.fetchone()
            
            if row:
                image_path, thumbnail_path = row[0], row[1]
                
                # Delete the database record
                cur.execute("DELETE FROM tbl_scan_record WHERE id=?", (scan_id,))
                conn.commit()
                
                # Delete associated image files
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError:
                        pass  # File may already be deleted
                
                if thumbnail_path and os.path.exists(thumbnail_path):
                    try:
                        os.remove(thumbnail_path)
                    except OSError:
                        pass
                
                return cur.rowcount > 0
            else:
                return False
    finally:
        # Invalidate scan count caches
        invalidate_cache('get_all_tree_scan_counts')
        invalidate_cache('count_scans_for_tree')
        invalidate_cache('count_unassigned_scans')
        return_connection(conn)


def export_scan_to_json(scan_id: int) -> Optional[str]:
    """Export a single scan record to JSON file.
    
    Args:
        scan_id: The scan record ID to export
        
    Returns:
        Path to the exported JSON file, or None on failure
    """
    import json
    from datetime import datetime
    
    scan_data = get_scan_detail(scan_id)
    
    if not scan_data:
        return None
    
    # Prepare export directory
    export_dir = os.path.join(os.getcwd(), "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scan_{scan_id}_{timestamp}.json"
    output_path = os.path.join(export_dir, filename)
    
    # Write JSON file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scan_data, f, indent=2, ensure_ascii=False)
        return output_path
    except Exception:
        return None


def export_scans_to_csv(tree_id: Optional[int] = None) -> Optional[str]:
    """Export scans to CSV file.
    
    Args:
        tree_id: Optional tree ID to filter scans (None = all scans)
        
    Returns:
        Path to the exported CSV file, or None on failure
    """
    import csv
    from datetime import datetime
    
    scans = get_scans(tree_id=tree_id)
    
    if not scans:
        return None
    
    # Prepare export directory
    export_dir = os.path.join(os.getcwd(), "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tree_suffix = f"_tree{tree_id}" if tree_id else "_all"
    filename = f"scans{tree_suffix}_{timestamp}.csv"
    output_path = os.path.join(export_dir, filename)
    
    # Write CSV file
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'scan_timestamp', 'tree_name', 'disease_name', 
                         'severity_percentage', 'severity_name', 'image_path', 'notes']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for scan in scans:
                writer.writerow({k: scan.get(k, '') for k in fieldnames})
        
        return output_path
    except Exception:
        return None

# ---------- Convenience Lookup ---------- #

def get_or_create_disease(name: str) -> int:
    return insert_disease(name)


def get_or_create_severity(name: str) -> int:
    return insert_severity_level(name)

# ---------- Seeding ---------- #

def seed_lookups(diseases: List[Dict[str, str]], severities: List[Dict[str, str]]) -> None:
    for d in diseases:
        insert_disease(
            d.get("name", ""),
            d.get("description", ""),
            d.get("symptoms", ""),
            d.get("prevention", "")
        )
    for s in severities:
        insert_severity_level(s.get("name", ""), s.get("description", ""))

# Initialize automatically on import (can be disabled if needed)
try:
    init_db()
except Exception as e:
    # Fail silently to avoid import-time crashes; calling code can retry
    print(f"[db] Initialization warning: {e}")
