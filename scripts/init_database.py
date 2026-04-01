#!/usr/bin/env python3
"""
Database Initialization Script for MangoFy System
Creates SQLite database with all required tables and seed data
Run this on Raspberry Pi: python3 scripts/init_database.py
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime

# Database path - use relative path from script location
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / "kivy-lcd-app" / "mangofy.db"

def create_database():
    """Create database with complete schema and seed data."""
    
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if database already exists
    if DB_PATH.exists():
        backup_path = DB_PATH.parent / f"mangofy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        print(f"⚠️  Database already exists. Creating backup: {backup_path}")
        import shutil
        shutil.copy2(DB_PATH, backup_path)
    
    print(f"📦 Creating database: {DB_PATH}")
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    try:
        # Enable foreign keys and set pragmas
        print("⚙️  Setting database pragmas...")
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        
        # Create tbl_tree table
        print("📋 Creating tbl_tree table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_tree (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                location TEXT,
                variety TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create tbl_disease table
        print("📋 Creating tbl_disease table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_disease (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                symptoms TEXT,
                prevention TEXT
            );
        """)
        
        # Create tbl_severity_level table
        print("📋 Creating tbl_severity_level table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_severity_level (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        # Create tbl_scan_record table
        print("📋 Creating tbl_scan_record table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_scan_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tree_id INTEGER REFERENCES tbl_tree(id) ON DELETE CASCADE,
                disease_id INTEGER REFERENCES tbl_disease(id) ON DELETE SET NULL,
                severity_level_id INTEGER REFERENCES tbl_severity_level(id) ON DELETE SET NULL,
                
                -- Core scan metadata
                scan_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                scan_duration REAL,
                scan_status TEXT,
                
                -- Classification results
                disease_class TEXT,
                confidence_score REAL,
                pred_anthracnose REAL,
                pred_healthy REAL,
                pred_bacterial_canker REAL,
                pred_cutting_weevil REAL,
                pred_powdery_mildew REAL,
                pred_sooty_mould REAL,
                
                -- Severity analysis
                severity_percentage REAL,
                severity_level TEXT,
                
                -- Leaf measurements
                leaf_area_cm2 REAL,
                lesion_area_cm2 REAL,
                lesion_count INTEGER,
                mean_lesion_size_px REAL,
                
                -- Color analysis - Leaf
                leaf_mean_r REAL,
                leaf_mean_g REAL,
                leaf_mean_b REAL,
                
                -- Color analysis - Lesion
                lesion_mean_r REAL,
                lesion_mean_g REAL,
                lesion_mean_b REAL,
                lesion_to_leaf_color_ratio_g REAL,
                
                -- Vegetation indices
                exg_mean REAL,
                ndvi_proxy_mean REAL,
                
                -- Shape features
                leaf_solidity REAL,
                leaf_circularity REAL,
                leaf_aspect_ratio REAL,
                
                -- Texture features
                damage_pct_inpaint REAL,
                lesion_glcm_contrast REAL,
                lesion_glcm_dissimilarity REAL,
                lesion_glcm_energy REAL,
                lesion_glcm_homogeneity REAL,
                lesion_glcm_correlation REAL,
                
                -- File references
                image_path TEXT,
                thumbnail_path TEXT,
                json_path TEXT,
                
                -- Metadata
                notes TEXT,
                is_archived INTEGER DEFAULT 0
            );
        """)
        
        # Create indexes for performance
        print("🔍 Creating database indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_scan_record_timestamp ON tbl_scan_record(scan_timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_record_tree ON tbl_scan_record(tree_id);",
            "CREATE INDEX IF NOT EXISTS idx_record_disease ON tbl_scan_record(disease_id);",
            "CREATE INDEX IF NOT EXISTS idx_record_severity ON tbl_scan_record(severity_level_id);",
            "CREATE INDEX IF NOT EXISTS idx_scan_archived ON tbl_scan_record(is_archived);",
            "CREATE INDEX IF NOT EXISTS idx_scan_tree_archived ON tbl_scan_record(tree_id, is_archived);",
            "CREATE INDEX IF NOT EXISTS idx_scan_archived_timestamp ON tbl_scan_record(is_archived, scan_timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_tree_name ON tbl_tree(name);",
        ]
        for idx_stmt in indexes:
            cur.execute(idx_stmt)
        
        # Insert seed data for diseases
        print("🌱 Inserting disease seed data...")
        diseases = [
            (1, "Anthracnose", 
             "A fungal disease caused by Colletotrichum gloeosporioides that affects mango leaves, flowers, and fruits.",
             "Dark brown or black spots on leaves, sunken lesions on fruits, premature leaf drop, and blossom blight.",
             "Apply copper-based fungicides, ensure proper drainage, remove infected plant parts, and maintain good air circulation."),
            
            (2, "Bacterial Canker",
             "A bacterial disease that causes dark, water-soaked lesions on mango leaves and stems.",
             "Water-soaked spots that turn dark brown, bacterial ooze, stem cankers, and leaf wilting.",
             "Remove infected branches, apply copper sprays, avoid overhead irrigation, and maintain tree health through proper nutrition."),
            
            (3, "Cutting Weevil",
             "Damage caused by weevil larvae that bore into young mango shoots and leaves.",
             "Wilted shoot tips, holes in young leaves, tunneling damage in stems, and stunted growth.",
             "Remove and destroy affected shoots, use pheromone traps, apply neem-based pesticides, and maintain orchard hygiene."),
            
            (4, "Powdery Mildew",
             "A fungal disease that appears as white powdery coating on mango leaves and inflorescences.",
             "White powdery patches on leaves, distorted young leaves, poor fruit set, and reduced yield.",
             "Apply sulfur-based fungicides, prune for air circulation, avoid excess nitrogen fertilization, and water management."),
            
            (5, "Sooty Mould",
             "A black fungal growth that develops on honeydew secreted by sap-sucking insects.",
             "Black sooty coating on leaves and fruits, reduced photosynthesis, and associated with insect infestation.",
             "Control sap-sucking insects (aphids, scales), wash leaves with water, improve air circulation, and use insecticidal soap if needed."),
        ]
        
        cur.executemany("""
            INSERT OR IGNORE INTO tbl_disease (id, name, description, symptoms, prevention)
            VALUES (?, ?, ?, ?, ?)
        """, diseases)
        
        # Insert seed data for severity levels
        print("🌱 Inserting severity level seed data...")
        severity_levels = [
            (1, "Low", "Minimal disease symptoms, less than 10% leaf area affected"),
            (2, "Moderate", "Moderate disease symptoms, 10-30% leaf area affected"),
            (3, "High", "Severe disease symptoms, more than 30% leaf area affected"),
        ]
        
        cur.executemany("""
            INSERT OR IGNORE INTO tbl_severity_level (id, name, description)
            VALUES (?, ?, ?)
        """, severity_levels)
        
        # Commit changes
        conn.commit()
        
        # Verify tables created
        print("\n✅ Database created successfully!")
        print("\n📊 Database Summary:")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cur.fetchall()
        print(f"   Tables created: {len(tables)}")
        for table in tables:
            print(f"      • {table[0]}")
        
        # Show disease data
        cur.execute("SELECT COUNT(*) FROM tbl_disease")
        disease_count = cur.fetchone()[0]
        print(f"   Diseases: {disease_count}")
        
        cur.execute("SELECT id, name FROM tbl_disease ORDER BY id")
        for disease_id, name in cur.fetchall():
            print(f"      {disease_id}. {name}")
        
        # Show severity levels
        cur.execute("SELECT COUNT(*) FROM tbl_severity_level")
        severity_count = cur.fetchone()[0]
        print(f"   Severity Levels: {severity_count}")
        
        cur.execute("SELECT id, name FROM tbl_severity_level ORDER BY id")
        for sev_id, name in cur.fetchall():
            print(f"      {sev_id}. {name}")
        
        print(f"\n✨ Database ready at: {DB_PATH}")
        print(f"📏 Database size: {DB_PATH.stat().st_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"\n❌ Error creating database: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

def verify_database():
    """Verify database integrity and show statistics."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return False
    
    print(f"\n🔍 Verifying database: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    try:
        # Check foreign key support
        cur.execute("PRAGMA foreign_keys;")
        fk_enabled = cur.fetchone()[0]
        print(f"   Foreign keys: {'✅ Enabled' if fk_enabled else '⚠️  Disabled'}")
        
        # Check integrity
        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchone()[0]
        print(f"   Integrity: {'✅ OK' if integrity == 'ok' else f'❌ {integrity}'}")
        
        # Check scan records
        cur.execute("SELECT COUNT(*) FROM tbl_scan_record")
        scan_count = cur.fetchone()[0]
        print(f"   Scan records: {scan_count}")
        
        if scan_count > 0:
            cur.execute("""
                SELECT scan_timestamp, disease_id, confidence_score 
                FROM tbl_scan_record 
                ORDER BY scan_timestamp DESC 
                LIMIT 5
            """)
            print(f"   Recent scans:")
            for timestamp, disease_id, confidence in cur.fetchall():
                print(f"      • {timestamp} - Disease ID: {disease_id} - Confidence: {confidence:.2%}" if confidence else f"      • {timestamp} - Disease ID: {disease_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("="*60)
    print("   MangoFy Database Initialization Script")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        # Verify existing database
        verify_database()
    else:
        # Create new database
        create_database()
        print()
        verify_database()
    
    print("\n" + "="*60)
    print("✅ Done!")
    print("="*60)
