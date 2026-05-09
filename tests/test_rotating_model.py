from unittest.mock import AsyncMock, MagicMock

import pytest

from shield_orchestrator.models import ModelPoolExhaustedError, RotatingModel


@pytest.mark.asyncio
async def test_rotating_model_success():
    # Setup
    mock_client = MagicMock()
    model_ids = ["model-1", "model-2"]
    
    # We mock the internal _models list directly to avoid complex initialization
    rotating_model = RotatingModel(model_ids, mock_client)
    
    mock_model_1 = AsyncMock()
    mock_model_1.get_response.return_value = "Success from model 1"
    
    mock_model_2 = AsyncMock()
    
    rotating_model._models = [mock_model_1, mock_model_2]
    
    # Execution
    response = await rotating_model.get_response("test prompt")
    
    # Assertion
    assert response == "Success from model 1"
    assert rotating_model.index == 0
    mock_model_1.get_response.assert_called_once()
    mock_model_2.get_response.assert_not_called()

@pytest.mark.asyncio
async def test_rotating_model_failover_on_429():
    # Setup
    mock_client = MagicMock()
    model_ids = ["model-1", "model-2"]
    
    rotating_model = RotatingModel(model_ids, mock_client)
    
    # Model 1 will fail with 429
    mock_model_1 = AsyncMock()
    mock_model_1.get_response.side_effect = Exception("Rate limit exceeded (429)")
    
    # Model 2 will succeed
    mock_model_2 = AsyncMock()
    mock_model_2.get_response.return_value = "Success from model 2"
    
    rotating_model._models = [mock_model_1, mock_model_2]
    
    # Execution
    response = await rotating_model.get_response("test prompt")
    
    # Assertion
    assert response == "Success from model 2"
    assert rotating_model.index == 1
    mock_model_1.get_response.assert_called_once()
    mock_model_2.get_response.assert_called_once()

@pytest.mark.asyncio
async def test_rotating_model_fatal_error():
    # Setup
    mock_client = MagicMock()
    model_ids = ["model-1", "model-2"]
    
    rotating_model = RotatingModel(model_ids, mock_client)
    
    # Model 1 will fail with 400 (Fatal)
    mock_model_1 = AsyncMock()
    mock_model_1.get_response.side_effect = Exception("Bad Request (400)")
    
    mock_model_2 = AsyncMock()
    
    rotating_model._models = [mock_model_1, mock_model_2]
    
    # Execution & Assertion
    with pytest.raises(Exception, match="400"):
        await rotating_model.get_response("test prompt")
    
    assert rotating_model.index == 0 # Should not have rotated
    mock_model_1.get_response.assert_called_once()
    mock_model_2.get_response.assert_not_called()

@pytest.mark.asyncio
async def test_rotating_model_all_exhausted():
    # Setup
    mock_client = MagicMock()
    model_ids = ["model-1", "model-2"]
    
    rotating_model = RotatingModel(model_ids, mock_client)
    
    # All models fail with 429
    mock_model_1 = AsyncMock()
    mock_model_1.get_response.side_effect = Exception("429 Too Many Requests")
    
    mock_model_2 = AsyncMock()
    mock_model_2.get_response.side_effect = Exception("resource_exhausted")
    
    rotating_model._models = [mock_model_1, mock_model_2]
    
    # Execution & Assertion
    with pytest.raises(ModelPoolExhaustedError, match="All models in the pool have reached their rate limits"):
        await rotating_model.get_response("test prompt")
    
    assert mock_model_1.get_response.call_count == 1
    assert mock_model_2.get_response.call_count == 1

@pytest.mark.asyncio
async def test_rotating_model_stream_success():
    # Setup
    mock_client = MagicMock()
    model_ids = ["model-1"]

    rotating_model = RotatingModel(model_ids, mock_client)

    # stream_response is now an async generator, so the delegate must also yield
    async def mock_stream(*args, **kwargs):
        yield "chunk-1"
        yield "chunk-2"

    mock_model_1 = MagicMock()
    mock_model_1.stream_response = mock_stream

    rotating_model._models = [mock_model_1]

    # Execution — collect chunks from the async generator
    chunks = [chunk async for chunk in rotating_model.stream_response("test prompt")]

    # Assertion
    assert chunks == ["chunk-1", "chunk-2"]

@pytest.mark.asyncio
async def test_rotating_model_model_id_property():
    """model_id should return the currently active model identifier."""
    mock_client = MagicMock()
    model_ids = ["model-alpha", "model-beta"]
    
    rotating_model = RotatingModel(model_ids, mock_client)
    assert rotating_model.model_id == "model-alpha"
    
    rotating_model.index = 1
    assert rotating_model.model_id == "model-beta"

@pytest.mark.asyncio
async def test_rotating_model_is_rate_limit_error():
    """Helper should detect various rate limit error patterns."""
    assert RotatingModel._is_rate_limit_error(Exception("429 Too Many Requests"))
    assert RotatingModel._is_rate_limit_error(Exception("RESOURCE_EXHAUSTED"))
    assert RotatingModel._is_rate_limit_error(Exception("rate limit exceeded"))
    assert not RotatingModel._is_rate_limit_error(Exception("Bad Request 400"))
    assert not RotatingModel._is_rate_limit_error(Exception("Internal Server Error"))
