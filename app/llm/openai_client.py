import json
import requests
from typing import Optional, List, Dict
from app.llm.base import BaseLLMClient

class OpenAICompatibleClient(BaseLLMClient):
    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_base = (api_base or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or ""
        self.model = model

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "OPENAI_API_KEY is not set."
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(f"{self.api_base}/models", headers=headers, timeout=5)
            if resp.status_code == 200:
                return True, f"OpenAI compatible API reachable at {self.api_base}"
            return False, f"OpenAI API check failed with status {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, f"OpenAI API connection error: {str(e)}"

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, json_mode=json_mode, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens:
            payload["max_tokens"] = max_tokens

        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
