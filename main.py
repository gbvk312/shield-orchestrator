"""Shield Orchestrator — Multi-Agent Security REPL entry point."""

import asyncio
import os
import shlex
import sys

from agents import set_tracing_disabled
from agents.mcp import MCPServerStdio, MCPServerStdioParams
from openai import AsyncOpenAI

from shield_orchestrator.agents import build_agent_pool
from shield_orchestrator.config import (
    DEFAULT_MODEL_POOL,
    GEMINI_BASE_URL,
    get_agent_path,
    get_gemini_api_key,
)
from shield_orchestrator.models import RotatingModel
from shield_orchestrator.repl import run_repl


class ConfigurationError(RuntimeError):
    """Raised when environment variables or paths are incorrectly configured."""


class AgentConnectionError(RuntimeError):
    """Raised when the MCP server fails to connect or start."""


async def main() -> None:
    # Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
    set_tracing_disabled(True)

    gemini_key = get_gemini_api_key()
    if not gemini_key:
        raise ConfigurationError("Please configure GEMINI_API_KEY in your .env file.")

    print("Initializing Multi-Agent Security Framework (Failover Mode)...")

    # 2. Configure Gemini Client
    gemini_client = AsyncOpenAI(
        api_key=gemini_key,
        base_url=GEMINI_BASE_URL,
    )

    # 3. Create the rotating model with the configured pool
    rotating_model = RotatingModel(DEFAULT_MODEL_POOL, gemini_client)

    # 4. Define MCP Server Connection
    agent_path = os.path.abspath(get_agent_path())

    if not os.path.exists(agent_path):
        raise ConfigurationError(
            f"The configured agent path '{agent_path}' does not exist.\n"
            "Please check your SHIELD_AGENT_PATH environment variable or confirm the directory exists."
        )

    server_params = MCPServerStdioParams(
        command="bash",
        args=["-c", f"cd {shlex.quote(agent_path)} && uv run shield-agent run-mcp"],
        env={**os.environ, "GEMINI_API_KEY": gemini_key},
    )

    try:
        async with MCPServerStdio(
            params=server_params, name="ShieldAgent-MCP", client_session_timeout_seconds=30
        ) as mcp_server:
            print("[+] Successfully connected to ShieldAgent-MCP!")

            # Build cross-linked agent pool; manager is at index 0
            agent_pool = build_agent_pool(rotating_model, mcp_server)
            manager = agent_pool[0]

            # Start interactive REPL
            await run_repl(manager, DEFAULT_MODEL_POOL)

    except (ConnectionRefusedError, TimeoutError, FileNotFoundError) as e:
        raise AgentConnectionError(f"Failed to connect to MCP server: {e}") from e
    except Exception as e:
        raise AgentConnectionError(f"Unexpected error running orchestrator: {e}") from e


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except AgentConnectionError as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Orchestrator Shutdown] Goodbye!")
        sys.exit(0)

