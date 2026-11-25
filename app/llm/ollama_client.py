import json
import re
import time
import requests
from typing import Optional, List, Dict
from app.llm.base import BaseLLMClient

class OllamaClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: int = 90,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def __repr__(self) -> str:
        return (
            f"OllamaClient(base_url='{self.base_url}', model='{self.model}', "
            f"timeout={self.timeout}, max_retries={self.max_retries})"
        )

    def is_available(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=min(3, self.timeout))
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_found = any(self.model in m or m.startswith(self.model.split(":")[0]) for m in models)
                if model_found or len(models) > 0:
                    return True, f"Ollama reachable with models: {', '.join(models) if models else 'none'}"
                return True, f"Ollama reachable, but model '{self.model}' not yet pulled. Run: `ollama pull {self.model}`"
            return False, f"Ollama returned HTTP status {resp.status_code}"
        except Exception as e:
            return False, (
                f"Ollama is unavailable at {self.base_url} ({str(e)}).\n"
                "Setup instructions:\n"
                "  1. Install Ollama from https://ollama.ai\n"
                "  2. Start Ollama server: `ollama serve`\n"
                f"  3. Pull model: `ollama pull {self.model}`\n"
                "  4. Alternatively, switch to an API provider via LLM_PROVIDER=openai in .env"
            )

    def _extract_and_validate_json(self, raw_content: str) -> str:
        text = raw_content.strip()
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            candidate = text[brace_start:brace_end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start != -1 and bracket_end > bracket_start:
            candidate = text[bracket_start:bracket_end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        return text

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                if resp.status_code == 200:
                    raw_resp = resp.json().get("response", "").strip()
                    if json_mode:
                        raw_resp = self._extract_and_validate_json(raw_resp)
                    return raw_resp

                if resp.status_code in (500, 502, 503, 504) and attempt <= self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                    continue

                raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
                last_error = net_err
                if attempt <= self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                    continue
                available, msg = self.is_available()
                raise ConnectionError(f"Cannot connect to Ollama after {self.max_retries} retries: {msg}")

        raise RuntimeError(f"Ollama request failed: {last_error}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if json_mode:
            payload["format"] = "json"
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                if resp.status_code == 200:
                    raw_resp = resp.json().get("message", {}).get("content", "").strip()
                    if json_mode:
                        raw_resp = self._extract_and_validate_json(raw_resp)
                    return raw_resp

                if resp.status_code in (500, 502, 503, 504) and attempt <= self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                    continue

                raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
                last_error = net_err
                if attempt <= self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                    continue
                available, msg = self.is_available()
                raise ConnectionError(f"Cannot connect to Ollama after {self.max_retries} retries: {msg}")

        raise RuntimeError(f"Ollama request failed: {last_error}")
