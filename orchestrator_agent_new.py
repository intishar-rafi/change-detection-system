#!/usr/bin/env python3

import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Paths
ROOT_DIR = Path(__file__).parent.resolve()

def detect_hr_changes() -> str:
    """Detect changes in HR system and create sync payload"""
    try:
        # Start HR MCP server
        print("🔧 Starting HR MCP Server...")
        server_process = subprocess.Popen([
            "python3", "hr_mcp_server.py"
        ], cwd=ROOT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        
        # Run HR agent
        import asyncio
        from hr_agent import run_agent_auto
        asyncio.run(run_agent_auto())
        return "HR change detection completed successfully"
    except Exception as e:
        return f"❌ HR detection error: {str(e)}"

def process_payroll_sync() -> str:
    """Process sync payload and update payroll system"""
    try:
        from payroll_agent import run_payroll_agent
        run_payroll_agent()
        return "Payroll sync completed successfully"
    except Exception as e:
        return f"❌ Payroll sync error: {str(e)}"

# Get OpenAI LLM
def get_llm():
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        temperature=0.1,
        model_kwargs={"parallel_tool_calls": False}  # Keep tool calls sequential
    )

# Create HR Agent
hr_agent = create_react_agent(
    model=get_llm(),
    tools=[detect_hr_changes],
    prompt="You are an HR system agent that detects employee changes and creates sync payloads",
    name="hr_agent"
)

# Create Payroll Agent
payroll_agent = create_react_agent(
    model=get_llm(),
    tools=[process_payroll_sync],
    prompt="You are a payroll system agent that processes sync payloads and updates payroll database",
    name="payroll_agent"
)

# Create Supervisor
supervisor = create_supervisor(
    agents=[hr_agent, payroll_agent],
    model=get_llm(),
    prompt=(
        "You are the Employee Sync System Orchestrator. You manage an HR agent and a payroll agent. "
        "For 'sync employees' or 'full sync' - assign to HR agent first to detect changes, then payroll agent to process. "
        "For 'check changes' - assign to HR agent only. "
        "For 'process payroll' - assign to payroll agent only. "
        "Always coordinate the workflow and provide clear handoff information."
    )
).compile()

def run_orchestrator():
    """Run the orchestrator"""
    print("🏢 EMPLOYEE SYNC SYSTEM ORCHESTRATOR")
    print("="*50)
    
    while True:
        user_input = input("\n🤖 What would you like me to do? (sync employees/check changes/process payroll/quit): ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        print(f"\n🎯 Processing: '{user_input}'")
        print("="*40)
        
        for chunk in supervisor.stream({
            "messages": [{"role": "user", "content": user_input}]
        }):
            for agent_name, agent_output in chunk.items():
                for msg in agent_output.get("messages", []):
                    content = getattr(msg, "content", "")
                    if content and content.strip() and "Transferring" not in content:
                        speaker = getattr(msg, "name", None) or agent_name
                        print(f"🗣️  [{speaker}] {content}")

if __name__ == "__main__":
    run_orchestrator()