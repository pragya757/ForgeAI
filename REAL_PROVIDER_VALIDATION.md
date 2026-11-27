# ForgeAI — Real-LLM Provider Architecture & Validation Audit

**Audit Date:** November 28, 2026  
**Auditor:** Antigravity Autonomous Audit Suite  
**Commit Inspected:** `fa6487e` (pushed to `origin/main`)  
**Status:** **REAL-PROVIDER VALIDATION BLOCKED (Credentials Unavailable)**

---

## Executive Summary

This audit evaluates the LLM provider layer of ForgeAI across its factory, evaluator, optimizer, and runtime pipelines. We verified provider abstractions, environment variable handling, API key validation, error propagation policies, and fallback behaviors for OpenAI, Ollama, and Mock implementations.

### Critical Status Finding: Real-Provider Validation Blocked
Per explicit audit mandate (*"If credentials are unavailable, stop and report that real-provider validation is blocked"*):
1. **OpenAI (`OPENAI_API_KEY`):** Unset in the system environment.
2. **Ollama (`OLLAMA_BASE_URL`):** Inactive on default `http://localhost:11434` (`Connection refused`).
3. **Execution Block:** Because valid API credentials and live model server endpoints are absent in the test environment, **live evaluation against external LLM providers is formally blocked**.
4. **Behavioral Invariant:** No mock responses have been relabeled as real-provider results.

---

## 1. Provider Architecture & Configuration Matrix

ForgeAI manages model access through a centralized factory pattern defined in `app/llm/factory.py`, implementing the abstract base interface in `app/llm/base.py`.

```
                        +---------------------------+
                        |     get_llm_client()      |
                        |   (app/llm/factory.py)    |
                        +-------------+-------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
  LLM_PROVIDER=openai          LLM_PROVIDER=ollama          LLM_PROVIDER=mock
         |                            |                            |
         v                            v                            v
+------------------+         +------------------+         +------------------+
| OpenAIClient     |         | OllamaClient     |         | MockLLMClient    |
| (openai_client)  |         | (ollama_client)  |         | (mock_client)    |
+------------------+         +------------------+         +------------------+
         |                            |                            |
         | (Auth / Net Fail)          | (Conn Fail)                | (Deterministic)
         v                            v                            v
   [Fallback Guard]             [Fallback Guard]             [Deterministic Engine]
         |                            |                            |
         +-------------+--------------+                            |
                       |                                           |
             LLM_ALLOW_FALLBACK=true                               |
                       |                                           |
                       v                                           |
           [MockLLMClient: Fallback] <-----------------------------+
```

### Configuration Environment Variables

| Variable | Type / Default | Role in Provider Routing | Strict Mode Behavior (`LLM_ALLOW_FALLBACK=false`) |
| :--- | :--- | :--- | :--- |
| `LLM_PROVIDER` | string (`"mock"`) | Primary selector: `"openai"`, `"ollama"`, or `"mock"`. | Determines class instantiated. |
| `OPENAI_API_KEY` | string (unset) | Authentication secret for OpenAI API v1 endpoints. | Missing key raises `ValueError` immediately. |
| `OPENAI_BASE_URL` | string (`None`) | Custom base URL for OpenAI-compatible gateways. | Used for vLLM / LiteLLM proxy routing. |
| `OPENAI_MODEL` | string (`"gpt-4o-mini"`) | Model target for OpenAI completions. | Injected into API payload. |
| `OLLAMA_BASE_URL` | string (`"http://localhost:11434"`) | Base URL for local Ollama HTTP REST daemon. | Connection failure raises `ConnectionError`. |
| `OLLAMA_MODEL` | string (`"llama3.1:8b"`) | Local model tag for Ollama `/api/generate` / `/api/chat`. | Target parameter in POST body. |
| `LLM_ALLOW_FALLBACK` | bool string (`"true"`) | Determines if provider failures silently degrade to mock. | When `"false"`, exceptions halt the pipeline. |

---

## 2. Silent Fallback Vulnerability Analysis

### The Silent Fallback Mechanism
In `app/llm/factory.py`, the fallback logic is structured as follows:

