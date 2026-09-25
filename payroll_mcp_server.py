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
mcp = FastMCP("PayrollSyncServer")

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
PAYROLL_DB_PATH = DATA_DIR / "payroll_system.db"
RECEIVED_PAYLOAD_PATH = DATA_DIR / "received_payload.json"

@mcp.tool()
async def receive_payload(payload_data: str) -> Dict[str, Any]:
    """
    Tool 1: Receive sync payload from HR system
    """
    try:
        # Parse payload
        if isinstance(payload_data, str):
            payload = json.loads(payload_data)
        else:
            payload = payload_data
        
        # Validate payload structure
        required_fields = ["source_system", "target_system", "sync_timestamp", "changes"]
        missing_fields = [field for field in required_fields if field not in payload]
        
        if missing_fields:
            return {"error": f"Missing required fields: {missing_fields}"}
        
        if payload.get("target_system") != "payroll_system":
            return {"error": f"Payload not intended for payroll system"}
        
        # Add reception metadata
        payload["received_timestamp"] = datetime.now().isoformat()
        payload["reception_status"] = "received"
        
        # Save to file
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(RECEIVED_PAYLOAD_PATH, 'w') as f:
            json.dump(payload, f, indent=2)
        
        # Log in database
        conn = sqlite3.connect(str(PAYROLL_DB_PATH))
        cursor = conn.cursor()
        
        for change in payload.get("changes", []):
            cursor.execute("""
                INSERT INTO sync_log (
                    employee_id, sync_type, source_data, sync_status
                ) VALUES (?, ?, ?, ?)
            """, (
                change.get("employee_id"),
                change.get("change_type", "UPDATE"),
                json.dumps(change),
                "received"
            ))
        
        conn.commit()
        conn.close()
        
        changes_count = len(payload.get("changes", []))
        logger.info(f"Received payload with {changes_count} changes")
        
        return {
            "success": True,
            "payload_path": str(RECEIVED_PAYLOAD_PATH.absolute()),
            "changes_received": changes_count,
            "source_system": payload.get("source_system"),
            "sync_timestamp": payload.get("sync_timestamp"),
            "received_timestamp": payload["received_timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Error receiving payload: {e}")
        return {"error": str(e)}

@mcp.tool()
async def validate_sync_data() -> Dict[str, Any]:
    """
    Tool 2: Validate received sync data for payroll system
    """
    try:
        if not RECEIVED_PAYLOAD_PATH.exists():
            return {"error": "No payload found. Please receive payload first."}
        
        # Load received payload
        with open(RECEIVED_PAYLOAD_PATH, 'r') as f:
            payload = json.load(f)
        
        changes = payload.get("changes", [])
        validated_changes = []
        errors = []
        warnings = []
        
        # Get existing payroll employees
        conn = sqlite3.connect(str(PAYROLL_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT employee_id, email, base_salary FROM payroll_employees")
        existing_employees = {
            row["employee_id"]: {"email": row["email"], "salary": row["base_salary"]} 
            for row in cursor.fetchall()
        }
        
        for change in changes:
            employee_id = change.get("employee_id")
            change_errors = []
            change_warnings = []
            
            new_values = change.get("new_values", {})
            current_data = change.get("current_employee_data", {})
            
            # Payroll validation rules
            
            # Rule 1: Check if employee exists in payroll system
            if employee_id not in existing_employees:
                if change.get("change_type") == "UPDATE":
                    change_warnings.append(f"Employee {employee_id} not in payroll - will create new record")
            
            # Rule 2: Salary validation for payroll
            if "salary" in new_values:
                salary = float(new_values.get("salary", 0))
                if salary <= 0:
                    change_errors.append(f"Invalid salary amount: ${salary}")
                
                # Check for large salary changes
                if employee_id in existing_employees:
                    current_salary = float(existing_employees[employee_id]["salary"])
                    change_percent = abs(salary - current_salary) / current_salary * 100
                    if change_percent > 20:
                        change_warnings.append(f"Large salary change: {change_percent:.1f}%")
            
            # Rule 3: Required fields for payroll
            required_fields = ["first_name", "last_name", "email"]
            for field in required_fields:
                if field not in current_data or not current_data.get(field):
                    change_errors.append(f"Missing required field: {field}")
            
            validation_result = {
                **change,
                "payroll_validation_status": "passed" if not change_errors else "failed",
                "payroll_errors": change_errors,
                "payroll_warnings": change_warnings
            }
            
            validated_changes.append(validation_result)
            errors.extend(change_errors)
            warnings.extend(change_warnings)
        
        conn.close()
        
        overall_status = "passed" if not errors else "failed"
        
        # Update payload with validation results
        payload["payroll_validation"] = {
            "validation_status": overall_status,
            "validation_timestamp": datetime.now().isoformat(),
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "errors": errors,
            "warnings": warnings
        }
        payload["validated_changes"] = validated_changes
        
        # Save updated payload
        with open(RECEIVED_PAYLOAD_PATH, 'w') as f:
            json.dump(payload, f, indent=2)
        
        logger.info(f"Validated {len(changes)} changes - Status: {overall_status}")
        return {
            "success": True,
            "validation_status": overall_status,
            "validated_changes": validated_changes,
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "errors": errors,
            "warnings": warnings
        }
        
    except Exception as e:
        logger.error(f"Error validating sync data: {e}")
        return {"error": str(e)}

@mcp.tool()
async def apply_changes() -> Dict[str, Any]:
    """
    Tool 3: Apply validated changes to payroll system
    """
    try:
        if not RECEIVED_PAYLOAD_PATH.exists():
            return {"error": "No payload found. Please receive and validate payload first."}
        
        # Load validated payload
        with open(RECEIVED_PAYLOAD_PATH, 'r') as f:
            payload = json.load(f)
        
        if "validated_changes" not in payload:
            return {"error": "Payload not validated. Please run validate_sync_data first."}
        
        validated_changes = payload["validated_changes"]
        
        # Filter only passed validations
        approved_changes = [
            change for change in validated_changes
            if change.get("payroll_validation_status") == "passed"
        ]
        
        if not approved_changes:
            return {"message": "No approved changes to apply"}
        
        conn = sqlite3.connect(str(PAYROLL_DB_PATH))
        cursor = conn.cursor()
        
        applied_changes = []
        failed_changes = []
        
        for change in approved_changes:
            try:
                employee_id = change.get("employee_id")
                current_data = change.get("current_employee_data", {})
                
                # Check if employee exists
                cursor.execute("SELECT employee_id FROM payroll_employees WHERE employee_id = ?", (employee_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing employee
                    cursor.execute("""
                        UPDATE payroll_employees SET
                            full_name = ?,
                            email = ?,
                            department = ?,
                            position = ?,
                            base_salary = ?,
                            last_sync_timestamp = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE employee_id = ?
                    """, (
                        f"{current_data.get('first_name', '')} {current_data.get('last_name', '')}".strip(),
                        current_data.get('email'),
                        current_data.get('department'),
                        current_data.get('position'),
                        current_data.get('salary'),
                        datetime.now().isoformat(),
                        employee_id
                    ))
                    operation = "updated"
                else:
                    # Insert new employee
                    cursor.execute("""
                        INSERT INTO payroll_employees (
                            employee_id, full_name, email, department, position, 
                            base_salary, pay_grade, tax_status, last_sync_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        employee_id,
                        f"{current_data.get('first_name', '')} {current_data.get('last_name', '')}".strip(),
                        current_data.get('email'),
                        current_data.get('department'),
                        current_data.get('position'),
                        current_data.get('salary'),
                        'L3',  # Default pay grade
                        'active',
                        datetime.now().isoformat()
                    ))
                    operation = "created"
                
                # Update sync log
                cursor.execute("""
                    UPDATE sync_log SET 
                        sync_status = 'success'
                    WHERE employee_id = ? AND sync_status = 'received'
                """, (employee_id,))
                
                applied_changes.append({
                    "employee_id": employee_id,
                    "operation": operation,
                    "employee_name": f"{current_data.get('first_name', '')} {current_data.get('last_name', '')}".strip()
                })
                
            except Exception as e:
                failed_changes.append({
                    "employee_id": employee_id,
                    "error": str(e)
                })
        
        conn.commit()
        conn.close()
        
        # Update payload with results
        payload["application_results"] = {
            "applied_timestamp": datetime.now().isoformat(),
            "applied_changes": applied_changes,
            "failed_changes": failed_changes,
            "success_count": len(applied_changes),
            "failure_count": len(failed_changes)
        }
        
        # Save final results
        with open(RECEIVED_PAYLOAD_PATH, 'w') as f:
            json.dump(payload, f, indent=2)
        
        logger.info(f"Applied {len(applied_changes)} changes, {len(failed_changes)} failed")
        return {
            "success": True,
            "applied_changes": applied_changes,
            "failed_changes": failed_changes,
            "success_count": len(applied_changes),
            "failure_count": len(failed_changes)
        }
        
    except Exception as e:
        logger.error(f"Error applying changes: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Payroll Sync MCP Server on port 7002...")
    mcp.run(transport="streamable-http")
