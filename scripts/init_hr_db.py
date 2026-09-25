import sqlite3
import json
from datetime import datetime
from pathlib import Path

def init_hr_database():
    """Initialize HR system database with employees and triggers"""
    
    db_path = Path(__file__).parent.parent / "data" / "hr_system.db"
    
    # Remove existing database for clean start
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create employees table
    cursor.execute("""
        CREATE TABLE employees (
            employee_id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            position TEXT,
            salary DECIMAL(10,2),
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create change log table
    cursor.execute("""
        CREATE TABLE employee_change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            change_type TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)
    
    # Create trigger for UPDATE
    cursor.execute("""
        CREATE TRIGGER employee_update_trigger 
        AFTER UPDATE ON employees
        FOR EACH ROW
        WHEN (
            OLD.first_name != NEW.first_name OR
            OLD.last_name != NEW.last_name OR
            OLD.email != NEW.email OR
            OLD.department != NEW.department OR
            OLD.position != NEW.position OR
            OLD.salary != NEW.salary OR
            OLD.status != NEW.status
        )
        BEGIN
            INSERT INTO employee_change_log (
                employee_id, change_type, old_values, new_values
            ) VALUES (
                NEW.employee_id,
                'UPDATE',
                json_object(
                    'first_name', OLD.first_name,
                    'last_name', OLD.last_name,
                    'email', OLD.email,
                    'department', OLD.department,
                    'position', OLD.position,
                    'salary', OLD.salary,
                    'status', OLD.status
                ),
                json_object(
                    'first_name', NEW.first_name,
                    'last_name', NEW.last_name,
                    'email', NEW.email,
                    'department', NEW.department,
                    'position', NEW.position,
                    'salary', NEW.salary,
                    'status', NEW.status
                )
            );
        END;
    """)
    
    # Create trigger for INSERT (new employees)
    cursor.execute("""
        CREATE TRIGGER employee_insert_trigger 
        AFTER INSERT ON employees
        FOR EACH ROW
        BEGIN
            INSERT INTO employee_change_log (
                employee_id, 
                change_type, 
                old_values,
                new_values
            ) VALUES (
                NEW.employee_id,
                'INSERT',
                '{}',
                json_object(
                    'employee_id', NEW.employee_id,
                    'first_name', NEW.first_name,
                    'last_name', NEW.last_name,
                    'email', NEW.email,
                    'department', NEW.department,
                    'position', NEW.position,
                    'salary', NEW.salary,
                    'status', NEW.status
                )
            );
        END;
    """)

    # Insert sample employees
    employees = [
        ('EMP001', 'John', 'Doe', 'john.doe@company.com', 'Engineering', 'Senior Developer', 95000.00, 'active'),
        ('EMP002', 'Jane', 'Smith', 'jane.smith@company.com', 'Marketing', 'Marketing Manager', 85000.00, 'active'),
        ('EMP003', 'Bob', 'Johnson', 'bob.johnson@company.com', 'Finance', 'Financial Analyst', 70000.00, 'active'),
        ('EMP004', 'Alice', 'Williams', 'alice.williams@company.com', 'HR', 'HR Specialist', 65000.00, 'active'),
        ('EMP005', 'Charlie', 'Brown', 'charlie.brown@company.com', 'Engineering', 'Junior Developer', 60000.00, 'active'),
    ]
    
    cursor.executemany("""
        INSERT INTO employees (
            employee_id, first_name, last_name, email, department, position, salary, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, employees)
    
    conn.commit()
    conn.close()
    
    print(f"✅ HR database initialized with {len(employees)} employees")
    print(f"📍 Database location: {db_path}")
    return db_path

if __name__ == "__main__":
    init_hr_database()
