#!/usr/bin/env python3
"""
Script to regenerate populated_mangofy.db with the correct schema.
Direct SQLite version without Kivy dependencies.
"""

import sys
import os
import sqlite3
import shutil
from datetime import datetime

def create_correct_schema(conn):
    """Create the correct database schema as defined in database.py."""
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    # Create tbl_tree (THIS IS THE MISSING TABLE!)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tbl_tree (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    
    # Create tbl_disease
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tbl_disease (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            symptoms TEXT,
            prevention TEXT
        )
    ''')
    
    # Create tbl_severity_level
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tbl_severity_level (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT
        )
    ''')
    
    # Create tbl_scan_record WITH tree_id
    cursor.execute('''
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
    ''')
    
    # Seed lookup data
    cursor.execute("INSERT OR IGNORE INTO tbl_disease (id, name, description, symptoms, prevention) VALUES (1, 'Anthracnose', '', '', '')")
    cursor.execute("INSERT OR IGNORE INTO tbl_disease (id, name, description, symptoms, prevention) VALUES (2, 'Healthy', '', '', '')")
    
    cursor.execute("INSERT OR IGNORE INTO tbl_severity_level (id, name, description) VALUES (1, 'Healthy', '')")
    cursor.execute("INSERT OR IGNORE INTO tbl_severity_level (id, name, description) VALUES (2, 'Early Stage', '')")
    cursor.execute("INSERT OR IGNORE INTO tbl_severity_level (id, name, description) VALUES (3, 'Advanced Stage', '')")
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tree_name ON tbl_tree(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tree_created ON tbl_tree(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_tree ON tbl_scan_record(tree_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_disease ON tbl_scan_record(disease_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_timestamp ON tbl_scan_record(scan_timestamp)')
    
    conn.commit()

def regenerate_database(old_db_path, new_db_path):
    """Regenerate database with correct schema, migrating data."""
    
    print(f"Starting database regeneration...")
    print(f"Old database: {old_db_path}")
    print(f"New database: {new_db_path}")
    
    # Step 1: Read data from old database
    print("\n1. Reading data from old database...")
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    # Get existing diseases
    old_cursor.execute("SELECT * FROM tbl_disease ORDER BY id")
    old_diseases = [dict(row) for row in old_cursor.fetchall()]
    print(f"   Found {len(old_diseases)} diseases")
    
    # Get existing severity levels
    old_cursor.execute("SELECT * FROM tbl_severity_level ORDER BY id")
    old_severities = [dict(row) for row in old_cursor.fetchall()]
    print(f"   Found {len(old_severities)} severity levels")
    
    # Get existing scan records
    old_cursor.execute("""
        SELECT 
            r.id,
            r.scan_timestamp,
            r.disease_id,
            r.severity_level_id,
            r.severity_percentage,
            r.image_path,
            d.name as disease_name,
            s.name as severity_name
        FROM tbl_scan_record r
        LEFT JOIN tbl_disease d ON r.disease_id = d.id
        LEFT JOIN tbl_severity_level s ON r.severity_level_id = s.id
        ORDER BY r.id
    """)
    old_records = [dict(row) for row in old_cursor.fetchall()]
    print(f"   Found {len(old_records)} scan records")
    
    old_conn.close()
    
    # Step 2: Create new database with correct schema
    print("\n2. Creating new database with correct schema...")
    
    # Remove if exists
    if os.path.exists(new_db_path):
        os.remove(new_db_path)
    
    new_conn = sqlite3.connect(new_db_path)
    create_correct_schema(new_conn)
    print("   Schema created successfully")
    
    # Step 3: Create a default tree for migrated records
    print("\n3. Creating default tree for migrated records...")
    default_tree_name = "Imported Records"
    new_cursor = new_conn.cursor()
    new_cursor.execute("INSERT INTO tbl_tree (name) VALUES (?)", (default_tree_name,))
    tree_id = new_cursor.lastrowid
    new_conn.commit()
    print(f"   Created tree '{default_tree_name}' with id={tree_id}")
    
    # Step 4: Migrate data
    print("\n4. Migrating data to new database...")
    
    # Migrate diseases (update existing, they were seeded)
    for disease in old_diseases:
        new_cursor.execute("""
            INSERT OR REPLACE INTO tbl_disease (id, name, description, symptoms, prevention)
            VALUES (?, ?, ?, ?, ?)
        """, (
            disease['id'],
            disease['name'],
            disease.get('description', ''),
            disease.get('symptoms', ''),
            disease.get('prevention', '')
        ))
    print(f"   Migrated {len(old_diseases)} diseases")
    
    # Migrate severity levels
    for severity in old_severities:
        new_cursor.execute("""
            INSERT OR REPLACE INTO tbl_severity_level (id, name, description)
            VALUES (?, ?, ?)
        """, (
            severity['id'],
            severity['name'],
            severity.get('description', '')
        ))
    print(f"   Migrated {len(old_severities)} severity levels")
    
    # Migrate scan records (add tree_id)
    migrated_count = 0
    for record in old_records:
        try:
            new_cursor.execute("""
                INSERT INTO tbl_scan_record 
                (tree_id, disease_id, severity_level_id, severity_percentage, image_path, scan_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                tree_id,  # All records go to default tree
                record['disease_id'],
                record['severity_level_id'],
                record['severity_percentage'],
                record['image_path'],
                record['scan_timestamp']
            ))
            migrated_count += 1
        except Exception as e:
            print(f"   Warning: Could not migrate record {record['id']}: {e}")
    
    print(f"   Migrated {migrated_count}/{len(old_records)} scan records")
    
    new_conn.commit()
    
    # Step 5: Verify migration
    print("\n5. Verifying migration...")
    
    # Verify tables exist
    new_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in new_cursor.fetchall()]
    expected_tables = ['tbl_disease', 'tbl_scan_record', 'tbl_severity_level', 'tbl_tree']
    
    for table in expected_tables:
        if table in tables:
            print(f"   ✅ {table} exists")
        else:
            print(f"   ❌ {table} MISSING!")
    
    # Verify tree_id column
    new_cursor.execute("PRAGMA table_info(tbl_scan_record)")
    columns = [row[1] for row in new_cursor.fetchall()]
    if 'tree_id' in columns:
        print(f"   ✅ tree_id column exists in tbl_scan_record")
    else:
        print(f"   ❌ tree_id column MISSING!")
    
    # Verify record count
    new_cursor.execute("SELECT COUNT(*) FROM tbl_scan_record")
    new_count = new_cursor.fetchone()[0]
    print(f"   📊 Records in new DB: {new_count} (expected: {len(old_records)})")
    
    # Verify foreign keys work
    new_cursor.execute("SELECT COUNT(*) FROM tbl_tree")
    tree_count = new_cursor.fetchone()[0]
    print(f"   📊 Trees in DB: {tree_count}")
    
    new_conn.close()
    
    print("\n✅ Database regeneration complete!")
    print(f"\nNew database: {new_db_path}")
    print(f"Backup of old: {old_db_path}")
    
    return True

if __name__ == "__main__":
    # Paths
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    old_db = os.path.join(project_root, 'populated_mangofy.db.backup')
    new_db = os.path.join(project_root, 'populated_mangofy.db')
    
    if not os.path.exists(old_db):
        print(f"Error: Backup database not found at {old_db}")
        print("Please run: cp populated_mangofy.db populated_mangofy.db.backup")
        sys.exit(1)
    
    try:
        regenerate_database(old_db, new_db)
        print("\n✅ SUCCESS: Database regenerated with correct schema")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
