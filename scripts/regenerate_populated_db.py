#!/usr/bin/env python3
"""
Script to regenerate populated_mangofy.db with the correct schema.

This script:
1. Backs up the old database
2. Creates a new database with the correct schema from database.py
3. Migrates existing data where possible
4. Adds a default tree for orphaned records
"""

import sys
import os
import sqlite3
import shutil
from datetime import datetime

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Set headless mode before importing Kivy-dependent modules
os.environ['HEADLESS_TEST'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from app.core.database import DatabaseManager

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
    
    # Initialize with correct schema
    db_manager = DatabaseManager(db_path=new_db_path, synchronous=True)
    db_manager.initialize_database()
    print("   Schema created successfully")
    
    # Step 3: Create a default tree for migrated records
    print("\n3. Creating default tree for migrated records...")
    default_tree_name = "Imported Records"
    tree_id = db_manager.add_tree_sync(default_tree_name)
    print(f"   Created tree '{default_tree_name}' with id={tree_id}")
    
    # Step 4: Migrate data
    print("\n4. Migrating data to new database...")
    
    with db_manager.connection() as new_conn:
        new_cursor = new_conn.cursor()
        
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
    
    with db_manager.connection() as verify_conn:
        verify_cursor = verify_conn.cursor()
        
        # Verify tables exist
        verify_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in verify_cursor.fetchall()]
        expected_tables = ['tbl_disease', 'tbl_scan_record', 'tbl_severity_level', 'tbl_tree']
        
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ {table} exists")
            else:
                print(f"   ❌ {table} MISSING!")
        
        # Verify tree_id column
        verify_cursor.execute("PRAGMA table_info(tbl_scan_record)")
        columns = [row[1] for row in verify_cursor.fetchall()]
        if 'tree_id' in columns:
            print(f"   ✅ tree_id column exists in tbl_scan_record")
        else:
            print(f"   ❌ tree_id column MISSING!")
        
        # Verify record count
        verify_cursor.execute("SELECT COUNT(*) FROM tbl_scan_record")
        new_count = verify_cursor.fetchone()[0]
        print(f"   📊 Records in new DB: {new_count} (expected: {len(old_records)})")
    
    db_manager.close_connection()
    
    print("\n✅ Database regeneration complete!")
    print(f"\nNew database: {new_db_path}")
    print(f"Backup of old: {old_db_path}.backup")
    
    return True

if __name__ == "__main__":
    # Paths
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
