import os
from app.config import settings
from app.llm.base import BaseLLMClient
from app.llm.ollama_client import OllamaClient
from app.llm.openai_client import OpenAICompatibleClient
from app.llm.mock_client import MockLLMClient

def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    selected_provider = (provider or settings.llm_provider).lower().strip()

    if selected_provider == "ollama":
        client = OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries,
            retry_delay=settings.llm_retry_delay,
        )
        # Check availability
        available, msg = client.is_available()
        if not available:
            allow_fallback = os.getenv("LLM_ALLOW_FALLBACK", "true").lower() in ("true", "1")
            if allow_fallback:
                return MockLLMClient(model_name="mock-fallback-v1")
            raise ConnectionError(
                f"Ollama is selected as the LLM provider but is unreachable.\n{msg}"
            )
        return client

    elif selected_provider in ("openai", "openai_compatible", "api"):
        client = OpenAICompatibleClient(
            api_base=settings.openai_api_base,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries,
            retry_delay=settings.llm_retry_delay,
        )
        available, msg = client.is_available()
        if not available:
            allow_fallback = os.getenv("LLM_ALLOW_FALLBACK", "true").lower() in ("true", "1")
            if allow_fallback:
                return MockLLMClient(model_name="mock-fallback-v1")
            raise ConnectionError(f"OpenAI compatible API is not properly configured:\n{msg}")
        return client

    elif selected_provider in ("mock", "test", "simulated"):
        return MockLLMClient()

    else:
        raise ValueError(f"Unknown LLM provider: '{selected_provider}'. Supported: 'ollama', 'openai', 'mock'")
