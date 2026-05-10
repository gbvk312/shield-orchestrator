"""Shield Orchestrator — Multi-Agent Security REPL entry point."""

import asyncio
import os
import shlex
import sys

# 1. Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
from agents import set_tracing_disabled  # noqa: E402

set_tracing_disabled(True)

from agents.mcp import MCPServerStdio, MCPServerStdioParams  # noqa: E402
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


class ConfigurationError(RuntimeError):
    """Raised when environment variables or paths are incorrectly configured."""


class AgentConnectionError(RuntimeError):
    """Raised when the MCP server fails to connect or start."""


async def main() -> None:
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

    except Exception as e:
        raise AgentConnectionError(f"Failed to connect or run the orchestrator: {e}") from e


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
