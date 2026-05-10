"""RotatingModel: Failover-aware model wrapper for rate-limit resilience."""

from collections.abc import AsyncIterator
from typing import Any

from agents import OpenAIChatCompletionsModel
from agents.models.interface import Model
from openai import AsyncOpenAI


class ModelPoolExhaustedError(RuntimeError):
    """Raised when every model in the pool has been rate-limited."""


class RotatingModel(Model):
    """
    Stays with the same model until a Rate Limit (429) is encountered,
    then fails over to the next model in the pool.
    """

    def __init__(self, model_ids: list[str], client: AsyncOpenAI):
        self.model_ids = model_ids
        self.client = client
        self.index = 0
        self._models = [OpenAIChatCompletionsModel(model=mid, openai_client=client) for mid in model_ids]

    @property
    def model_id(self) -> str:
        """Return the currently active model identifier."""
        return self.model_ids[self.index]

    def _get_current_model(self) -> OpenAIChatCompletionsModel:
        return self._models[self.index]

    @staticmethod
    def _is_rate_limit_error(e: Exception) -> bool:
        """Check if an exception indicates a rate limit / resource exhaustion."""
        err_str = str(e).lower()
        return any(key in err_str for key in ["429", "resource_exhausted", "rate limit"])

    async def get_response(self, *args, **kwargs):
        attempts = 0
        while attempts < len(self._models):
            model = self._get_current_model()
            try:
                return await model.get_response(*args, **kwargs)
            except Exception as e:
                if self._is_rate_limit_error(e):
                    print(f"[RotatingModel] ⚠️ Rate Limit hit for {self.model_ids[self.index]}.")
                    self.index = (self.index + 1) % len(self._models)
                    print(f"[RotatingModel] 🔄 Failing over to: {self.model_ids[self.index]}")
                    attempts += 1
                    continue
                # For any other fatal errors (400, etc.), raise immediately
                raise

        raise ModelPoolExhaustedError("❌ All models in the pool have reached their rate limits. Please wait a minute.")

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator:  # type: ignore[override]
        """Stream with failover: retries on 429 only if no chunks have been yielded yet."""
        attempts = 0
        while attempts < len(self._models):
            model = self._get_current_model()
            yielded_any = False
            try:
                async for chunk in model.stream_response(*args, **kwargs):
                    yield chunk
                    yielded_any = True
                return
            except Exception as e:
                if self._is_rate_limit_error(e):
                    if yielded_any:
                        print(
                            f"[RotatingModel] ⚠️ Rate Limit hit mid-stream for "
                            f"{self.model_ids[self.index]}. Cannot cleanly failover."
                        )
                        raise
                    print(f"[RotatingModel] ⚠️ Stream Rate Limit hit for {self.model_ids[self.index]}.")
                    self.index = (self.index + 1) % len(self._models)
                    print(f"[RotatingModel] 🔄 Stream failing over to: {self.model_ids[self.index]}")
                    attempts += 1
                    continue
                raise
        raise ModelPoolExhaustedError("❌ All models in the pool have reached their rate limits during streaming.")
