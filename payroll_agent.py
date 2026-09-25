#!/usr/bin/env python3

import os
import json
import logging
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
SYNC_PAYLOAD_PATH = DATA_DIR / "sync_payload.json"
PAYROLL_DB_PATH = DATA_DIR / "payroll_system.db"

# Azure OpenAI LLM
def get_llm():
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        temperature=0.1,
    )

@tool
def process_sync_payload() -> str:
    """
    Process the HR sync payload and update the payroll system database.
    Reads the sync payload file and applies changes to payroll system.
    """
    try:
        # Check if sync payload exists
        if not SYNC_PAYLOAD_PATH.exists():
            return "❌ No sync payload found. Please ensure HR system has generated a payload."
        
        # Load sync payload
        with open(SYNC_PAYLOAD_PATH, 'r') as f:
            payload = json.load(f)
        
        print(f"📋 Processing sync payload with {payload['total_changes']} changes")
        
        # Connect to payroll database
        conn = sqlite3.connect(PAYROLL_DB_PATH)
        cursor = conn.cursor()
        
        processed_count = 0
        results = []
        
        for change in payload['changes']:
            employee_id = change['employee_id']
            change_type = change['change_type']
            
            if change_type == 'INSERT':
                # Add new employee to payroll
                new_data = change['new_values']
                full_name = f"{new_data['first_name']} {new_data['last_name']}"
                cursor.execute('''
                    INSERT OR REPLACE INTO payroll_employees 
                    (employee_id, full_name, email, department, position, base_salary, tax_status, last_sync_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_data['employee_id'],
                    full_name,
                    new_data['email'],
                    new_data['department'],
                    new_data['position'],
                    new_data['salary'],
                    new_data['status'],
                    datetime.now().isoformat()
                ))
                results.append(f"✅ Added employee {employee_id} ({full_name}) to payroll system")
                
            elif change_type == 'UPDATE':
                # Update existing employee in payroll
                new_data = change['new_values']
                full_name = f"{new_data['first_name']} {new_data['last_name']}"
                cursor.execute('''
                    UPDATE payroll_employees SET
                    full_name=?, email=?, department=?, 
                    position=?, base_salary=?, tax_status=?, last_sync_timestamp=?
                    WHERE employee_id=?
                ''', (
                    full_name,
                    new_data['email'], 
                    new_data['department'],
                    new_data['position'],
                    new_data['salary'],
                    new_data['status'],
                    datetime.now().isoformat(),
                    employee_id
                ))
                results.append(f"✅ Updated employee {employee_id} ({full_name}) in payroll system")
                
            elif change_type == 'DELETE':
                # Remove employee from payroll (set status to inactive)
                cursor.execute('''
                    UPDATE payroll_employees SET tax_status='inactive', last_sync_timestamp=? WHERE employee_id=?
                ''', (datetime.now().isoformat(), employee_id))
                results.append(f"✅ Deactivated employee {employee_id} in payroll system")
            
            processed_count += 1
        
        # Log the sync operation for each employee
        for change in payload['changes']:
            cursor.execute('''
                INSERT INTO sync_log (employee_id, sync_type, source_data, sync_status)
                VALUES (?, ?, ?, ?)
            ''', (
                change['employee_id'],
                f"HR_{change['change_type']}",
                json.dumps(change),
                'completed'
            ))
        
        conn.commit()
        conn.close()
        
        # Update the same payload file with processed status
        payload['metadata']['status'] = 'processed'
        payload['metadata']['processed_timestamp'] = datetime.now().isoformat()
        payload['metadata']['processed_by'] = 'Payroll System Agent'
        
        # Write back to the same file
        with open(SYNC_PAYLOAD_PATH, 'w') as f:
            json.dump(payload, f, indent=2)
        
        summary = f"""
🏢 PAYROLL SYNC COMPLETED
========================
• Processed {processed_count} changes from {payload['source_system']}
• Sync ID: {payload['metadata']['sync_id']}
• Payload file updated with processed status

Changes Applied:
{chr(10).join(results)}
        """
        
        print(summary)
        return summary
        
    except Exception as e:
        error_msg = f"❌ Error processing sync payload: {str(e)}"
        print(error_msg)
        return error_msg

def create_payroll_agent():
    # Create agent with the simple tool
    llm = get_llm()
    tools = [process_sync_payload]
    agent = create_react_agent(llm, tools,prompt="You are a Payroll System Agent that processes HR sync payloads and updates the payroll database.", name="payroll_agent")
    
    print(f"✅ Payroll agent created with {len(tools)} tool:")
    for tool in tools:
        print(f"   • {tool.name}")
    
    return agent

# Run agent
def run_payroll_agent():
    print("🏢 Payroll System Agent")
    
    # Load sync payload
    if not SYNC_PAYLOAD_PATH.exists():
        print("❌ No sync payload found. Please ensure HR system has generated a payload.")
        return
    
    print(f"📋 Found sync payload at {SYNC_PAYLOAD_PATH}")
    
    agent = create_payroll_agent()
    
    user_message = """
    Please process the HR sync payload for the payroll system.
    Use the process_sync_payload tool to read the sync payload file and apply the changes to the payroll database.
    """
    
    print("🤖 Processing sync payload...")
    
    response = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })
    
    print("="*60)
    print("PAYROLL PROCESSING RESULT:")
    print("="*60)
    print(response['messages'][-1].content)
    print("="*60)

if __name__ == "__main__":
    run_payroll_agent()
