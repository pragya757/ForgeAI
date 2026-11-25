import pytest
from unittest.mock import patch, MagicMock
from app.llm.openai_client import OpenAICompatibleClient
from app.llm.ollama_client import OllamaClient
from app.llm.factory import get_llm_client
from app.llm.mock_client import MockLLMClient

def test_openai_client_masking():
    client = OpenAICompatibleClient(api_key="sk-secret-123456789-key", model="gpt-4o-mini")
    rep = repr(client)
    assert "sk-secret-123456789-key" not in rep
    assert "sk-s...-key" in rep

    short_client = OpenAICompatibleClient(api_key="short", model="gpt-4o-mini")
    assert "****" in repr(short_client)
    assert "short" not in repr(short_client)

def test_openai_client_retry_on_429():
    client = OpenAICompatibleClient(
        api_base="https://api.test.com/v1",
        api_key="test-key-12345",
        timeout=5,
        max_retries=2,
        retry_delay=0.01,
    )
    
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Rate limit exceeded"

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "choices": [{"message": {"content": "Resolved after backoff"}}]
    }

    with patch("requests.post", side_effect=[mock_resp_429, mock_resp_200]) as mock_post:
        result = client.chat([{"role": "user", "content": "Hello"}])
        assert result == "Resolved after backoff"
        assert mock_post.call_count == 2

def test_openai_client_max_retries_exhausted():
    client = OpenAICompatibleClient(
        api_base="https://api.test.com/v1",
        api_key="super-secret-key-9999",
        timeout=5,
        max_retries=2,
        retry_delay=0.01,
    )
    
    mock_resp_500 = MagicMock()
    mock_resp_500.status_code = 500
    mock_resp_500.text = "Internal Server Error"

    with patch("requests.post", return_value=mock_resp_500) as mock_post:
        with pytest.raises(RuntimeError) as exc_info:
            client.chat([{"role": "user", "content": "Hello"}])
        assert "500" in str(exc_info.value)
        # Ensure api_key does not leak in error string
        assert "super-secret-key-9999" not in str(exc_info.value)
        assert mock_post.call_count == 3  # initial + 2 retries

def test_openai_client_json_extraction():
    client = OpenAICompatibleClient(api_key="dummy")
    # Clean JSON
    assert client._extract_and_validate_json('{"key": "value"}') == '{"key": "value"}'
    
    # Markdown fenced JSON
    fenced = '```json\n{"status": "ok", "count": 42}\n```'
    extracted = client._extract_and_validate_json(fenced)
    assert extracted == '{"status": "ok", "count": 42}'

    # Conversational text surrounding JSON
    embedded = 'Here is the result:\n{"verdict": "pass"}\nHope this helps!'
    extracted_embedded = client._extract_and_validate_json(embedded)
    assert extracted_embedded == '{"verdict": "pass"}'

def test_ollama_client_retry_on_503():
    client = OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2",
        timeout=5,
        max_retries=2,
        retry_delay=0.01,
    )
    
    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503
    mock_resp_503.text = "Service Unavailable"

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"message": {"content": "Ollama recovered"}}

    with patch("requests.post", side_effect=[mock_resp_503, mock_resp_200]) as mock_post:
        result = client.chat([{"role": "user", "content": "Ping"}])
        assert result == "Ollama recovered"
        assert mock_post.call_count == 2

def test_ollama_client_json_extraction():
    client = OllamaClient()
    fenced = '```\n{"name": "test", "items": [1, 2, 3]}\n```'
    extracted = client._extract_and_validate_json(fenced)
    assert extracted == '{"name": "test", "items": [1, 2, 3]}'

def test_factory_provider_selection(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    client = get_llm_client()
    assert isinstance(client, MockLLMClient)

def test_factory_fallback_behavior(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ALLOW_FALLBACK", "true")
    # Should safely fallback to MockLLMClient
    client = get_llm_client("openai")
    assert isinstance(client, MockLLMClient)

    # When fallback is disabled, should raise ConnectionError
    monkeypatch.setenv("LLM_ALLOW_FALLBACK", "false")
    with pytest.raises(ConnectionError):
        get_llm_client("openai")
