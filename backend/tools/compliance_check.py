"""
Compliance Check Tool - Detect SOP rule violations
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
RULES_PATH = BACKEND_DIR / "data" / "rules" / "rules.json"

class ComplianceCheckTool:
    """Check for SOP rule violations"""
    
    def __init__(self):
        """Load rules from JSON"""
        with open(RULES_PATH, 'r') as f:
            self.rules = json.load(f)
        
        # Index rules by protocol ID
        self.rules_by_id = {r['protocol_id']: r for r in self.rules}
    
    def _check_rc01(self, asset_id: str, start_date: str, end_date: str, cursor) -> List[Dict]:
        """RC-01: Inspect every 14 days"""
        cursor.execute("""
            SELECT inspected_at 
            FROM inspections 
            WHERE asset_id = ?
            AND date(inspected_at) >= date(?)
            AND date(inspected_at) <= date(?)
            ORDER BY inspected_at
        """, (asset_id, start_date, end_date))
        
        inspections = [row[0] for row in cursor.fetchall()]
        violations = []
        
        for i in range(len(inspections) - 1):
            date1 = datetime.fromisoformat(inspections[i].replace('Z', '+00:00'))
            date2 = datetime.fromisoformat(inspections[i+1].replace('Z', '+00:00'))
            gap_days = (date2 - date1).days
            
            if gap_days > 14:
                violations.append({
                    'rule_id': 'RC-01',
                    'protocol_id': 'RC-01',
                    'violated': True,
                    'violation_date': inspections[i],
                    'details': f'Gap of {gap_days} days between inspections (limit: 14 days)',
                    'deadline_missed_by_hours': (gap_days - 14) * 24
                })
        
        return violations
    
    def _check_rc02(self, asset_id: str, start_date: str, end_date: str, cursor) -> List[Dict]:
        """RC-02: Annual flowline integrity test"""
        cursor.execute("""
            SELECT started_at 
            FROM maintenance 
            WHERE asset_id = ?
            AND issue LIKE '%flowline integrity test%'
            AND date(started_at) >= date(?)
            AND date(started_at) <= date(?)
            ORDER BY started_at
        """, (asset_id, start_date, end_date))
        
        tests = cursor.fetchall()
        
        # Check if test exists in the date range
        start_year = datetime.fromisoformat(start_date).year
        end_year = datetime.fromisoformat(end_date).year
        
        violations = []
        for year in range(start_year, end_year + 1):
            year_tests = [t for t in tests if datetime.fromisoformat(t[0]).year == year]
            if not year_tests:
                violations.append({
                    'rule_id': 'RC-02',
                    'protocol_id': 'RC-02',
                    'violated': True,
                    'violation_date': f'{year}-12-31',
                    'details': f'No annual flowline integrity test found for {year}',
                    'deadline_missed_by_hours': None
                })
        
        return violations
    
    def _check_sr01(self, asset_id: str, start_date: str, end_date: str, cursor) -> List[Dict]:
        """SR-01: Reportable spills - report within 24h (≥5 bbl) or 2h (≥25 bbl)"""
        # Get spills
        cursor.execute("""
            SELECT inspection_id, inspected_at, spill_est_volume_bbl
            FROM inspections
            WHERE asset_id = ?
            AND spill_detected = 1
            AND spill_est_volume_bbl >= 5
            AND date(inspected_at) >= date(?)
            AND date(inspected_at) <= date(?)
        """, (asset_id, start_date, end_date))
        
        spills = cursor.fetchall()
        violations = []
        
        for spill in spills:
            inspection_id, inspected_at, volume = spill
            
            # Check if maintenance was started within deadline
            deadline_hours = 2 if volume >= 25 else 24
            
            cursor.execute("""
                SELECT started_at
                FROM maintenance
                WHERE asset_id = ?
                AND triggered_by_inspection_id = ?
            """, (asset_id, inspection_id))
            
            maintenance = cursor.fetchone()
            
            if maintenance:
                spill_time = datetime.fromisoformat(inspected_at.replace('Z', '+00:00'))
                response_time = datetime.fromisoformat(maintenance[0].replace('Z', '+00:00'))
                hours_to_response = (response_time - spill_time).total_seconds() / 3600
                
                if hours_to_response > deadline_hours:
                    violations.append({
                        'rule_id': 'SR-01',
                        'protocol_id': 'SR-01-major' if volume >= 25 else 'SR-01-reportable',
                        'violated': True,
                        'violation_date': inspected_at,
                        'details': f'Spill {volume} bbl reported {hours_to_response:.1f}h after discovery (limit: {deadline_hours}h)',
                        'deadline_missed_by_hours': hours_to_response - deadline_hours
                    })
            else:
                violations.append({
                    'rule_id': 'SR-01',
                    'protocol_id': 'SR-01-major' if volume >= 25 else 'SR-01-reportable',
                    'violated': True,
                    'violation_date': inspected_at,
                    'details': f'Spill {volume} bbl detected but no maintenance record found',
                    'deadline_missed_by_hours': None
                })
        
        return violations
    
    def _check_sr02(self, asset_id: str, start_date: str, end_date: str, cursor) -> List[Dict]:
        """SR-02: Contain spill within 4 hours"""
        cursor.execute("""
            SELECT i.inspection_id, i.inspected_at, i.spill_est_volume_bbl,
                   m.started_at
            FROM inspections i
            LEFT JOIN maintenance m ON i.inspection_id = m.triggered_by_inspection_id
            WHERE i.asset_id = ?
            AND i.spill_detected = 1
            AND date(i.inspected_at) >= date(?)
            AND date(i.inspected_at) <= date(?)
        """, (asset_id, start_date, end_date))
        
        spills = cursor.fetchall()
        violations = []
        
        for spill in spills:
            inspection_id, inspected_at, volume, started_at = spill
            
            if started_at:
                spill_time = datetime.fromisoformat(inspected_at.replace('Z', '+00:00'))
                containment_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                hours_to_containment = (containment_time - spill_time).total_seconds() / 3600
                
                if hours_to_containment > 4:
                    violations.append({
                        'rule_id': 'SR-02',
                        'protocol_id': 'SR-02',
                        'violated': True,
                        'violation_date': inspected_at,
                        'details': f'Spill contained {hours_to_containment:.1f}h after discovery (limit: 4h)',
                        'deadline_missed_by_hours': hours_to_containment - 4
                    })
        
        return violations
    
    def check_violations(
        self,
        asset_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Check for SOP violations
        
        Args:
            asset_id: Well identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of violations with details
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            violations = []
            
            # Check each rule
            violations.extend(self._check_rc01(asset_id, start_date, end_date, cursor))
            violations.extend(self._check_rc02(asset_id, start_date, end_date, cursor))
            violations.extend(self._check_sr01(asset_id, start_date, end_date, cursor))
            violations.extend(self._check_sr02(asset_id, start_date, end_date, cursor))
            
            conn.close()
            
            # Add non-violated rules
            checked_rules = set(v['protocol_id'] for v in violations)
            for rule in self.rules:
                if rule['protocol_id'] not in checked_rules:
                    violations.append({
                        'rule_id': rule['protocol_id'],
                        'protocol_id': rule['protocol_id'],
                        'violated': False,
                        'violation_date': None,
                        'details': f"Compliant with {rule['description']}",
                        'deadline_missed_by_hours': None
                    })
            
            return violations
            
        except Exception as e:
            return [{'error': str(e)}]
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'compliance_check',
            'description': 'Check SOP rule violations for a well. Returns list of violations with deadlines missed.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'asset_id': {
                        'type': 'string',
                        'description': 'Well identifier'
                    },
                    'start_date': {
                        'type': 'string',
                        'description': 'Start date (YYYY-MM-DD)'
                    },
                    'end_date': {
                        'type': 'string',
                        'description': 'End date (YYYY-MM-DD)'
                    }
                },
                'required': ['asset_id', 'start_date', 'end_date']
            }
        }

# Tool instance
compliance_check_tool = ComplianceCheckTool()
