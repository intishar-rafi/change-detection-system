from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class ChangeType(Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class SyncStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class Employee:
    """HR System Employee Model"""
    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str
    position: str
    hire_date: str
    salary: float
    manager_id: Optional[str] = None
    status: str = "active"
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class PayrollEmployee:
    """Payroll System Employee Model"""
    employee_id: str
    full_name: str
    email: str
    department: str
    position: str
    base_salary: float
    pay_grade: Optional[str] = None
    tax_status: str = "active"
    bank_account: Optional[str] = None
    routing_number: Optional[str] = None
    tax_withholding: float = 22.00
    benefits_deduction: float = 0.00
    last_sync_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class EmployeeChange:
    """Change Detection Model"""
    employee_id: str
    change_type: ChangeType
    changed_fields: List[str]
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    change_timestamp: datetime
    processed: bool = False

@dataclass
class SyncPayload:
    """Data transfer payload between systems"""
    timestamp: datetime
    changes_detected: int
    employee_changes: List[Dict[str, Any]]
    source_system: str = "hr_system"
    target_system: str = "payroll_system"
