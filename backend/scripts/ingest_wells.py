#!/usr/bin/env python3
"""
Ingest per-well data: metadata, equipment, inspections, maintenance, context notes
"""
import sqlite3
import json
import jsonlines
from pathlib import Path
from datetime import datetime

# Paths
BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
SAMPLE_DATA = BACKEND_DIR.parent / "sample-data" / "assets"

def ingest_well_data(well_dir, cursor):
    """Ingest all data for a single well"""
    asset_id = well_dir.name
    
    # 1. Load metadata.json
    metadata_path = well_dir / "metadata.json"
    if not metadata_path.exists():
        print(f"   ⚠️  No metadata.json for {asset_id}")
        return None
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Insert well
    cursor.execute("""
        INSERT INTO wells (
            asset_id, name, asset_category, well_type, area_id, team_id,
            in_charge_user_id, lat, lon, installed_on, recorded_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        metadata['asset_id'],
        metadata['name'],
        metadata.get('asset_category', 'oil_well'),
        metadata['well_type'],
        metadata['area_id'],
        metadata['team_id'],
        metadata['in_charge_user_id'],
        metadata['location']['lat'],
        metadata['location']['lon'],
        metadata['installed_on'],
        metadata['recorded_status']
    ))
    
    # Insert equipment
    equipment_count = 0
    for equip in metadata.get('equipment', []):
        cursor.execute("""
            INSERT INTO equipment (equipment_id, asset_id, kind, model)
            VALUES (?, ?, ?, ?)
        """, (
            equip['equipment_id'],
            metadata['asset_id'],
            equip['kind'],
            equip.get('model', '')
        ))
        equipment_count += 1
    
    # 2. Load inspections.jsonl
    inspections_path = well_dir / "inspections.jsonl"
    inspections_count = 0
    if inspections_path.exists():
        with jsonlines.open(inspections_path) as reader:
            for row in reader:
                cursor.execute("""
                    INSERT INTO inspections (
                        inspection_id, asset_id, inspected_at, inspector_user_id,
                        method, ambient_temp_c, wellhead_temp_c, spill_detected,
                        spill_area_pct, spill_est_volume_bbl, notes, evidence_images
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['inspection_id'],
                    row['asset_id'],
                    row['inspected_at'],
                    row['inspector_user_id'],
                    row.get('method', ''),
                    row['ambient_temp_c'],
                    row['wellhead_temp_c'],
                    1 if row.get('spill_detected', False) else 0,
                    row.get('spill_area_pct'),
                    row.get('spill_est_volume_bbl'),
                    row.get('notes', ''),
                    json.dumps(row.get('evidence_images', []))
                ))
                inspections_count += 1
    
    # 3. Load maintenance.jsonl
    maintenance_path = well_dir / "maintenance.jsonl"
    maintenance_count = 0
    if maintenance_path.exists():
        with jsonlines.open(maintenance_path) as reader:
            for row in reader:
                # Parse cost data
                cost_data = row.get('cost_usd', {})
                if isinstance(cost_data, dict):
                    cost_labor = cost_data.get('labor', 0)
                    cost_parts = cost_data.get('parts', 0)
                    cost_total = cost_data.get('total', 0)
                else:
                    cost_labor = cost_parts = cost_total = 0
                
                cursor.execute("""
                    INSERT INTO maintenance (
                        maintenance_id, asset_id, started_at, completed_at,
                        maintenance_type, equipment_kind, issue, action_taken,
                        technician_user_id, contractor, downtime_hours,
                        cost_labor, cost_parts, cost_total,
                        triggered_by_inspection_id, report_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['maintenance_id'],
                    row['asset_id'],
                    row['started_at'],
                    row.get('completed_at'),
                    row['maintenance_type'],
                    row.get('equipment_kind', ''),
                    row['issue'],
                    row.get('action_taken', ''),
                    row.get('technician_user_id'),
                    row.get('contractor'),
                    row.get('downtime_hours', 0),
                    cost_labor,
                    cost_parts,
                    cost_total,
                    row.get('triggered_by_inspection_id'),
                    row.get('report_file')
                ))
                maintenance_count += 1
    
    # 4. Load context.jsonl
    context_path = well_dir / "context.jsonl"
    context_count = 0
    if context_path.exists():
        with jsonlines.open(context_path) as reader:
            for row in reader:
                cursor.execute("""
                    INSERT INTO context_notes (
                        note_id, asset_id, created_at, author_user_id,
                        note_type, inspection_id, text, valid_from, valid_to
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['note_id'],
                    row['asset_id'],
                    row['created_at'],
                    row['author_user_id'],
                    row['note_type'],
                    row.get('inspection_id'),
                    row['text'],
                    row.get('valid_from'),
                    row.get('valid_to')
                ))
                context_count += 1
    
    return {
        'equipment': equipment_count,
        'inspections': inspections_count,
        'maintenance': maintenance_count,
        'context': context_count
    }

def ingest_wells():
    """Main function to ingest all wells"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"📂 Scanning {SAMPLE_DATA}")
        well_dirs = sorted([d for d in SAMPLE_DATA.iterdir() if d.is_dir() and d.name.startswith('WELL-')])
        print(f"   Found {len(well_dirs)} wells")
        
        total_stats = {
            'wells': 0,
            'equipment': 0,
            'inspections': 0,
            'maintenance': 0,
            'context': 0
        }
        
        # Process in batches
        batch_size = 50
        for i, well_dir in enumerate(well_dirs, 1):
            asset_id = well_dir.name
            
            try:
                stats = ingest_well_data(well_dir, cursor)
                if stats:
                    total_stats['wells'] += 1
                    total_stats['equipment'] += stats['equipment']
                    total_stats['inspections'] += stats['inspections']
                    total_stats['maintenance'] += stats['maintenance']
                    total_stats['context'] += stats['context']
                    
                    if i % 10 == 0:
                        print(f"   Processed {i}/{len(well_dirs)} wells...")
                
            except Exception as e:
                print(f"   ❌ Error processing {asset_id}: {e}")
                continue
            
            # Commit in batches
            if i % batch_size == 0:
                conn.commit()
                print(f"   💾 Committed batch at {i} wells")
        
        # Final commit
        conn.commit()
        
        print(f"\n📊 Ingestion Summary:")
        print(f"   Wells: {total_stats['wells']}")
        print(f"   Equipment: {total_stats['equipment']}")
        print(f"   Inspections: {total_stats['inspections']}")
        print(f"   Maintenance: {total_stats['maintenance']}")
        print(f"   Context Notes: {total_stats['context']}")
        
        # Verify counts
        print("\n✅ Database Verification:")
        cursor.execute("SELECT COUNT(*) FROM wells")
        print(f"   Wells in DB: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM inspections")
        print(f"   Inspections in DB: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM maintenance")
        print(f"   Maintenance in DB: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM context_notes")
        print(f"   Context Notes in DB: {cursor.fetchone()[0]}")
        
        print("\n✅ Wells ingestion complete")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_wells()
