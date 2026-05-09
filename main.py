"""Shield Orchestrator — Multi-Agent Security REPL entry point."""

import asyncio
import os

# 1. Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
from agents import set_tracing_disabled  # noqa: E402
set_tracing_disabled(True)

from openai import AsyncOpenAI  # noqa: E402
from agents import Agent, Runner  # noqa: E402
from agents.mcp import MCPServerStdio  # noqa: E402

from shield_orchestrator.models import RotatingModel  # noqa: E402
from shield_orchestrator.config import (  # noqa: E402
    get_gemini_api_key,
    get_agent_path,
    DEFAULT_MODEL_POOL,
    GEMINI_BASE_URL,
)


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
        "args": ["-c", f"cd {agent_path} && uv run shield-agent run-mcp"],
        "env": {**os.environ, "GEMINI_API_KEY": gemini_key}
    }

    try:
        async with MCPServerStdio(
            params=server_params, 
            name="ShieldAgent-MCP",
            client_session_timeout_seconds=30
        ) as mcp_server:
            print("[+] Successfully connected to ShieldAgent-MCP!")
            
            # --- AGENT DEFINITIONS ---

            # Triage/Manager
            manager = Agent(
                name="Manager",
                instructions=(
                    "You are the Lead Security Orchestrator (Manager). "
                    "Your workflow for every request: "
                    "1. Use 'list_directory' to explore the project structure and understand the codebase layout. "
                    "2. Use 'check_network_exposure' to identify open ports and risky network services. "
                    "3. Hand off to 'SecurityAuditor' for deep vulnerability scanning and file audits. "
                    "4. After receiving audit findings, hand off to 'SecurityRemediator' to apply fixes. "
                    "5. Summarize all findings and actions taken in a final report. "
                    "Always prefer delegation over doing security analysis yourself."
                ),
                model=rotating_model,
                mcp_servers=[mcp_server],
                mcp_config={"convert_schemas_to_strict": True}
            )

            auditor = Agent(
                name="SecurityAuditor",
                instructions=(
                    "You are a Senior Security Auditor. Your ONLY goal is to find vulnerabilities. "
                    "Workflow: "
                    "1. Use 'scan_for_secrets' on the target directory to detect PII, API keys, and secrets. "
                    "2. Use 'read_file' to inspect suspicious files identified by the scan. "
                    "3. Use 'audit_file' on critical source files (e.g., config, auth, API handlers) for deep analysis. "
                    "4. Compile a structured report with severity levels (CRITICAL/HIGH/MEDIUM/LOW). "
                    "5. Hand off to the Manager with your findings. Do NOT attempt to fix issues yourself."
                ),
                model=rotating_model,
                mcp_servers=[mcp_server],
                mcp_config={"convert_schemas_to_strict": True}
            )

            remediator = Agent(
                name="SecurityRemediator",
                instructions=(
                    "You are a Security Remediation Expert. Your ONLY goal is to fix vulnerabilities. "
                    "Workflow: "
                    "1. Review the audit findings provided by the Manager or Auditor. "
                    "2. Use 'read_file' to inspect the current content of affected files. "
                    "3. Use 'safe_write_file' to apply patches. ALWAYS provide a clear 'reason' explaining the security fix. "
                    "4. Verify your fix by reading the file again after writing. "
                    "5. Report all changes made and hand off to the Manager. Do NOT scan for new issues."
                ),
                model=rotating_model,
                mcp_servers=[mcp_server],
                mcp_config={"convert_schemas_to_strict": True}
            )

            # Link all agents to each other to ensure all 'transfer_to' tools are available
            agent_pool = [manager, auditor, remediator]
            for agent in agent_pool:
                agent.handoffs = [a for a in agent_pool if a != agent]

            # --- START REPL ---
            print("---")
            print(f"Primary Model: {DEFAULT_MODEL_POOL[0]}")
            print(f"Failover Pool: {', '.join(DEFAULT_MODEL_POOL[1:])}")
            print("---")
            
            while True:
                prompt = input("\n[You]> ")
                if prompt.lower() in ("exit", "quit"):
                    break
                if not prompt.strip():
                    continue
                
                print("\n[ShieldOrchestrator is processing...]")
                
                try:
                    # Always start with the manager/triage agent
                    result = await Runner.run(manager, prompt)
                    print(f"\n[Result]> {result.final_output}")
                except Exception as e:
                    print(f"\n[Error during run]: {e}")

    except Exception as e:
        print(f"Failed to connect or run the orchestrator: {e}")

if __name__ == "__main__":
    asyncio.run(main())
