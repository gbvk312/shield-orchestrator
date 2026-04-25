import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from main import main

@pytest.mark.asyncio
async def test_main_initialization_and_exit():
    """
    Verifies that the orchestrator starts, connects to MCP (mocked), 
    processes an exit command, and shuts down gracefully.
    """
    # Mock GEMINI_API_KEY
    with patch("os.getenv", return_value="fake-key"):
        # Mock MCPServerStdio context manager
        mock_mcp_server = MagicMock()
        mock_mcp_server.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_mcp_server.__aexit__ = AsyncMock(return_value=None)
        
        with patch("main.MCPServerStdio", return_value=mock_mcp_server):
            # Mock input() to return "exit" immediately
            with patch("builtins.input", side_effect=["exit"]):
                # Mock Runner.run to avoid actual LLM calls
                with patch("agents.Runner.run", new_callable=AsyncMock) as mock_runner:
                    # Run main
                    await main()
                    
                    # Verify MCP server was initialized
                    mock_mcp_server.__aenter__.assert_called_once()
                    # Runner should not have been called since we exited immediately
                    mock_runner.assert_not_called()

@pytest.mark.asyncio
async def test_main_single_command_and_exit():
    """
    Verifies that the orchestrator can process a single command and then exit.
    """
    # Mock GEMINI_API_KEY
    with patch("os.getenv", return_value="fake-key"):
        # Mock MCPServerStdio
        mock_mcp_server = MagicMock()
        mock_mcp_server.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_mcp_server.__aexit__ = AsyncMock(return_value=None)
        
        with patch("main.MCPServerStdio", return_value=mock_mcp_server):
            # Mock input() to return a prompt then "exit"
            with patch("builtins.input", side_effect=["test audit", "exit"]):
                # Mock Runner.run
                mock_result = MagicMock()
                mock_result.final_output = "Audit complete."
                with patch("agents.Runner.run", new_callable=AsyncMock, return_value=mock_result) as mock_runner:
                    # Run main
                    await main()
                    
                    # Verify Runner.run was called with the manager and prompt
                    mock_runner.assert_called_once()
                    assert "test audit" in mock_runner.call_args[0]
