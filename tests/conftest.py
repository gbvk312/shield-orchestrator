"""Shared test fixtures for shield-orchestrator test suite."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from shield_orchestrator.models import RotatingModel


@pytest.fixture()
def mock_client() -> MagicMock:
    """A mock AsyncOpenAI client."""
    return MagicMock()


@pytest.fixture()
def mock_rotating_model(mock_client: MagicMock) -> RotatingModel:
    """A RotatingModel with two mock models pre-wired."""
    model_ids = ["model-1", "model-2"]
    rm = RotatingModel(model_ids, mock_client)

    mock_model_1 = AsyncMock()
    mock_model_2 = AsyncMock()
    rm._models = [mock_model_1, mock_model_2]

    return rm
