"""Provider factory resolving the active LLMProvider instance.

Selects between LlamaCppProvider and MockLLMProvider based strictly on explicit
user configuration. Never silently falls back between real and mock modes.
"""

from __future__ import annotations

from pathlib import Path

from sarthika_code.domain.config import AppSettings
from sarthika_code.llm.base import LLMProvider
from sarthika_code.llm.llama_cpp import LlamaCppProvider
from sarthika_code.llm.manager import LlamaServerManager
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.utils.logging import get_logger

logger = get_logger("LLMProviderFactory")


class LLMProviderFactory:
    """Factory for resolving and instantiating LLMProvider instances."""

    @staticmethod
    def create_provider(
        settings: AppSettings,
        server_manager: LlamaServerManager | None = None,
    ) -> LLMProvider:
        """Create the appropriate LLMProvider based on explicit settings.

        Guarantees:
        - Never silently switches from real mode to mock mode.
        - Clearly distinguishes between MockLLMProvider and LlamaCppProvider.
        """
        if settings.mock_mode:
            logger.info("Initializing MockLLMProvider (Mock Mode explicitly enabled).")
            return MockLLMProvider()

        # Real local server provider
        target_url = f"http://{settings.server_host}:{settings.server_port}"
        if server_manager is not None and server_manager.status.url:
            target_url = server_manager.status.url

        model_name = "local-model"
        if settings.model_path:
            model_name = Path(settings.model_path).name

        logger.info("Initializing LlamaCppProvider pointing to %s (%s).", target_url, model_name)
        return LlamaCppProvider(
            base_url=target_url,
            server_manager=server_manager,
            model_name=model_name,
        )
