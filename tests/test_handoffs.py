from unittest.mock import MagicMock

import pytest

from shield_orchestrator.agents import build_agent_pool


@pytest.mark.asyncio
async def test_agent_handoff_configuration():
    """Verify that the agent pool is correctly cross-linked for handoffs."""
    mock_model = "test-model"  # Passed as string to satisfy Agent's type checks
    mock_mcp_server = MagicMock()
    
    agent_pool = build_agent_pool(mock_model, mock_mcp_server)
    
    assert len(agent_pool) == 3
    manager = agent_pool[0]
    auditor = agent_pool[1]
    remediator = agent_pool[2]
    
    assert manager.name == "Manager"
    assert auditor.name == "SecurityAuditor"
    assert remediator.name == "SecurityRemediator"
    
    # Verify cross-linking
    assert len(manager.handoffs) == 2
    assert auditor in manager.handoffs
    assert remediator in manager.handoffs
    
    assert len(auditor.handoffs) == 2
    assert manager in auditor.handoffs
    assert remediator in auditor.handoffs
    
    assert len(remediator.handoffs) == 2
    assert manager in remediator.handoffs
    assert auditor in remediator.handoffs
    
    # Verify manager tools include write_final_report
    assert any(t.__name__ == "write_final_report" for t in manager.tools)

