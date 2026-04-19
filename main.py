import asyncio
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# 1. Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
from agents import set_tracing_disabled
set_tracing_disabled(True)

from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio

async def main():
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Please configure GEMINI_API_KEY in your .env file.")
        return

    print("Initializing ShieldOrchestrator with Gemini...")

    # 2. Configure a dedicated AsyncOpenAI client for Gemini
    # This ensures the base URL is locked in at the client level
    gemini_client = AsyncOpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    # 3. Use OpenAIChatCompletionsModel to force use of the Chat Completions API
    # (Gemini's compatibility layer supports Chat Completions, but not the newer 'Responses API')
    model = OpenAIChatCompletionsModel(
        model="gemini-flash-latest", 
        openai_client=gemini_client
    )

    # Define how to start ShieldAgent-MCP
    server_params = {
        "command": "bash",
        "args": ["-c", "cd ../shield-agent-mcp && uv run shield-agent run-mcp"]
    }

    try:
        async with MCPServerStdio(params=server_params, name="ShieldAgent-MCP") as mcp_server:
            print("[+] Successfully connected to ShieldAgent-MCP!")
            
            # Debug: Print discovered tools
            tools = await mcp_server.list_tools()
            print(f"[+] Discovered {len(tools)} tools: {[t.name for t in tools]}")
            
            # Initialize the agent and pass the MCP server instance 
            agent = Agent(
                name="ShieldOrchestrator",
                instructions=(
                    "You are ShieldOrchestrator, a highly capable multi-agent security analyst. "
                    "You have access to tools via the connected ShieldAgent-MCP. "
                    "CRITICAL: Only use tools that are explicitly provided in your tool list. "
                    "Do NOT assume tools like 'list_dir' exist; use 'list_directory' instead if available. "
                    "When asked to investigate, use 'list_directory' to explore the path first. "
                    "Be meticulous and think step-by-step."
                ),
                model=model,
                mcp_servers=[mcp_server],
                mcp_config={"convert_schemas_to_strict": True}
            )

            print("---")
            print("ShieldOrchestrator (Gemini) REPL Started. Type 'exit' or 'quit' to terminate.")
            print("---")
            
            while True:
                prompt = input("\n[You]> ")
                if prompt.lower() in ("exit", "quit"):
                    break
                if not prompt.strip():
                    continue
                
                print("\n[ShieldOrchestrator is thinking...]")
                
                try:
                    result = await Runner.run(agent, prompt)
                    print(f"\n[ShieldOrchestrator]> {result.final_output}")
                except Exception as e:
                    print(f"\n[Error during run]: {e}")

    except Exception as e:
        print(f"Failed to connect or run the orchestrator: {e}")

if __name__ == "__main__":
    asyncio.run(main())
