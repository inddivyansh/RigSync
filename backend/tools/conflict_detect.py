"""
Conflict Detection Tool - Find disagreements between data sources
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
MEMORY_DIR = BACKEND_DIR / "data" / "memory"

class ConflictDetectTool:
    """Detect conflicts between corrections and existing data"""
    
    def detect_conflicts(
        self,
        asset_id: str,
        field: str,
        new_value: Any
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts for a new value
        
        Args:
            asset_id: Well identifier
            field: Field being changed
            new_value: New value to check
            
        Returns:
            List of conflicts with severity
        """
        conflicts = []
        
        try:
            # Check against latest SQLite data
            conflicts.extend(self._check_database_conflicts(asset_id, field, new_value))
            
            # Check against existing corrections
            conflicts.extend(self._check_memory_conflicts(asset_id, field, new_value))
            
            # Check against context notes
            conflicts.extend(self._check_context_conflicts(asset_id, field, new_value))
            
        except Exception as e:
            conflicts.append({
                'conflict_type': 'error',
                'source': 'system',
                'severity': 'high',
                'details': str(e)
            })
        
        return conflicts
    
    def _check_database_conflicts(self, asset_id: str, field: str, new_value: Any) -> List[Dict]:
        """Check conflicts with database records"""
        conflicts = []
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check inspections for temperature fields
            if field in ['wellhead_temp_c', 'ambient_temp_c']:
                cursor.execute("""
                    SELECT inspection_id, inspected_at, wellhead_temp_c, ambient_temp_c, notes
                    FROM inspections
                    WHERE asset_id = ?
                    ORDER BY inspected_at DESC
                    LIMIT 1
                """, (asset_id,))
                
                inspection = cursor.fetchone()
                if inspection:
                    existing_value = inspection[field]
                    
                    # Check if there's a significant difference
                    if abs(float(new_value) - existing_value) > 10:
                        # Check inspector notes for contradictions
                        if inspection['notes'] and any(word in inspection['notes'].lower() for word in ['not moving', 'stopped', 'shut in', 'idle']):
                            conflicts.append({
                                'conflict_type': 'database_observation',
                                'source': f"Inspection {inspection['inspection_id']}",
                                'source_id': inspection['inspection_id'],
                                'existing_value': existing_value,
                                'new_value': new_value,
                                'severity': 'high',
                                'details': f"Inspector noted: {inspection['notes']}"
                            })
            
            conn.close()
            
        except Exception as e:
            pass
        
        return conflicts
    
    def _check_memory_conflicts(self, asset_id: str, field: str, new_value: Any) -> List[Dict]:
        """Check conflicts with existing corrections"""
        conflicts = []
        
        try:
            import json
            
            # Check well-scoped corrections
            well_file = MEMORY_DIR / f"well_{asset_id}.json"
            if well_file.exists():
                with open(well_file, 'r') as f:
                    corrections = json.load(f)
                    
                    for correction in corrections:
                        if correction['field'] == field and correction.get('valid_to') is None:
                            if correction['new_value'] != new_value:
                                conflicts.append({
                                    'conflict_type': 'previous_correction',
                                    'source': f"Correction {correction['correction_id']}",
                                    'source_id': correction['correction_id'],
                                    'existing_value': correction['new_value'],
                                    'new_value': new_value,
                                    'severity': 'low',
                                    'details': f"Previous correction by {correction['author_user_id']}: {correction['reason']}"
                                })
        
        except Exception as e:
            pass
        
        return conflicts
    
    def _check_context_conflicts(self, asset_id: str, field: str, new_value: Any) -> List[Dict]:
        """Check conflicts with context notes"""
        conflicts = []
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get recent context notes
            cursor.execute("""
                SELECT note_id, text, note_type, author_user_id, created_at
                FROM context_notes
                WHERE asset_id = ?
                AND (valid_to IS NULL OR date(valid_to) >= date('now'))
                ORDER BY created_at DESC
                LIMIT 5
            """, (asset_id,))
            
            notes = cursor.fetchall()
            
            # Check for contradictions based on field
            if field == 'wellhead_temp_c' and float(new_value) > 40:
                # High temperature - check for shutdown notes
                for note in notes:
                    if any(word in note['text'].lower() for word in ['shut in', 'shutdown', 'stopped', 'not producing', 'down']):
                        conflicts.append({
                            'conflict_type': 'context_note',
                            'source': f"Context note {note['note_id']}",
                            'source_id': note['note_id'],
                            'existing_value': note['text'],
                            'new_value': new_value,
                            'severity': 'medium',
                            'details': f"Operator note ({note['author_user_id']}): {note['text']}"
                        })
            
            conn.close()
            
        except Exception as e:
            pass
        
        return conflicts
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'conflict_detect',
            'description': 'Detect conflicts between new value and existing data (database, corrections, context notes). Returns severity rating.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'asset_id': {
                        'type': 'string',
                        'description': 'Well identifier'
                    },
                    'field': {
                        'type': 'string',
                        'description': 'Field being changed'
                    },
                    'new_value': {
                        'description': 'New value to check for conflicts'
                    }
                },
                'required': ['asset_id', 'field', 'new_value']
            }
        }

# Tool instance
conflict_detect_tool = ConflictDetectTool()
