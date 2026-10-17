"""
SQL Query Tool - Execute safe SQL queries on oilwells database
"""
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Any

BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"

class SQLQueryTool:
    """Execute SQL queries with safety checks"""
    
    # Allowed SQL keywords
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER',
        'ON', 'AND', 'OR', 'IN', 'NOT', 'IS', 'NULL', 'LIKE',
        'GROUP', 'BY', 'ORDER', 'ASC', 'DESC', 'LIMIT', 'OFFSET',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'HAVING', 'AS', 'DISTINCT'
    }
    
    # Blocked keywords (DML/DDL)
    BLOCKED_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
        'TRUNCATE', 'REPLACE', 'ATTACH', 'DETACH'
    }
    
    def __init__(self):
        """Initialize tool with database connection"""
        self.well_types = self._load_well_types()
    
    def _load_well_types(self) -> Dict[str, float]:
        """Load production thresholds for well types"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT well_type_code, production_threshold_c FROM well_types")
        thresholds = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return thresholds
    
    def _validate_query(self, query: str) -> None:
        """Validate query for safety"""
        query_upper = query.upper()
        
        # Check for blocked keywords
        for keyword in self.BLOCKED_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                raise ValueError(f"Blocked keyword detected: {keyword}")
        
        # Must start with SELECT
        if not query_upper.strip().startswith('SELECT'):
            raise ValueError("Query must start with SELECT")
    
    def execute(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute SQL query with parameterized values
        
        Args:
            query: SQL SELECT query
            params: Dictionary of parameters for query
            
        Returns:
            Dictionary with columns, rows, and row_count
        """
        if params is None:
            params = {}
        
        try:
            # Validate query
            self._validate_query(query)
            
            # Connect and execute
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Execute with named parameters
            cursor.execute(query, params)
            
            # Fetch results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convert to list of lists
            row_data = [[row[col] for col in columns] for row in rows]
            
            result = {
                'columns': columns,
                'rows': row_data,
                'row_count': len(row_data)
            }
            
            conn.close()
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'columns': [],
                'rows': [],
                'row_count': 0
            }
    
    def get_schema(self) -> str:
        """Get database schema information"""
        query = """
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        result = self.execute(query)
        return result
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Pydantic schema for LLM function calling"""
        return {
            'name': 'sql_query',
            'description': 'Execute SQL query on oilwells database. Returns inspection, maintenance, well metadata. Use for structured time-series data queries.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'SQL SELECT query. Use parameterized queries with :param_name syntax. Only SELECT allowed, no DML/DDL.'
                    },
                    'params': {
                        'type': 'object',
                        'description': 'Named parameters for query as key-value pairs',
                        'default': {}
                    }
                },
                'required': ['query']
            }
        }

# Tool instance
sql_query_tool = SQLQueryTool()
