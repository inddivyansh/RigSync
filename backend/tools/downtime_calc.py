"""
Downtime Calculator Tool - Calculate well downtime using production rules
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"

class DowntimeCalculatorTool:
    """Calculate well downtime based on production temperature threshold"""
    
    def __init__(self):
        """Initialize with well type thresholds"""
        self.thresholds = self._load_thresholds()
    
    def _load_thresholds(self) -> Dict[str, float]:
        """Load production thresholds from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT well_type_code, production_threshold_c 
            FROM well_types
        """)
        thresholds = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return thresholds
    
    def _is_producing(self, wellhead_temp: float, ambient_temp: float, threshold: float) -> bool:
        """Check if well is producing based on temperature difference"""
        temp_diff = wellhead_temp - ambient_temp
        return temp_diff >= threshold
    
    def calculate_downtime(
        self,
        asset_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Calculate downtime for a well in date range
        
        Args:
            asset_id: Well identifier (e.g., WELL-0001)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary with downtime statistics and details
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get well type
            cursor.execute("""
                SELECT well_type FROM wells WHERE asset_id = ?
            """, (asset_id,))
            well = cursor.fetchone()
            
            if not well:
                return {'error': f'Well {asset_id} not found'}
            
            well_type = well['well_type']
            threshold = self.thresholds.get(well_type, 15.0)
            
            # Get inspections in date range
            cursor.execute("""
                SELECT inspection_id, inspected_at, 
                       wellhead_temp_c, ambient_temp_c, notes
                FROM inspections
                WHERE asset_id = ?
                AND date(inspected_at) >= date(?)
                AND date(inspected_at) <= date(?)
                ORDER BY inspected_at
            """, (asset_id, start_date, end_date))
            
            inspections = cursor.fetchall()
            
            # Get context notes for reasons
            cursor.execute("""
                SELECT note_type, text, valid_from, valid_to
                FROM context_notes
                WHERE asset_id = ?
                AND (
                    (date(valid_from) <= date(?) AND (valid_to IS NULL OR date(valid_to) >= date(?)))
                    OR
                    (date(valid_from) >= date(?) AND date(valid_from) <= date(?))
                )
            """, (asset_id, end_date, start_date, start_date, end_date))
            
            context_notes = {note['valid_from']: note['text'] for note in cursor.fetchall()}
            
            conn.close()
            
            # Calculate downtime
            total_downtime_days = 0
            producing_weeks = 0
            non_producing_weeks = 0
            missed_weeks = 0
            details = []
            
            prev_date = None
            for inspection in inspections:
                date = inspection['inspected_at'][:10]
                wellhead_temp = inspection['wellhead_temp_c']
                ambient_temp = inspection['ambient_temp_c']
                
                temp_diff = wellhead_temp - ambient_temp
                is_producing = self._is_producing(wellhead_temp, ambient_temp, threshold)
                
                # Check for context note explaining status
                reason = None
                for note_date, note_text in context_notes.items():
                    if note_date and note_date <= date:
                        reason = note_text
                        break
                
                if is_producing:
                    producing_weeks += 1
                else:
                    non_producing_weeks += 1
                    total_downtime_days += 7  # Weekly inspection = 7 days
                
                details.append({
                    'inspection_id': inspection['inspection_id'],
                    'date': date,
                    'is_producing': is_producing,
                    'temp_diff': round(temp_diff, 1),
                    'threshold': threshold,
                    'wellhead_temp': wellhead_temp,
                    'ambient_temp': ambient_temp,
                    'reason': reason or inspection['notes'] or None
                })
                
                # Check for missed inspections (gap > 14 days)
                if prev_date:
                    prev_dt = datetime.fromisoformat(prev_date)
                    curr_dt = datetime.fromisoformat(date)
                    gap_days = (curr_dt - prev_dt).days
                    if gap_days > 14:
                        missed_weeks += (gap_days - 7) // 7
                
                prev_date = date
            
            return {
                'asset_id': asset_id,
                'well_type': well_type,
                'threshold_c': threshold,
                'total_downtime_days': total_downtime_days,
                'producing_weeks': producing_weeks,
                'non_producing_weeks': non_producing_weeks,
                'missed_weeks': missed_weeks,
                'total_inspections': len(inspections),
                'details': details
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'downtime_calc',
            'description': 'Calculate well downtime using production temperature threshold. Returns producing/non-producing weeks and reasons.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'asset_id': {
                        'type': 'string',
                        'description': 'Well identifier (e.g., WELL-0001)'
                    },
                    'start_date': {
                        'type': 'string',
                        'description': 'Start date in YYYY-MM-DD format'
                    },
                    'end_date': {
                        'type': 'string',
                        'description': 'End date in YYYY-MM-DD format'
                    }
                },
                'required': ['asset_id', 'start_date', 'end_date']
            }
        }

# Tool instance
downtime_calc_tool = DowntimeCalculatorTool()


def calculate_downtime(well_id: str, db_path: str = None, start_date: str = "2026-01-01", end_date: str = "2027-01-15") -> Dict[str, Any]:
    """Calculate downtime helper function for agent."""
    tool = downtime_calc_tool
    return tool.calculate_downtime(well_id, start_date, end_date)
