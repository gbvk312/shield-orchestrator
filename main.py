import asyncio
import os
from collections.abc import AsyncIterator
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# 1. Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
from agents import set_tracing_disabled  # noqa: E402
set_tracing_disabled(True)

from openai import AsyncOpenAI  # noqa: E402
from agents import Agent, Runner, OpenAIChatCompletionsModel  # noqa: E402
from agents.models.interface import Model  # noqa: E402
from agents.mcp import MCPServerStdio  # noqa: E402

# --- CUSTOM ROTATING MODEL (FAILOVER MODE) ---

class RotatingModel(Model):
    """
    Stays with the same model until a Rate Limit (429) is encountered,
    then fails over to the next model in the pool.
    """
    def __init__(self, model_ids: list[str], client: AsyncOpenAI):
        self.model_ids = model_ids
        self.client = client
        self.index = 0
        self._models = [
            OpenAIChatCompletionsModel(model=mid, openai_client=client)
            for mid in model_ids
        ]

    def _get_current_model(self):
        return self._models[self.index]

    async def get_response(self, *args, **kwargs):
        attempts = 0
        while attempts < len(self._models):
            model = self._get_current_model()
            try:
                # Attempt to get a response with the current model
                return await model.get_response(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                # Detect rate limits (429) or Google's RESOURCE_EXHAUSTED status
                if any(key in err_str for key in ["429", "resource_exhausted", "rate limit"]):
                    print(f"[RotatingModel] ⚠️ Rate Limit hit for {self.model_ids[self.index]}.")
                    self.index = (self.index + 1) % len(self._models)
                    print(f"[RotatingModel] 🔄 Failing over to: {self.model_ids[self.index]}")
                    attempts += 1
                    continue
                # For any other fatal errors (400, etc.), raise immediately
                raise e
        
        raise Exception("❌ All models in the pool have reached their rate limits. Please wait a minute.")

    async def stream_response(self, *args, **kwargs) -> AsyncIterator:  # type: ignore[override]
        """Stream with failover: retries on 429 at connection start."""
        attempts = 0
        while attempts < len(self._models):
            model = self._get_current_model()
            try:
                return await model.stream_response(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                if any(key in err_str for key in ["429", "resource_exhausted", "rate limit"]):
                    print(f"[RotatingModel] ⚠️ Stream Rate Limit hit for {self.model_ids[self.index]}.")
                    self.index = (self.index + 1) % len(self._models)
                    print(f"[RotatingModel] 🔄 Stream failing over to: {self.model_ids[self.index]}")
                    attempts += 1
                    continue
                raise e
        raise Exception("❌ All models in the pool have reached their rate limits during streaming.")

async def main():
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Please configure GEMINI_API_KEY in your .env file.")
        return

    print("Initializing Multi-Agent Security Framework (Failover Mode)...")

    # 2. Configure Gemini Client
    gemini_client = AsyncOpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    # 3. Define the Model Pool (Gemma 4+ and Gemini)
    # Sticking to models confirmed to support Tool Calling.
    model_pool = [
        "gemma-4-31b-it",
        "gemma-4-26b-a4b-it",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-pro-latest"
    ]
    
    rotating_model = RotatingModel(model_pool, gemini_client)

    # 4. Define MCP Server Connection
    agent_path = os.getenv("SHIELD_AGENT_PATH", "../shield-agent-mcp")
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
            print(f"Primary Model: {model_pool[0]}")
            print(f"Failover Pool: {', '.join(model_pool[1:])}")
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
