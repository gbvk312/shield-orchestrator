"""Shield Orchestrator — Multi-Agent Security REPL entry point."""

import asyncio
import os
import shlex

# 1. Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
from agents import set_tracing_disabled  # noqa: E402

set_tracing_disabled(True)

from agents.mcp import MCPServerStdio  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

from shield_orchestrator.agents import build_agent_pool  # noqa: E402
from shield_orchestrator.config import (  # noqa: E402
    DEFAULT_MODEL_POOL,
    GEMINI_BASE_URL,
    get_agent_path,
    get_gemini_api_key,
)
from shield_orchestrator.models import RotatingModel  # noqa: E402
from shield_orchestrator.repl import run_repl  # noqa: E402


async def main():
    gemini_key = get_gemini_api_key()
    if not gemini_key:
        print("Please configure GEMINI_API_KEY in your .env file.")
        return

    print("Initializing Multi-Agent Security Framework (Failover Mode)...")

    # 2. Configure Gemini Client
    gemini_client = AsyncOpenAI(
        api_key=gemini_key,
        base_url=GEMINI_BASE_URL,
    )

    # 3. Create the rotating model with the configured pool
    rotating_model = RotatingModel(DEFAULT_MODEL_POOL, gemini_client)

    # 4. Define MCP Server Connection
    agent_path = get_agent_path()
    server_params = {
        "command": "bash",
        "args": ["-c", f"cd {shlex.quote(agent_path)} && uv run shield-agent run-mcp"],
        "env": {**os.environ, "GEMINI_API_KEY": gemini_key}
    }

    try:
        async with MCPServerStdio(
            params=server_params, 
            name="ShieldAgent-MCP",
            client_session_timeout_seconds=30
        ) as mcp_server:
            print("[+] Successfully connected to ShieldAgent-MCP!")

            # Build cross-linked agent pool; manager is at index 0
            agent_pool = build_agent_pool(rotating_model, mcp_server)
            manager = agent_pool[0]

            # Start interactive REPL
            await run_repl(manager, DEFAULT_MODEL_POOL)

    except Exception as e:
        print(f"Failed to connect or run the orchestrator: {e}")

if __name__ == "__main__":
    asyncio.run(main())
