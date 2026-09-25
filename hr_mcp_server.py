import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("HRChangeDetectionServer")

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
HR_DB_PATH = DATA_DIR / "hr_system.db"
PAYLOAD_PATH = DATA_DIR / "sync_payload.json"

@mcp.tool()
async def detect_changes() -> Dict[str, Any]:
    """
    Tool 1: Detect and track unprocessed employee changes from HR database
    """
    try:
        if not HR_DB_PATH.exists():
            return {"error": f"HR database not found at {HR_DB_PATH}"}
        
        conn = sqlite3.connect(str(HR_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get unprocessed changes with current employee data
        cursor.execute("""
            SELECT 
                cl.id as log_id,
                cl.employee_id,
                cl.change_type,
                cl.old_values,
                cl.new_values,
                cl.change_timestamp,
                e.first_name,
                e.last_name,
                e.email,
                e.department,
                e.position,
                e.salary,
                e.status
            FROM employee_change_log cl
            LEFT JOIN employees e ON cl.employee_id = e.employee_id
            WHERE cl.processed = FALSE
            ORDER BY cl.change_timestamp ASC
        """)
        
        changes = []
        for row in cursor.fetchall():
            change_data = {
                "log_id": row["log_id"],
                "employee_id": row["employee_id"],
                "change_type": row["change_type"],
                "old_values": json.loads(row["old_values"]) if row["old_values"] else {},
                "new_values": json.loads(row["new_values"]) if row["new_values"] else {},
                "change_timestamp": row["change_timestamp"],
                "current_employee_data": {
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "department": row["department"],
                    "position": row["position"],
                    "salary": row["salary"],
                    "status": row["status"]
                }
            }
            changes.append(change_data)
        
        conn.close()
        
        logger.info(f"Detected {len(changes)} unprocessed changes")
        return {
            "success": True,
            "changes_count": len(changes),
            "changes": changes,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error detecting changes: {e}")
        return {"error": str(e)}

@mcp.tool()
async def create_sync_payload() -> Dict[str, Any]:
    """
    Tool 2: Create JSON file with sync payload from unprocessed changes and mark them as processed
    """
    try:
        # Get unprocessed changes directly from database
        if not HR_DB_PATH.exists():
            return {"error": f"HR database not found at {HR_DB_PATH}"}
        
        conn = sqlite3.connect(str(HR_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get unprocessed changes with current employee data
        cursor.execute("""
            SELECT 
                cl.id as log_id,
                cl.employee_id,
                cl.change_type,
                cl.old_values,
                cl.new_values,
                cl.change_timestamp,
                e.first_name,
                e.last_name,
                e.email,
                e.department,
                e.position,
                e.salary,
                e.status
            FROM employee_change_log cl
            LEFT JOIN employees e ON cl.employee_id = e.employee_id
            WHERE cl.processed = FALSE
            ORDER BY cl.change_timestamp ASC
        """)
        
        changes = []
        for row in cursor.fetchall():
            change_data = {
                "log_id": row["log_id"],
                "employee_id": row["employee_id"],
                "change_type": row["change_type"],
                "old_values": json.loads(row["old_values"]) if row["old_values"] else {},
                "new_values": json.loads(row["new_values"]) if row["new_values"] else {},
                "change_timestamp": row["change_timestamp"],
                "current_employee_data": {
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "department": row["department"],
                    "position": row["position"],
                    "salary": row["salary"],
                    "status": row["status"]
                }
            }
            changes.append(change_data)
        
        if not changes:
            conn.close()
            return {
                "success": True,
                "message": "No unprocessed changes found",
                "changes_processed": 0
            }
        
        # Create sync payload
        payload = {
            "source_system": "hr_system",
            "target_system": "payroll_system",
            "sync_timestamp": datetime.now().isoformat(),
            "total_changes": len(changes),
            "changes": changes,
            "metadata": {
                "generated_by": "HR Change Detection System",
                "sync_id": f"SYNC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "status": "ready_for_sync"
            }
        }
        
        # Save payload to JSON file
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(PAYLOAD_PATH, 'w') as f:
            json.dump(payload, f, indent=2)
        
        # Mark changes as processed in database
        log_ids = [change["log_id"] for change in changes]
        placeholders = ",".join("?" * len(log_ids))
        
        cursor.execute(f"""
            UPDATE employee_change_log 
            SET processed = TRUE
            WHERE id IN ({placeholders})
        """, log_ids)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created sync payload with {len(changes)} changes")
        return {
            "success": True,
            "payload_path": str(PAYLOAD_PATH.absolute()),
            "changes_processed": len(changes),
            "sync_id": payload["metadata"]["sync_id"],
            "timestamp": datetime.now().isoformat(),
            "payload_preview": {
                "total_changes": payload["total_changes"],
                "sync_id": payload["metadata"]["sync_id"],
                "target_system": payload["target_system"]
            }
        }
        
        # Save payload to JSON file
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(PAYLOAD_PATH, 'w') as f:
            json.dump(payload, f, indent=2)
        
        # Mark changes as processed in database
        if changes:
            conn = sqlite3.connect(str(HR_DB_PATH))
            cursor = conn.cursor()
            
            log_ids = [change["log_id"] for change in changes]
            placeholders = ",".join("?" * len(log_ids))
            
            cursor.execute(f"""
                UPDATE employee_change_log 
                SET processed = TRUE
                WHERE id IN ({placeholders})
            """, log_ids)
            
            conn.commit()
            conn.close()
        
        logger.info(f"Created sync payload with {len(changes)} changes")
        return {
            "success": True,
            "payload_path": str(PAYLOAD_PATH.absolute()),
            "changes_processed": len(changes),
            "sync_id": payload["metadata"]["sync_id"],
            "timestamp": datetime.now().isoformat(),
            "payload_preview": {
                "total_changes": payload["total_changes"],
                "sync_id": payload["metadata"]["sync_id"],
                "target_system": payload["target_system"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating sync payload: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting HR Change Detection MCP Server on port 7001...")
    print(f"📊 Database: {HR_DB_PATH}")
    print(f"📦 Payload path: {PAYLOAD_PATH}")
    mcp.run(transport="streamable-http")
