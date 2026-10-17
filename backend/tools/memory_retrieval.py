"""
Memory Retrieval Tool - Fetch corrections and conversation history
"""
import json
from pathlib import Path
from typing import Dict, List, Any

BACKEND_DIR = Path(__file__).parent.parent
MEMORY_DIR = BACKEND_DIR / "data" / "memory"

class MemoryRetrievalTool:
    """Retrieve corrections and context from memory"""
    
    def __init__(self):
        """Initialize memory directory"""
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_corrections(self, file_path: Path) -> List[Dict]:
        """Load corrections from JSON file"""
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    
    def get_context(
        self,
        user_id: str,
        asset_id: str = None,
        scope: str = 'all'
    ) -> Dict[str, Any]:
        """
        Retrieve corrections and conversation history
        
        Args:
            user_id: User identifier
            asset_id: Well identifier (optional)
            scope: Scope filter - 'user', 'well', 'global', or 'all'
            
        Returns:
            Dictionary with corrections and conversation history
        """
        try:
            corrections = []
            
            # Load user-scoped corrections
            if scope in ['user', 'all']:
                user_file = MEMORY_DIR / f"user_{user_id}.json"
                user_corrections = self._load_corrections(user_file)
                corrections.extend([{**c, 'source': 'user'} for c in user_corrections])
            
            # Load well-scoped corrections
            if scope in ['well', 'all'] and asset_id:
                well_file = MEMORY_DIR / f"well_{asset_id}.json"
                well_corrections = self._load_corrections(well_file)
                corrections.extend([{**c, 'source': 'well'} for c in well_corrections])
            
            # Load global corrections
            if scope in ['global', 'all']:
                global_file = MEMORY_DIR / "global_rules.json"
                global_corrections = self._load_corrections(global_file)
                corrections.extend([{**c, 'source': 'global'} for c in global_corrections])
            
            # Load conversation history
            history = []
            history_file = MEMORY_DIR / f"user_{user_id}_history.jsonl"
            if history_file.exists():
                try:
                    import jsonlines
                    with jsonlines.open(history_file) as reader:
                        for entry in reader:
                            history.append(entry)
                        # Get last 10 messages
                        history = history[-10:] if len(history) > 10 else history
                except:
                    pass
            
            return {
                'corrections': corrections,
                'conversation_history': history,
                'total_corrections': len(corrections)
            }
            
        except Exception as e:
            return {'error': str(e), 'corrections': [], 'conversation_history': []}
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'memory_retrieval',
            'description': 'Fetch data corrections and conversation history. Use before answering to check for user/well/global corrections.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'user_id': {
                        'type': 'string',
                        'description': 'User identifier'
                    },
                    'asset_id': {
                        'type': 'string',
                        'description': 'Well identifier (optional)',
                        'default': None
                    },
                    'scope': {
                        'type': 'string',
                        'enum': ['user', 'well', 'global', 'all'],
                        'description': 'Scope filter for corrections',
                        'default': 'all'
                    }
                },
                'required': ['user_id']
            }
        }

# Tool instance
memory_retrieval_tool = MemoryRetrievalTool()
