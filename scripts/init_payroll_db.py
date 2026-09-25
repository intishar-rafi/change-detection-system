import sqlite3
from datetime import datetime
from pathlib import Path

def init_payroll_database():
    """Initialize Payroll system database"""
    
    db_path = Path(__file__).parent.parent / "data" / "payroll_system.db"
    
    # Remove existing database for clean start
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create payroll_employees table
    cursor.execute("""
        CREATE TABLE payroll_employees (
            employee_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            position TEXT,
            base_salary DECIMAL(10,2),
            pay_grade TEXT,
            tax_status TEXT DEFAULT 'active',
            last_sync_timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create sync_log table
    cursor.execute("""
        CREATE TABLE sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            sync_type TEXT NOT NULL,
            source_data TEXT,
            sync_status TEXT DEFAULT 'pending',
            error_message TEXT,
            sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES payroll_employees(employee_id)
        )
    """)
    
    # Insert some existing payroll data (subset of HR employees)
    payroll_employees = [
        ('EMP001', 'John Doe', 'john.doe@company.com', 'Engineering', 'Senior Developer', 95000.00, 'L5', 'active'),
        ('EMP002', 'Jane Smith', 'jane.smith@company.com', 'Marketing', 'Marketing Manager', 85000.00, 'L4', 'active'),
        ('EMP003', 'Bob Johnson', 'bob.johnson@company.com', 'Finance', 'Financial Analyst', 70000.00, 'L3', 'active'),
    ]
    
    cursor.executemany("""
        INSERT INTO payroll_employees (
            employee_id, full_name, email, department, position, base_salary, pay_grade, tax_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, payroll_employees)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Payroll database initialized with {len(payroll_employees)} employees")
    print(f"📍 Database location: {db_path}")
    return db_path

if __name__ == "__main__":
    init_payroll_database()
