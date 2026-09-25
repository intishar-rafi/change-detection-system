#!/usr/bin/env python3

import os
import subprocess
import time
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# OpenAI API Key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Paths
ROOT_DIR = Path(__file__).parent.resolve()

def start_hr_mcp_server():
    """Start HR MCP Server in background"""
    try:
        print("🔧 Starting HR MCP Server...")
        server_process = subprocess.Popen([
            "python3", "hr_mcp_server.py"
        ], cwd=ROOT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)  # Give server time to start
        print("✅ HR MCP Server started")
        return server_process
    except Exception as e:
        print(f"❌ Failed to start HR MCP Server: {e}")
        return None

def detect_hr_changes():
    """Detect changes in HR system and create sync payload"""
    try:
        # Start HR MCP server if needed
        start_hr_mcp_server()
        
        # Import and run HR agent auto function
        from hr_agent import run_agent_auto
        import asyncio
        result = asyncio.run(run_agent_auto())
        return f"HR change detection completed: {result}"
    except Exception as e:
        return f"❌ HR detection error: {str(e)}"

def process_payroll_sync():
    """Process sync payload and update payroll system"""
    try:
        # Import and run Payroll agent  
        from payroll_agent import run_payroll_agent
        run_payroll_agent()
        return "Payroll sync completed successfully"
    except Exception as e:
        return f"❌ Payroll sync error: {str(e)}"

# Create HR Agent with tools
hr_agent = create_react_agent(
    model=f"openai:gpt-4o",
    tools=[detect_hr_changes],
    prompt="You are an HR system agent that detects employee changes and creates sync payloads",
    name="hr_agent"
)

# Create Payroll Agent with tools
payroll_agent = create_react_agent(
    model=f"openai:gpt-4o",
    tools=[process_payroll_sync],
    prompt="You are a payroll system agent that processes sync payloads and updates payroll database",
    name="payroll_agent"
)

# Create Supervisor
supervisor = create_supervisor(
    agents=[hr_agent, payroll_agent],
    model=ChatOpenAI(model="gpt-4o", model_kwargs={"parallel_tool_calls": False}),
    prompt=(
        "You are the Employee Sync System Orchestrator. You manage an HR agent and a payroll agent. "
        "For 'sync employees' or 'full sync' - assign to HR agent first to detect changes, then payroll agent to process. "
        "For 'check changes' - assign to HR agent only. "
        "For 'process payroll' - assign to payroll agent only. "
        "Always coordinate the workflow and provide clear handoff information."
    )
).compile()

def run_orchestrator():
    """Run the orchestrator agent with user interaction"""
    
    print("="*60)
    print("🏢 EMPLOYEE SYNC SYSTEM ORCHESTRATOR")
    print("="*60)
    print("Available commands:")
    print("• 'sync employees' - Detect HR changes and sync to payroll")
    print("• 'check changes' - Check for new HR changes only") 
    print("• 'process payroll' - Process existing sync payload")
    print("• 'quit' - Exit")
    print("="*60)
    
    while True:
        try:
            user_input = input("\n🤖 What would you like me to do? ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            print(f"\n🎯 Processing request: '{user_input}'")
            print("="*50)
            
            # Stream the response to show real-time progress
            for chunk in supervisor.stream({
                "messages": [{"role": "user", "content": user_input}]
            }):
                print(chunk)
                print("\n")
                            
            print("="*50)
            print("✅ Task completed!")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")

if __name__ == "__main__":
    run_orchestrator()
