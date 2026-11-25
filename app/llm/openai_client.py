import json
import re
import time
import requests
from typing import Optional, List, Dict
from app.llm.base import BaseLLMClient

class OpenAICompatibleClient(BaseLLMClient):
    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_base = (api_base or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def __repr__(self) -> str:
        masked_key = self._mask_key(self.api_key)
        return (
            f"OpenAICompatibleClient(api_base='{self.api_base}', "
            f"model='{self.model}', api_key='{masked_key}', "
            f"timeout={self.timeout}, max_retries={self.max_retries})"
        )

    @staticmethod
    def _mask_key(key: Optional[str]) -> str:
        if not key:
            return "<none>"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    def _sanitize_error(self, err_text: str) -> str:
        if self.api_key and len(self.api_key) > 4:
            return err_text.replace(self.api_key, self._mask_key(self.api_key))
        return err_text

    def is_available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "OPENAI_API_KEY is not set."
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(f"{self.api_base}/models", headers=headers, timeout=min(5, self.timeout))
            if resp.status_code == 200:
                return True, f"OpenAI compatible API reachable at {self.api_base}"
            sanitized = self._sanitize_error(resp.text)
            return False, f"OpenAI API check failed with status {resp.status_code}: {sanitized}"
        except Exception as e:
            return False, f"OpenAI API connection error: {self._sanitize_error(str(e))}"

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

    def _extract_and_validate_json(self, raw_content: str) -> str:
        text = raw_content.strip()
        # Direct check
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Check markdown fences: ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        # Try to locate opening and closing braces or brackets
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

        # Return stripped text if no JSON structure recovered
        return text

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

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    if json_mode:
                        content = self._extract_and_validate_json(content)
                    return content

                sanitized_body = self._sanitize_error(resp.text)
                # Transient errors: 429 (rate limit), 500, 502, 503, 504
                if resp.status_code in (429, 500, 502, 503, 504) and attempt <= self.max_retries:
                    backoff = self.retry_delay * (2 ** (attempt - 1))
                    time.sleep(backoff)
                    continue

                raise RuntimeError(f"OpenAI API error ({resp.status_code}): {sanitized_body}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
                last_error = net_err
                if attempt <= self.max_retries:
                    backoff = self.retry_delay * (2 ** (attempt - 1))
                    time.sleep(backoff)
                    continue
                raise RuntimeError(
                    f"OpenAI connection error after {self.max_retries} retries: {self._sanitize_error(str(net_err))}"
                )
            except Exception as e:
                raise RuntimeError(f"OpenAI request failed: {self._sanitize_error(str(e))}")

        if last_error:
            raise RuntimeError(f"OpenAI request failed after retries: {self._sanitize_error(str(last_error))}")
        raise RuntimeError("OpenAI request failed with unknown error.")
