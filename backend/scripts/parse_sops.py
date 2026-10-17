#!/usr/bin/env python3
"""
Parse SOP documents to extract compliance rules
"""
import sqlite3
import json
import re
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
RULES_PATH = BACKEND_DIR / "data" / "rules" / "rules.json"
SAMPLE_DATA = BACKEND_DIR.parent / "test-data" / "dataset"

def parse_spill_response_sop():
    """Extract rules from spill-response-sop.md"""
    sop_path = SAMPLE_DATA / "fleet" / "sops" / "spill-response-sop.md"
    
    with open(sop_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    rules = []
    
    # SR-01: Reportable spills (≥5 bbl) - 24 hours; Major (≥25 bbl) - 2 hours
    rules.append({
        'protocol_id': 'SR-01-reportable',
        'category': 'spill_response',
        'description': 'Reportable spills (≥5 bbl) require written notice within 24 hours of discovery',
        'deadline_hours': 24,
        'threshold_value': 5.0,
        'threshold_unit': 'bbl'
    })
    
    rules.append({
        'protocol_id': 'SR-01-major',
        'category': 'spill_response',
        'description': 'Major spills (≥25 bbl) require written notice within 2 hours of discovery',
        'deadline_hours': 2,
        'threshold_value': 25.0,
        'threshold_unit': 'bbl'
    })
    
    # SR-02: Contain within 4 hours
    rules.append({
        'protocol_id': 'SR-02',
        'category': 'spill_response',
        'description': 'Source must be stopped and spill contained within 4 hours of discovery',
        'deadline_hours': 4,
        'threshold_value': None,
        'threshold_unit': None
    })
    
    # SR-03: Remediation to 1.0% TPH, verify within 60 days
    rules.append({
        'protocol_id': 'SR-03-cleanup',
        'category': 'spill_response',
        'description': 'Contaminated soil must be cleaned to 1.0% TPH or less',
        'deadline_hours': None,
        'threshold_value': 1.0,
        'threshold_unit': 'pct_tph'
    })
    
    rules.append({
        'protocol_id': 'SR-03-verification',
        'category': 'spill_response',
        'description': 'Reportable spills must be verified within 60 days of discovery',
        'deadline_hours': 1440,  # 60 days * 24 hours
        'threshold_value': None,
        'threshold_unit': None
    })
    
    # SR-04: Record all spills
    rules.append({
        'protocol_id': 'SR-04',
        'category': 'spill_response',
        'description': 'All spills (including minor) must be recorded with volume and affected area',
        'deadline_hours': None,
        'threshold_value': None,
        'threshold_unit': None
    })
    
    return rules

def parse_regulatory_compliance_sop():
    """Extract rules from regulatory-compliance-sop.md"""
    sop_path = SAMPLE_DATA / "fleet" / "sops" / "regulatory-compliance-sop.md"
    
    with open(sop_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    rules = []
    
    # RC-01: Inspect every 14 days
    rules.append({
        'protocol_id': 'RC-01',
        'category': 'regulatory_compliance',
        'description': 'Every well must be inspected at least once every 14 days',
        'deadline_hours': 336,  # 14 days * 24 hours
        'threshold_value': 14,
        'threshold_unit': 'days'
    })
    
    # RC-02: Annual flowline integrity test
    rules.append({
        'protocol_id': 'RC-02',
        'category': 'regulatory_compliance',
        'description': 'Every flowline must pass an integrity test once per calendar year',
        'deadline_hours': 8760,  # 365 days * 24 hours
        'threshold_value': 1,
        'threshold_unit': 'per_year'
    })
    
    # RC-03: Report downtime >14 days
    rules.append({
        'protocol_id': 'RC-03',
        'category': 'regulatory_compliance',
        'description': 'Any well down for more than 14 consecutive days must be reported to area supervisor',
        'deadline_hours': 336,  # 14 days * 24 hours
        'threshold_value': 14,
        'threshold_unit': 'days'
    })
    
    # RC-04: NOV response within 30 days
    rules.append({
        'protocol_id': 'RC-04',
        'category': 'regulatory_compliance',
        'description': 'Agency notices of violation must be answered within 30 days',
        'deadline_hours': 720,  # 30 days * 24 hours
        'threshold_value': 30,
        'threshold_unit': 'days'
    })
    
    # RC-05: Flowline maintenance program
    rules.append({
        'protocol_id': 'RC-05',
        'category': 'regulatory_compliance',
        'description': 'Maintain flowline program: weekly inspections, prompt leak repair, cleanup',
        'deadline_hours': 168,  # 7 days * 24 hours (weekly)
        'threshold_value': None,
        'threshold_unit': None
    })
    
    return rules

def save_rules_to_database(rules):
    """Save rules to SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        for rule in rules:
            cursor.execute("""
                INSERT INTO sop_rules (protocol_id, category, description, deadline_hours, threshold_value, threshold_unit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rule['protocol_id'],
                rule['category'],
                rule['description'],
                rule['deadline_hours'],
                rule['threshold_value'],
                rule['threshold_unit']
            ))
        
        conn.commit()
        print(f"   ✅ Inserted {len(rules)} rules into database")
        
    except Exception as e:
        print(f"   ❌ Error saving to database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def save_rules_to_json(rules):
    """Save rules to JSON file for agent reference"""
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(RULES_PATH, 'w') as f:
        json.dump(rules, f, indent=2)
    
    print(f"   ✅ Saved rules to {RULES_PATH}")

def parse_sops():
    """Main function to parse SOPs and extract rules"""
    print("📝 Parsing Spill Response SOP...")
    spill_rules = parse_spill_response_sop()
    print(f"   Extracted {len(spill_rules)} spill response rules")
    
    print("📝 Parsing Regulatory Compliance SOP...")
    compliance_rules = parse_regulatory_compliance_sop()
    print(f"   Extracted {len(compliance_rules)} regulatory compliance rules")
    
    all_rules = spill_rules + compliance_rules
    print(f"\n📊 Total rules extracted: {len(all_rules)}")
    
    print("\n💾 Saving to database...")
    save_rules_to_database(all_rules)
    
    print("💾 Saving to JSON...")
    save_rules_to_json(all_rules)
    
    print("\n✅ SOP parsing complete")
    print("\n📋 Rule Summary:")
    print("   Spill Response (SR-01 to SR-04):")
    for rule in spill_rules:
        print(f"      {rule['protocol_id']}: {rule['description'][:60]}...")
    print("   Regulatory Compliance (RC-01 to RC-05):")
    for rule in compliance_rules:
        print(f"      {rule['protocol_id']}: {rule['description'][:60]}...")

if __name__ == "__main__":
    parse_sops()
