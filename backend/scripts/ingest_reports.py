#!/usr/bin/env python3
"""
Parse maintenance report markdown files and extract structured data
"""
import sqlite3
import json
import re
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
SAMPLE_DATA = BACKEND_DIR.parent / "test-data" / "dataset" / "assets"

def extract_root_cause(content):
    """Extract root cause from markdown report"""
    match = re.search(r'##\s+Root\s+cause\s*\n\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_compliance_table(content):
    """Extract compliance check table and convert to JSON"""
    match = re.search(r'##\s+Compliance\s+check\s*\n\s*\n\|.*?\n\|.*?\n((?:\|.*?\n)+)', content, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    
    table_text = match.group(1)
    rows = [line.strip() for line in table_text.split('\n') if line.strip().startswith('|')]
    
    compliance_results = []
    for row in rows:
        cells = [cell.strip() for cell in row.split('|')[1:-1]]
        if len(cells) >= 3:
            compliance_results.append({
                'protocol_id': cells[0].strip(),
                'result': cells[1].strip(),
                'detail': cells[2].strip() if len(cells) > 2 else ''
            })
    
    return compliance_results if compliance_results else None

def extract_parts_cost(content):
    """Extract parts and cost from table"""
    match = re.search(r'##\s+Parts\s+and\s+cost\s*\n\s*\n\|.*?\n\|.*?\n((?:\|.*?\n)+)', content, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    
    table_text = match.group(1)
    
    # Look for Total row
    total_match = re.search(r'\|\s*\*\*Total\*\*\s*\|\s*\*\*([0-9,]+)\*\*', table_text)
    if total_match:
        total = int(total_match.group(1).replace(',', ''))
        
        # Try to extract labor and parts
        labor_match = re.search(r'\|\s*Labour.*?\|\s*([0-9,]+)', table_text)
        parts_match = re.search(r'\|\s*(?:Line pipe|Absorbents|Soil hauling|Parts).*?\|\s*([0-9,]+)', table_text)
        
        labor = int(labor_match.group(1).replace(',', '')) if labor_match else 0
        parts = int(parts_match.group(1).replace(',', '')) if parts_match else total - labor
        
        return {
            'labor': labor,
            'parts': parts,
            'total': total
        }
    
    return None

def parse_report(report_path):
    """Parse a single maintenance report"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract maintenance ID from filename
    maintenance_id = report_path.stem  # e.g., MNT-0001-002
    
    root_cause = extract_root_cause(content)
    compliance_json = extract_compliance_table(content)
    parts_json = extract_parts_cost(content)
    
    return {
        'maintenance_id': maintenance_id,
        'root_cause': root_cause,
        'compliance_json': json.dumps(compliance_json) if compliance_json else None,
        'parts_json': json.dumps(parts_json) if parts_json else None,
        'report_path': str(report_path.relative_to(SAMPLE_DATA.parent))
    }

def ingest_reports():
    """Main function to parse all maintenance reports"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"📂 Scanning for maintenance reports...")
        report_count = 0
        processed_count = 0
        
        # Scan all well directories
        for well_dir in sorted(SAMPLE_DATA.iterdir()):
            if not well_dir.is_dir() or not well_dir.name.startswith('WELL-'):
                continue
            
            reports_dir = well_dir / "maintenance-reports"
            if not reports_dir.exists():
                continue
            
            # Process each markdown file
            for report_file in reports_dir.glob("*.md"):
                report_count += 1
                
                try:
                    report_data = parse_report(report_file)
                    
                    cursor.execute("""
                        INSERT INTO maintenance_reports (
                            maintenance_id, root_cause, compliance_json, parts_json, report_path
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        report_data['maintenance_id'],
                        report_data['root_cause'],
                        report_data['compliance_json'],
                        report_data['parts_json'],
                        report_data['report_path']
                    ))
                    
                    processed_count += 1
                    
                    if processed_count % 100 == 0:
                        print(f"   Processed {processed_count} reports...")
                        conn.commit()
                    
                except Exception as e:
                    print(f"   ⚠️  Error parsing {report_file.name}: {e}")
                    continue
        
        conn.commit()
        
        print(f"\n📊 Report Parsing Summary:")
        print(f"   Reports found: {report_count}")
        print(f"   Successfully parsed: {processed_count}")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM maintenance_reports")
        db_count = cursor.fetchone()[0]
        print(f"   Reports in database: {db_count}")
        
        # Sample check
        cursor.execute("""
            SELECT maintenance_id, root_cause 
            FROM maintenance_reports 
            WHERE root_cause IS NOT NULL 
            LIMIT 3
        """)
        print(f"\n   Sample parsed reports:")
        for row in cursor.fetchall():
            print(f"      {row[0]}: {row[1][:60]}...")
        
        print("\n✅ Maintenance reports ingestion complete")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_reports()
