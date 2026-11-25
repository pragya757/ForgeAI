from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from pydantic import BaseModel

class LLMMessage(BaseModel):
    role: str
    content: str

class BaseLLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        """Generate response from a chat conversation."""
        pass

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Check if LLM backend is reachable and configured."""
        pass
