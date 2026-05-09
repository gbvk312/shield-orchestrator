"""Agent definitions for the Shield Orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents import Agent
from agents.agent import MCPConfig

if TYPE_CHECKING:
    from agents.mcp import MCPServerStdio

    from shield_orchestrator.models import RotatingModel

# --- Agent Instruction Prompts ---

MANAGER_INSTRUCTIONS = (
    "You are the Lead Security Orchestrator (Manager). "
    "Your workflow for every request: "
    "1. Use 'list_directory' to explore the project structure and understand the codebase layout. "
    "2. Use 'check_network_exposure' to identify open ports and risky network services. "
    "3. Hand off to 'SecurityAuditor' for deep vulnerability scanning and file audits. "
    "4. After receiving audit findings, hand off to 'SecurityRemediator' to apply fixes. "
    "5. Summarize all findings and actions taken in a final report using the 'write_final_report' tool. "
    "Always prefer delegation over doing security analysis yourself."
)

AUDITOR_INSTRUCTIONS = (
    "You are a Senior Security Auditor. Your ONLY goal is to find vulnerabilities. "
    "Workflow: "
    "1. Use 'scan_for_secrets' on the target directory to detect PII, API keys, and secrets. "
    "2. Use 'read_file' to inspect suspicious files identified by the scan. "
    "3. Use 'audit_file' on critical source files (e.g., config, auth, API "
    "handlers) for deep analysis. "
    "4. Compile a structured report with severity levels (CRITICAL/HIGH/MEDIUM/LOW). "
    "5. Hand off to the Manager with your findings. Do NOT attempt to fix issues yourself."
)

REMEDIATOR_INSTRUCTIONS = (
    "You are a Security Remediation Expert. Your ONLY goal is to fix vulnerabilities. "
    "Workflow: "
    "1. Review the audit findings provided by the Manager or Auditor. "
    "2. Use 'read_file' to inspect the current content of affected files. "
    "3. Use 'safe_write_file' to apply patches. ALWAYS provide a clear "
    "'reason' explaining the security fix. "
    "4. Verify your fix by reading the file again after writing. "
    "5. Report all changes made and hand off to the Manager. Do NOT scan for new issues."
)

MCP_CONFIG: MCPConfig = {"convert_schemas_to_strict": True}


def write_final_report(content: str) -> str:
    """Writes the final security audit report to 'security_report.md' in the current directory."""
    with open("security_report.md", "w") as f:
        f.write(content)
    return "✅ Final report saved successfully to security_report.md."


def build_agent_pool(
    model: RotatingModel,
    mcp_server: MCPServerStdio,
) -> list[Agent]:
    """Build and cross-link the Manager, Auditor, and Remediator agents.

    Returns the full agent pool with the Manager at index 0.
    """
    manager = Agent(
        name="Manager",
        instructions=MANAGER_INSTRUCTIONS,
        model=model,
        tools=[write_final_report],  # type: ignore[list-item]
        mcp_servers=[mcp_server],
        mcp_config=MCP_CONFIG,
    )

    auditor = Agent(
        name="SecurityAuditor",
        instructions=AUDITOR_INSTRUCTIONS,
        model=model,
        mcp_servers=[mcp_server],
        mcp_config=MCP_CONFIG,
    )

    remediator = Agent(
        name="SecurityRemediator",
        instructions=REMEDIATOR_INSTRUCTIONS,
        model=model,
        mcp_servers=[mcp_server],
        mcp_config=MCP_CONFIG,
    )

    # Cross-link all agents for handoff support
    agent_pool = [manager, auditor, remediator]
    for agent in agent_pool:
        agent.handoffs = [a for a in agent_pool if a != agent]

    return agent_pool
