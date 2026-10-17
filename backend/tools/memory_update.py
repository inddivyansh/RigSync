"""
Memory Update Tool - Record corrections with provenance
"""
import json
import time
import random
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

BACKEND_DIR = Path(__file__).parent.parent
MEMORY_DIR = BACKEND_DIR / "data" / "memory"

class MemoryUpdateTool:
    """Record data corrections with full provenance"""
    
    def __init__(self):
        """Initialize memory directory"""
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    
    def _save_correction(self, file_path: Path, correction: Dict):
        """Append correction to JSON file"""
        corrections = []
        
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    corrections = json.load(f)
                    if not isinstance(corrections, list):
                        corrections = []
            except:
                corrections = []
        
        corrections.append(correction)
        
        with open(file_path, 'w') as f:
            json.dump(corrections, f, indent=2)
    
    def record_correction(
        self,
        user_id: str,
        asset_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        scope: str = 'well'
    ) -> Dict[str, Any]:
        """
        Record a data correction
        
        Args:
            user_id: User making the correction
            asset_id: Well identifier (or 'global' for global rules)
            field: Field being corrected (e.g., 'wellhead_temp_c')
            old_value: Original value
            new_value: Corrected value
            reason: Reason for correction
            scope: 'user', 'well', or 'global'
            
        Returns:
            Dictionary with correction_id and status
        """
        try:
            # Generate unique correction ID
            correction_id = f"COR-{int(time.time())}-{random.randint(1000, 9999)}"
            
            # Create correction object
            correction = {
                'correction_id': correction_id,
                'created_at': datetime.now().isoformat(),
                'author_user_id': user_id,
                'scope': scope,
                'entity_id': asset_id if scope != 'global' else 'global',
                'field': field,
                'old_value': old_value,
                'new_value': new_value,
                'reason': reason,
                'valid_from': datetime.now().isoformat(),
                'valid_to': None
            }
            
            # Save to appropriate file
            if scope == 'user':
                file_path = MEMORY_DIR / f"user_{user_id}.json"
            elif scope == 'well':
                file_path = MEMORY_DIR / f"well_{asset_id}.json"
            else:  # global
                file_path = MEMORY_DIR / "global_rules.json"
            
            self._save_correction(file_path, correction)
            
            # Check for conflicts (import here to avoid circular dependency)
            from .conflict_detect import conflict_detect_tool
            conflicts = conflict_detect_tool.detect_conflicts(asset_id, field, new_value)
            
            return {
                'correction_id': correction_id,
                'status': 'recorded',
                'conflicts': conflicts if conflicts else None,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            return {
                'correction_id': None,
                'status': 'error',
                'error': str(e),
                'conflicts': None
            }
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'memory_update',
            'description': 'Record a data correction with full provenance (who, when, why). Triggers conflict detection.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'user_id': {
                        'type': 'string',
                        'description': 'User making the correction'
                    },
                    'asset_id': {
                        'type': 'string',
                        'description': 'Well identifier or "global" for global rules'
                    },
                    'field': {
                        'type': 'string',
                        'description': 'Field being corrected (e.g., wellhead_temp_c, production_threshold_c)'
                    },
                    'old_value': {
                        'description': 'Original value'
                    },
                    'new_value': {
                        'description': 'Corrected value'
                    },
                    'reason': {
                        'type': 'string',
                        'description': 'Reason for correction'
                    },
                    'scope': {
                        'type': 'string',
                        'enum': ['user', 'well', 'global'],
                        'description': 'Scope of correction',
                        'default': 'well'
                    }
                },
                'required': ['user_id', 'asset_id', 'field', 'old_value', 'new_value', 'reason']
            }
        }

# Tool instance
memory_update_tool = MemoryUpdateTool()


def update_memory(user_id: str, asset_id: str, field: str, old_value: Any, new_value: Any, reason: str, scope: str = 'well') -> Dict[str, Any]:
    """Record memory correction helper function for agent."""
    tool = memory_update_tool
    return tool.record_correction(user_id, asset_id, field, old_value, new_value, reason, scope)
