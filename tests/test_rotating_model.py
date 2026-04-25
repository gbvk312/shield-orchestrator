import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from main import RotatingModel

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
    with pytest.raises(Exception, match="All models in the pool have reached their rate limits"):
        await rotating_model.get_response("test prompt")
    
    assert mock_model_1.get_response.call_count == 1
    assert mock_model_2.get_response.call_count == 1

@pytest.mark.asyncio
async def test_rotating_model_stream_success():
    # Setup
    mock_client = MagicMock()
    model_ids = ["model-1"]
    
    rotating_model = RotatingModel(model_ids, mock_client)
    
    mock_model_1 = AsyncMock()
    mock_iterator = AsyncMock()
    mock_model_1.stream_response.return_value = mock_iterator
    
    rotating_model._models = [mock_model_1]
    
    # Execution
    response_stream = await rotating_model.stream_response("test prompt")
    
    # Assertion
    assert response_stream == mock_iterator
    mock_model_1.stream_response.assert_called_once()
