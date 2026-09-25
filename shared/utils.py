import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path: Path, schema_path: Optional[Path] = None):
        self.db_path = db_path
        self.schema_path = schema_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Ensure data directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if schema provided
        if schema_path and schema_path.exists():
            self.initialize_database()
    
    def initialize_database(self):
        """Initialize database with schema if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                if self.schema_path and self.schema_path.exists():
                    schema_sql = self.schema_path.read_text()
                    conn.executescript(schema_sql)
                    self.logger.info(f"Database initialized with schema from {self.schema_path}")
                else:
                    self.logger.warning(f"Schema file not found: {self.schema_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

def format_validation_errors(errors: List[str], warnings: List[str]) -> str:
    """Format validation errors and warnings for display"""
    result = []
    
    if errors:
        result.append("❌ ERRORS:")
        for error in errors:
            result.append(f"  • {error}")
    
    if warnings:
        result.append("⚠️  WARNINGS:")
        for warning in warnings:
            result.append(f"  • {warning}")
    
    return "\n".join(result) if result else "✅ No validation issues"

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """Safely load JSON string with error handling"""
    try:
        return json.loads(json_str) if json_str else {}
    except json.JSONDecodeError:
        return {}

def calculate_salary_change_percent(old_salary: float, new_salary: float) -> float:
    """Calculate percentage change in salary"""
    if old_salary == 0:
        return 0
    return abs(new_salary - old_salary) / old_salary * 100
