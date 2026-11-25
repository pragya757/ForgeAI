# ForgeAI – Real LLM Architecture and Integration Audit

**Document Version:** 1.0  
**Phase:** Phase 7 Validation  
**Date:** 2026-11-26  
**Auditor:** Senior GenAI Architect & Security Reviewer  

---

## Executive Summary

ForgeAI was engineered with an abstracted LLM client architecture (`BaseLLMClient`), allowing uniform invocation across factory modules (Intake Interviewer, Groundability Guard, Agent Generator, Evaluation Generator, Automated Judge, Critic–Optimizer) and the generic runtime agent runner (`ChatRunner`).

This audit evaluated:
1. Provider decoupling and architectural conformity across `app/llm/`, `app/factory/`, and `app/runtime/`.
2. Provider implementations (`OpenAICompatibleClient`, `OllamaClient`, and `MockLLMClient`).
3. Configuration management, timeouts, exponential backoff retries, and rate limit handling.
4. Security protections: credential sanitization, secret masking in logs and exceptions, and JSON extraction resilience.

---

## 1. Architectural Inspection & Provider Mapping

### 1.1 Common Interface (`BaseLLMClient`)
All LLM providers inherit from the abstract base class `BaseLLMClient` defined in [base.py](file:///Users/pragya/Downloads/OceanAI/app/llm/base.py):

```python
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
```

### 1.2 Module-by-Module Client Instantiation
Every factory component and runtime runner accepts an optional `llm_client: Optional[BaseLLMClient] = None`. When omitted, they invoke `get_llm_client()` from `app.llm`:

| Component | File Path | LLM Instantiation Pattern | Configurable Model / Provider |
| :--- | :--- | :--- | :--- |
| **Intake Interviewer** | `app/factory/interviewer.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Groundability Guard** | `app/factory/groundability.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Agent Generator** | `app/factory/agent_generator.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Eval Generator** | `app/factory/eval_generator.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Automated Judge** | `app/factory/judge.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Critic–Optimizer** | `app/factory/critic_optimizer.py`| `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Factory Pipeline** | `app/factory/pipeline.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |
| **Chat Runner** | `app/runtime/chat_runner.py` | `self.llm = llm_client or get_llm_client()` | Yes (`LLM_PROVIDER`, env vars) |

**Audit Verdict:** No module hardcodes `MockLLMClient` in production paths. Production components dynamically resolve the configured provider through the central factory.

---

## 2. Configuration & Parameter Matrix

All configurations are managed declaratively in [app/config.py](file:///Users/pragya/Downloads/OceanAI/app/config.py) using Pydantic Settings, backed by environment variables:

| Setting Parameter | Environment Variable | Default Value | Purpose |
| :--- | :--- | :--- | :--- |
| `llm_provider` | `LLM_PROVIDER` | `"ollama"` | Selects backend: `ollama`, `openai`, `mock` |
| `ollama_base_url` | `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama daemon endpoint |
| `ollama_model` | `OLLAMA_MODEL` | `"llama3.2"` | Model name for local inference |
| `openai_api_base` | `OPENAI_API_BASE` | `"https://api.openai.com/v1"`| Any OpenAI-compatible endpoint |
| `openai_api_key` | `OPENAI_API_KEY` | `None` | Authentication bearer token |
| `openai_model` | `OPENAI_MODEL` | `"gpt-4o-mini"` | Target model identifier |
| `llm_request_timeout`| `LLM_REQUEST_TIMEOUT` | `60` (seconds) | HTTP network timeout threshold |
| `llm_max_retries` | `LLM_MAX_RETRIES` | `3` | Maximum retry attempts for transient errors |
| `llm_retry_delay` | `LLM_RETRY_DELAY` | `1.0` (second) | Base backoff factor for exponential backoff |

---

## 3. Resilience, Error Handling, and Retries

### 3.1 Rate Limiting (HTTP 429) & Transient Server Errors (HTTP 5xx)
`OpenAICompatibleClient` and `OllamaClient` implement exponential backoff retry loops:
$$\text{delay} = \text{retry\_delay} \times 2^{(\text{attempt} - 1)}$$

- **Target Status Codes for Retry:**
  - `429 Too Many Requests`: Handled automatically with backoff.
  - `500 Internal Server Error`, `502 Bad Gateway`, `503 Service Unavailable`, `504 Gateway Timeout`.
  - Network timeouts (`requests.exceptions.Timeout`) and connection interruptions.
- **Fail-Safe Exhaustion:**
  If errors persist after `max_retries` (default 3), a descriptive `RuntimeError` is raised indicating status code and sanitized error response.

### 3.2 Robust JSON Extraction & Repair
LLMs occasionally wrap structured JSON outputs in Markdown code fences (e.g. ````json ... ````) or prefix/suffix conversational pleasantries. Both real providers incorporate `_extract_and_validate_json`:
1. Attempts direct `json.loads(text)`.
2. If failed, extracts content between ````json ... ```` or ```` ... ```` fences.
3. If still unparsed, scans for outermost braces `{ ... }` or brackets `[ ... ]`.
4. Guarantees that valid JSON payloads are passed to calling factory schemas.

---

## 4. Security & Credential Protection

### 4.1 Secret Masking in String Representations
Inspecting objects in REPL, debuggers, or logging statements must never expose the raw API key.
- `OpenAICompatibleClient.__repr__`:
  - Keys $> 8$ characters: displays prefix and suffix (e.g., `sk-s...-key`).
  - Keys $\le 8$ characters: displays `****`.
  - Missing keys: displays `<none>`.

### 4.2 Error Message Sanitization
- `_sanitize_error(err_text)` actively redacts occurrences of the raw `api_key` from HTTP error bodies and network exception messages before propagating exceptions to logs or UI panes.
- Authorization headers (`Bearer <token>`) are stripped from diagnostic outputs.

---

## 5. Host Environment Status & Fallback Behavior

A physical audit of the execution host environment was performed:
1. **Ollama Status:**
   - Command `which ollama` returned exit code 1 (not installed).
   - Port 11434 is unreachable (`Connection refused`).
2. **OpenAI / API Status:**
   - `OPENAI_API_KEY` is not present in the local environment.
3. **Graceful Fallback Mechanism:**
   - `app/llm/factory.py` implements an explicit fallback switch:
     ```python
     allow_fallback = os.getenv("LLM_ALLOW_FALLBACK", "true").lower() in ("true", "1")
     if allow_fallback:
         return MockLLMClient(model_name="mock-fallback-v1")
     ```
   - When `LLM_ALLOW_FALLBACK=false`, the factory raises an informative `ConnectionError` with step-by-step setup instructions for Ollama or OpenAI configuration.

---

## 6. Audit Summary

| Audit Item | Status | Verification Reference |
| :--- | :--- | :--- |
| Uniform `BaseLLMClient` Abstraction | **VERIFIED** | All 8 factory/runtime callers conform |
| Dynamic Provider Selection | **VERIFIED** | `get_llm_client()` supports `ollama`, `openai`, `mock` |
| Configurable Timeouts & Tokens | **VERIFIED** | `app/config.py` settings plumbed to request payloads |
| Exponential Backoff (429 / 5xx) | **VERIFIED** | Verified by unit tests in `tests/test_real_llm_providers.py` |
| Credential Redaction & Masking | **VERIFIED** | Masked in `__repr__` and exception strings |
| Robust JSON Mode Extraction | **VERIFIED** | Strips Markdown fences and conversational wrappers |
| Host Real Provider Live State | **PENDING CREDENTIALS** | Verified locally via mock simulation and unit tests |
