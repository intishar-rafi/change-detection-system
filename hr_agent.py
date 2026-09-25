#!/usr/bin/env python3

import os
import asyncio
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

# Load environment variables
load_dotenv()

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

#  OpenAI LLM
def get_llm():
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        temperature=0.1,
    )

# Create HR agent
async def create_hr_agent():
    # MCP client configuration
    client = MultiServerMCPClient({
        "hr_system": {
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        }
    })
    
    # Get tools from MCP server
    tools = await client.get_tools()
    print(f"✅ Loaded {len(tools)} MCP tools:")
    for tool in tools:
        print(f"   • {tool.name}")
    
    # Create agent
    llm = get_llm()
    agent = create_react_agent(llm, tools, prompt="You are an HR system agent that detects employee changes and creates sync payloads", name="hr_agent")

    return agent, client

# Run agent programmatically (for orchestrator)
async def run_agent_auto():
    print("🚀 HR Change Detection Agent (Auto Mode)")
    
    agent, client = await create_hr_agent()
    
    # Automatically check for changes and create payload
    user_message = """
    Please check for HR system changes and create a sync payload if there are any unprocessed changes.
    First use detect_changes to see if there are any new employee changes, then if there are changes, use create_sync_payload to generate the payload file.
    """
    
    print("🤖 Checking for HR changes...")
    
    response = await agent.ainvoke({
        "messages": [{"role": "user", "content": user_message}]
    })
    
    print(f"🤖 HR Agent Result: {response['messages'][-1].content}")
    
    return response['messages'][-1].content

# Run agent interactively (for manual testing)
async def run_agent():
    print("🚀 HR Change Detection Agent")
    print("Commands: 'check changes', 'create payload', or 'quit'")
    
    agent, client = await create_hr_agent()
    
    while True:
        user_input = input("\n💬 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        if not user_input:
            continue
        
        print("🤖 Processing...")
        
        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        
        print(f"🤖 Agent: {response['messages'][-1].content}")
    
    print("👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(run_agent())