```python
# app/llm/factory.py lines 34-45
allow_fallback = os.getenv("LLM_ALLOW_FALLBACK", "true").lower() in ("true", "1", "yes")

if provider == "openai":
    try:
        from app.llm.openai_client import OpenAIClient
        return OpenAIClient(...)
    except Exception as exc:
        if allow_fallback:
            logger.warning("OpenAI client failed to initialize: %s. Falling back to MockLLMClient.", exc)
            return MockLLMClient(model_name="mock-fallback-v1")
        raise
```

### Risk Assessment & Audit Finding
1. **Silent Degradation Risk:** When `LLM_ALLOW_FALLBACK="true"` (the default), if a developer configures `LLM_PROVIDER=openai` but misconfigures their API key, the system logs a warning and returns `MockLLMClient(model_name="mock-fallback-v1")`. The pipeline continues without hard failure, which could mislead an operator into believing an agent was synthesized or judged by GPT-4o.
2. **Strict Enforcement Verification:** We verified via automated tests (`tests/test_real_llm_providers.py`) that setting `LLM_ALLOW_FALLBACK="false"` successfully disables silent fallback:
   - Requesting `LLM_PROVIDER=openai` without an API key raises `ValueError: OpenAI API key is missing or invalid.`
   - Requesting `LLM_PROVIDER=ollama` with an inactive daemon raises `ConnectionError: Ollama server unreachable at http://localhost:11434`.

---

## 3. End-to-End Pipeline Routing Audit

We audited all 7 stages of the ForgeAI pipeline to verify whether `get_llm_client()` is uniformly respected:

| Pipeline Stage | Module File | LLM Client Resolution | Direct Provider Routing Verified? |
| :--- | :--- | :--- | :--- |
| **1. Intake Interviewer** | `app/factory/intake_interviewer.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Uses caller's specified provider. |
| **2. Groundability Guard** | `app/factory/groundability_guard.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Routes claim verification through provider. |
| **3. Agent Generator** | `app/factory/agent_generator.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Synthesizes instructions via provider. |
| **4. Eval Generator** | `app/factory/eval_generator.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Synthesizes 20 diverse cases via provider. |
| **5. Runner / Runtime** | `app/runtime/agent_runtime.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Generates answers with retrieval context. |
| **6. Judge Evaluator** | `app/evaluator/judge.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Performs 6-dimensional evaluation. |
| **7. Critic Optimizer** | `app/factory/critic_optimizer.py` | `llm_client = get_llm_client(provider, ...)` | **YES** — Diagnoses failures and mutates prompts. |

**Observation:** There is no hardcoded fallback or bypass in any stage. When a valid provider client is supplied, it is passed down and executed consistently.

---

## 4. Verification Test Suite Results

The provider integration suite (`tests/test_real_llm_providers.py`) was executed to verify provider handling:

```bash
.venv/bin/pytest tests/test_real_llm_providers.py -v
```

```
tests/test_real_llm_providers.py::test_mock_provider_instantiation PASSED
tests/test_real_llm_providers.py::test_openai_provider_missing_key_strict_raises PASSED
tests/test_real_llm_providers.py::test_openai_provider_missing_key_fallback_warns PASSED
tests/test_real_llm_providers.py::test_ollama_provider_unreachable_strict_raises PASSED
tests/test_real_llm_providers.py::test_ollama_provider_unreachable_fallback_warns PASSED
tests/test_real_llm_providers.py::test_pipeline_rejects_silent_fallback_when_strict PASSED
tests/test_real_llm_providers.py::test_runtime_honors_configured_provider PASSED
tests/test_real_llm_providers.py::test_judge_honors_configured_provider PASSED

======================== 8 passed in 0.42s ========================
```

---

## 5. Architectural Recommendations

1. **Default `LLM_ALLOW_FALLBACK` to `false` in Production:**  
   In production environments and benchmarking runs, silent fallback should be prohibited by default to ensure all artifacts and scores reflect the intended model.
2. **Surface Provider Badges in Dashboard:**  
   The Streamlit UI header should display an explicit indicator (`Provider: OpenAI (gpt-4o)` vs `Provider: Mock Engine`) alongside the active Run ID, preventing accidental confusion between mock simulation and live inference.
