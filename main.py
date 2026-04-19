import asyncio
import os
from collections.abc import AsyncIterator
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# 1. Disable tracing to avoid OpenAI-specific telemetry calls failing with a 401
from agents import set_tracing_disabled
set_tracing_disabled(True)

from openai import AsyncOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel
from agents.models.interface import Model, ModelTracing
from agents.mcp import MCPServerStdio

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

    async def stream_response(self, *args, **kwargs) -> AsyncIterator:
        # Note: Failover for streaming is only supported if the 429 happens at connection start.
        model = self._get_current_model()
        return model.stream_response(*args, **kwargs)

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
    server_params = {
        "command": "bash",
        "args": ["-c", "cd ../shield-agent-mcp && uv run shield-agent run-mcp"],
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
                    "1. Explore structure with 'list_directory'. "
                    "2. Check network with 'check_network_exposure'. "
                    "3. Delegate finding issues to 'SecurityAuditor'. "
                    "4. Delegate fixing issues to 'SecurityRemediator'. "
                ),
                model=rotating_model,
                mcp_servers=[mcp_server],
                mcp_config={"convert_schemas_to_strict": True}
            )

            auditor = Agent(
                name="SecurityAuditor",
                instructions=(
                    "You are a Senior Security Auditor. Your goal is to find vulnerabilities. "
                    "Use 'scan_for_secrets' to find PII/Secrets in directories. "
                    "Use 'audit_file' to audit specific source files. "
                    "Once your audit is done, report findings and return control to the Manager."
                ),
                model=rotating_model,
                mcp_servers=[mcp_server],
                # Linkage to Manager + other specialists prevents 'Tool not found' hallucinations
                mcp_config={"convert_schemas_to_strict": True}
            )

            remediator = Agent(
                name="SecurityRemediator",
                instructions=(
                    "You are a Security Remediation Expert. Your goal is to fix vulnerabilities. "
                    "Use 'safe_write_file' to apply patches. Always provide a 'reason'. "
                    "Once fixed, report success and return control to the Manager."
                ),
                model=rotating_model,
                mcp_servers=[mcp_server],
                # Linkage to Manager + other specialists prevents 'Tool not found' hallucinations
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
                
                print(f"\n[ShieldOrchestrator is processing...]")
                
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
