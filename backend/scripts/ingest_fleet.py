#!/usr/bin/env python3
"""
Ingest fleet metadata: areas, teams, users, and well types with production thresholds
"""
import sqlite3
import json
import re
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
SAMPLE_DATA = BACKEND_DIR.parent / "test-data" / "dataset"

def extract_production_threshold(manual_path):
    """Extract production threshold from well-type manual"""
    with open(manual_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for production temperature rule section
    # T200: "**15 °C above ambient**" or "at least **15 °C above ambient**"
    # T350: "at least **20 °C above ambient**"
    patterns = [
        r'\*\*(\d+)\s*°?C\s+above',
        r'at\s+least\s+\*\*(\d+)\s*°?C\s+above',
        r'(\d+)\s*°C\s+above\s+ambient'
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def extract_temp_alarm(manual_path):
    """Extract temperature alarm threshold"""
    with open(manual_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for "at or below XX °C" - try multiple patterns
    patterns = [
        r'at\s+or\s+below\s+\*\*(\d+)\s*°C\*\*',
        r'stay\s+\*\*at\s+or\s+below\s+(\d+)\s*°C\*\*',
        r'below\s+(\d+)\s*°C'
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
    return None

def extract_max_pressure(manual_path):
    """Extract maximum pressure from manual"""
    with open(manual_path, 'r') as f:
        content = f.read()
    
    # Look for pressure in psi
    pattern = r'(\d+[,\d]*)\s*psi'
    matches = re.findall(pattern, content)
    if matches:
        # Get the largest value (likely max pressure)
        pressures = [int(m.replace(',', '')) for m in matches]
        return max(pressures)
    return None

def ingest_fleet_data():
    """Ingest areas, teams, users, and well types"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Load areas.json
        areas_path = SAMPLE_DATA / "fleet" / "areas.json"
        print(f"📂 Loading {areas_path}")
        with open(areas_path, 'r') as f:
            fleet_data = json.load(f)
        
        # Insert teams
        print("📝 Inserting teams...")
        for team in fleet_data['teams']:
            cursor.execute("""
                INSERT INTO teams (team_id, name, lead_user_id)
                VALUES (?, ?, ?)
            """, (team['team_id'], team['name'], team['lead_user_id']))
        print(f"   ✅ Inserted {len(fleet_data['teams'])} teams")
        
        # Insert areas
        print("📝 Inserting areas...")
        for area in fleet_data['areas']:
            cursor.execute("""
                INSERT INTO areas (area_id, name, team_id, center_lat, center_lon)
                VALUES (?, ?, ?, ?, ?)
            """, (
                area['area_id'],
                area['name'],
                area['team_id'],
                area['center']['lat'],
                area['center']['lon']
            ))
        print(f"   ✅ Inserted {len(fleet_data['areas'])} areas")
        
        # Load users.json
        users_path = SAMPLE_DATA / "fleet" / "users.json"
        print(f"📂 Loading {users_path}")
        with open(users_path, 'r') as f:
            users_data = json.load(f)
        
        # Insert users
        print("📝 Inserting users...")
        for user in users_data['users']:
            cursor.execute("""
                INSERT INTO users (user_id, name, role, team_id)
                VALUES (?, ?, ?, ?)
            """, (user['user_id'], user['name'], user['role'], user['team_id']))
        print(f"   ✅ Inserted {len(users_data['users'])} users")
        
        # Parse well-type manuals
        print("📝 Parsing well-type manuals...")
        well_types_dir = SAMPLE_DATA / "fleet" / "well-types"
        
        # T200 Manual
        t200_path = well_types_dir / "T200.md"
        print(f"   📄 Parsing {t200_path.name}")
        t200_threshold = extract_production_threshold(t200_path)
        t200_alarm = extract_temp_alarm(t200_path)
        t200_pressure = extract_max_pressure(t200_path)
        print(f"      T200 threshold: {t200_threshold}°C, alarm: {t200_alarm}°C, pressure: {t200_pressure} psi")
        
        cursor.execute("""
            INSERT INTO well_types (well_type_code, name, production_threshold_c, temp_alarm_c, max_pressure_psi)
            VALUES (?, ?, ?, ?, ?)
        """, ('T200', 'T200 Rod-Lift Oil Well', t200_threshold, t200_alarm, t200_pressure))
        
        # T350 Manual
        t350_path = well_types_dir / "T350.md"
        print(f"   📄 Parsing {t350_path.name}")
        t350_threshold = extract_production_threshold(t350_path)
        t350_alarm = extract_temp_alarm(t350_path)
        t350_pressure = extract_max_pressure(t350_path)
        print(f"      T350 threshold: {t350_threshold}°C, alarm: {t350_alarm}°C, pressure: {t350_pressure} psi")
        
        cursor.execute("""
            INSERT INTO well_types (well_type_code, name, production_threshold_c, temp_alarm_c, max_pressure_psi)
            VALUES (?, ?, ?, ?, ?)
        """, ('T350', 'T350 Deep Rod-Lift Oil Well', t350_threshold, t350_alarm, t350_pressure))
        
        print(f"   ✅ Inserted 2 well types")
        
        conn.commit()
        
        # Verify
        print("\n📊 Verification:")
        cursor.execute("SELECT COUNT(*) FROM teams")
        print(f"   Teams: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM areas")
        print(f"   Areas: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM users")
        print(f"   Users: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM well_types")
        print(f"   Well Types: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT well_type_code, production_threshold_c, temp_alarm_c, max_pressure_psi FROM well_types")
        print("\n   Well Type Details:")
        for row in cursor.fetchall():
            print(f"      {row[0]}: threshold={row[1]}°C, alarm={row[2]}°C, pressure={row[3]} psi")
        
        print("\n✅ Fleet data ingestion complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_fleet_data()
