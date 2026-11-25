import json
import requests
from typing import Optional, List, Dict
from app.llm.base import BaseLLMClient

class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> tuple[bool, str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check if configured model or prefix matches
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

        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text}")
            return resp.json().get("response", "").strip()
        except requests.exceptions.ConnectionError:
            available, msg = self.is_available()
            raise ConnectionError(f"Cannot connect to Ollama: {msg}")

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

        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text}")
            return resp.json().get("message", {}).get("content", "").strip()
        except requests.exceptions.ConnectionError:
            available, msg = self.is_available()
            raise ConnectionError(f"Cannot connect to Ollama: {msg}")
