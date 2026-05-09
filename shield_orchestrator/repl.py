"""Interactive REPL for the Shield Orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents import Runner

if TYPE_CHECKING:
    from agents import Agent

    from shield_orchestrator.config import DEFAULT_MODEL_POOL  # noqa: F401


async def run_repl(manager: Agent, model_pool: list[str]) -> None:
    """Run the interactive security REPL.

    Args:
        manager: The triage/manager agent that receives all user prompts.
        model_pool: The ordered list of model IDs (for display only).
    """
    print("---")
    print(f"Primary Model: {model_pool[0]}")
    print(f"Failover Pool: {', '.join(model_pool[1:])}")
    print("---")

    while True:
        try:
            prompt = input("\n[You]> ")
        except (EOFError, KeyboardInterrupt):
            print("\n[Exiting...]")
            break

        if prompt.lower() in ("exit", "quit"):
            break
        if not prompt.strip():
            continue

        print("\n[ShieldOrchestrator is processing...]")

        try:
            result = await Runner.run(manager, prompt)
            print(f"\n[Result]> {result.final_output}")
        except Exception as e:
            print(f"\n[Error during run]: {e}")
