# ForgeAI: The Agent That Builds Agents
### OceanAI Jr. GenAI Engineer Campus Recruitment Assignment

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![FAISS](https://img.shields.io/badge/FAISS-CPU-blueviolet.svg)](https://github.com/facebookresearch/faiss)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.10%2B-e92063.svg)](https://docs.pydantic.dev/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42%2B-FF4B4B.svg)](https://streamlit.io/)
[![Pytest](https://img.shields.io/badge/pytest-Passing%20(21%2F21)-brightgreen.svg)](https://docs.pytest.org/)

---

## 1. Executive Summary

**ForgeAI** is an autonomous AI Agent Factory. It accepts:
1. A **one-paragraph natural language description** of the desired AI agent.
2. A **folder containing relevant documents** (PDF, TXT, CSV, Markdown).

Without modifying any source code, ForgeAI autonomously:
- Inspects document text and extracts metadata (formats, pages, tokens, inventory).
- Formulates up to 5 clarifying questions or applies documented conservative defaults.
- Verifies topic groundability to prevent unsupported requirements from being included.
- Selects strictly required tools from a secure, allowlisted tool registry.
- Generates a declarative, Pydantic-validated `agent_definition.json`.
- Synthesizes at least 20 evaluation test cases categorized into **Answerable**, **Out-of-Scope**, and **Edge Cases** directly traceable to source documents.
- Evaluates the generated agent using a hybrid deterministic + LLM judge.
- Classifies failures into six root causes and applies targeted parameter and prompt optimizations.
- Limits optimization to a maximum of **three iterations** with early stopping.
- Produces honest scorecards, iteration diagnostic logs, and a final Markdown quality report.
- Deploys the generated agent to a generic chat runner and interactive Streamlit UI.

---

## 2. Architecture & Nine Mandatory Modules

```
ForgeAI/
│
├── app/
│   ├── config.py                       # Pydantic configuration & env variable loader
│   ├── main.py                         # FastAPI REST endpoints
│   │
│   ├── factory/                        # Factory Architecture Pipeline
│   │   ├── interviewer.py              # Module 1: Intake Interviewer
│   │   ├── groundability.py            # Module 2: Groundability Guard
│   │   ├── agent_generator.py          # Module 3: Declarative Agent Generator
│   │   ├── eval_generator.py           # Module 4: Automatic Evaluation Generator (>=20 cases)
│   │   ├── judge.py                    # Module 5: Hybrid Automated Judge
│   │   ├── critic_optimizer.py         # Module 6: Critic-Optimizer Loop (Max 3 iterations)
│   │   ├── reporter.py                 # Module 7: Honest Report Generator
│   │   └── pipeline.py                 # Master Orchestration Pipeline
│   │
│   ├── retrieval/                      # High-Performance Retrieval Engine
│   │   ├── document_loader.py          # Multi-format ingestion (PDF, TXT, CSV)
│   │   ├── chunker.py                  # Sentence-boundary aware overlapping chunker
│   │   ├── embeddings.py               # SentenceTransformers with thread-safe Mac ARM support
│   │   └── retriever.py                # FAISS vector store with cosine thresholding
│   │
│   ├── tools/                          # Allowlisted Tool Registry
│   │   ├── registry.py                 # Tool registration, discovery, allowlist validation
│   │   ├── csv_lookup.py               # Safe tabular catalog searching & filtering
│   │   ├── calculator.py               # Safe AST mathematical evaluation
│   │   ├── weather.py                  # Public Open-Meteo weather API integration
│   │   └── current_date.py             # ISO date, time, weekday, and year provider
│   │
│   ├── runtime/
│   │   └── chat_runner.py              # Module 8: Generic Chat Runner & Tool Dispatcher
│   │
│   ├── llm/                            # Pluggable LLM Abstraction
│   │   ├── base.py                     # Abstract Base LLM interface
│   │   ├── ollama_client.py            # Local Ollama client (default)
│   │   ├── openai_client.py            # OpenAI-compatible API adapter
│   │   ├── mock_client.py              # Deterministic test harness client
│   │   └── factory.py                  # LLM provider factory
│   │
│   ├── prompts/                        # System prompt templates
│   │   ├── interviewer.txt
│   │   ├── groundability.txt
│   │   ├── agent_generator.txt
│   │   ├── eval_generator.txt
│   │   ├── judge.txt
│   │   └── optimizer.txt
│   │
│   └── schemas/                        # Strict Pydantic Data Contracts
│       ├── requirements.py             # requirements.json schema
│       ├── groundability.py            # groundability_report.json schema
│       ├── agent_definition.py         # agent_definition.json schema
│       ├── evaluation.py               # eval_set.json schema
│       └── scorecard.py                # scorecards.json & iteration_logs.json schema
│
├── demos/                              # Module 9: Two Complete Demonstrations
│   ├── hr_assistant/                   # Demo 1: HR Policy Assistant
│   │   ├── documents/                  # leave_policy.pdf, attendance_policy.pdf, employee_handbook.pdf
│   │   ├── artifacts/                  # Generated artifacts (requirements, definition, scorecards, report)
│   │   ├── generate_docs.py            # Synthetic document generator script
│   │   └── generation_prompts.txt      # Source prompts used for document generation
│   │
│   └── procurement_assistant/          # Demo 2: Ship-Spares Procurement Assistant
│       ├── documents/                  # spare_parts_catalog.csv, supplier_info.pdf, procurement_guidelines.pdf
│       ├── artifacts/                  # Generated artifacts (requirements, definition, scorecards, report)
│       ├── generate_docs.py            # Synthetic document generator script
│       └── generation_prompts.txt      # Source prompts used for document generation
│
├── outputs/                            # Unseen domain factory test outputs
├── tests/                              # Automated Pytest Suite (21 tests)
├── streamlit_app.py                    # Interactive Streamlit Web Dashboard
├── run_agent.py                        # Generic CLI chat runner
├── run_factory.py                      # Factory pipeline CLI runner
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment variables template
└── README.md                           # Documentation
```

---

## 3. Tool Registry & Isolation Architecture

ForgeAI implements a strict **Tool Allowlist Guardrail**. Agents cannot access tools that are not explicitly authorized in their generated `agent_definition.json`.

| Tool Name | Capability | Authorized Domains | Security Sandbox |
|---|---|---|---|
| `csv_lookup` | Search & filter tabular catalogs by keyword or column | Procurement, Inventory | Read-only pandas filtering, max results cap |
| `calculator` | Mathematical evaluation (pricing, discounts, totals) | Procurement, Finance | Safe `eval` sandbox; regex token whitelist |
| `weather` | Real-time weather via Open-Meteo public API | Travel, Shipping | Keyless public REST API with offline fallback |
| `current_date` | Current date, time, weekday, and year | All agents | System clock with ISO-8601 formatting |

---

## 4. Installation & Setup

### Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Git
- Ollama (Optional for local inference; Mock adapter works offline out-of-the-box)

### Step 1: Clone and Set Up Virtual Environment

```bash
git clone <repo-url> ForgeAI
cd ForgeAI

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

To configure your LLM backend in `.env`:

```ini
# Option A: Local Ollama (Default)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Option B: OpenAI or Any OpenAI-Compatible API (e.g., Groq, vLLM)
# LLM_PROVIDER=openai
# OPENAI_API_BASE=https://api.openai.com/v1
# OPENAI_API_KEY=your_key_here
# OPENAI_MODEL=gpt-4o-mini

# Option C: Fully Offline / Deterministic CI Test Harness
# LLM_PROVIDER=mock
```

> **Note on Ollama Setup:**
> If using Ollama, ensure the server is running:
> ```bash
> ollama serve
> ollama pull llama3.2
> ```
> If Ollama is unreachable, ForgeAI detects the issue, explains setup steps, and gracefully falls back to deterministic execution without crashing.

---

## 5. Execution Guide

### Running Demonstration 1: HR Policy Assistant

Generate HR assistant, evaluate 21 test cases, run optimizer, and produce quality report:

```bash
python run_factory.py \
  --brief "Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents." \
  --docs demos/hr_assistant/documents \
  --output demos/hr_assistant/artifacts
```

Run the generated HR agent in the Generic Chat Runner:

```bash
# Single query mode
python run_agent.py \
  --definition demos/hr_assistant/artifacts/agent_definition.json \
  --query "How many days of annual leave are full-time employees entitled to per calendar year?"

# Interactive chat mode
python run_agent.py \
  --definition demos/hr_assistant/artifacts/agent_definition.json
```

---

### Running Demonstration 2: Ship-Spares Procurement Assistant

Generate Procurement assistant with CSV lookup and Calculator tools:

```bash
python run_factory.py \
  --brief "Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents." \
  --docs demos/procurement_assistant/documents \
  --output demos/procurement_assistant/artifacts
```

Run the generated Procurement agent:

```bash
# Query utilizing CSV Lookup and Calculator tools:
python run_agent.py \
  --definition demos/procurement_assistant/artifacts/agent_definition.json \
  --query "What is the unit price and available stock for part number NV-PUMP-001?"

# Query testing refusal of unauthorized financial execution:
python run_agent.py \
  --definition demos/procurement_assistant/artifacts/agent_definition.json \
  --query "Please initiate an automated bank wire transfer of $12,400 to supplier Nordik Marine Spares right now."
```

---

### Running on a Completely Unseen Domain

To verify zero-code-change generic operation:

```bash
python run_factory.py \
  --brief "Build a CyberSecurity Compliance Assistant that answers employee questions on device encryption, incident reporting SLAs, USB drive restrictions, and VPN requirements based on security policies." \
  --docs outputs/unseen_test/documents \
  --output outputs/unseen_test/artifacts
```

---

### Interactive Web Dashboard (Streamlit)

Launch the full graphical interface:

```bash
streamlit run streamlit_app.py
```

The UI provides:
1. **Agent Factory:** Brief input, document folder selection, and live pipeline progress.
2. **Evaluation & Scorecards:** Metric progression tables, failure mode breakdown, and full markdown report.
3. **Live Agent Chat:** Real-time conversational interface with visible source citations and tool call badges.
4. **System Status:** LLM connectivity health check and registered tool directory.

---

### FastAPI REST Backend

Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation is accessible at `http://localhost:8000/docs`.

---

## 6. Automated Testing Suite

Execute the complete test suite:

```bash
pytest -v
```

### Test Coverage Summary:
- `tests/test_retrieval.py`: Document ingestion (PDF, TXT, CSV), sentence chunking, metadata preservation, and FAISS indexing/reloading.
- `tests/test_tools.py`: Tool discovery, calculator math evaluation, CSV searching, current date, and tool allowlist security enforcement.
- `tests/test_schemas.py`: Pydantic validation for Requirements, GroundabilityReport, AgentDefinition, EvalSet, and Scorecards.
- `tests/test_factory_modules.py`: IntakeInterviewer, GroundabilityGuard, AgentGenerator, EvalGenerator (>=20 cases), and CriticOptimizer.
- `tests/test_runtime.py`: GenericChatRunner answering, citation formatting, tool execution, and refusal policy enforcement for both domains.
- `tests/test_pipeline_integration.py`: End-to-end factory pipeline execution on an unseen domain without source code modification.

**Result: 21 Passed, 0 Failed (100% Pass Rate).**

---

## 7. Generated Artifacts Reference

Each factory run produces the following artifacts in the designated output directory:

| Artifact | Format | Description |
|---|---|---|
| `requirements.json` | JSON | Scope, audience, tone, topics, tool requirements, document inventory, assumptions |
| `groundability_report.json` | JSON | Evidence mapping, supported/unsupported topic classification, refusal guidance |
| `agent_definition.json` | JSON | Declarative agent specification executable by `GenericChatRunner` |
| `eval_set.json` | JSON | At least 20 evaluation test cases (Answerable, Out-of-Scope, Edge Cases) |
| `eval_generation_prompt.txt` | Text | Exact prompt used to synthesize the evaluation dataset |
| `scorecards.json` | JSON | Iteration scorecards, pass rates, metric breakdown, and individual test results |
| `iteration_logs.json` | JSON | Critic diagnostics, root cause classifications, and targeted modifications |
| `final_report.md` | Markdown | Comprehensive honest quality report documenting metrics, iterations, and limitations |

---

## 8. Honest Performance & Limitations Assessment

ForgeAI adheres to strict honest reporting principles:

1. **Evidence-Based Evaluation:** Evaluation cases must be verifiable against uploaded document text. The system never invents or inflates evaluation metrics.
2. **Deterministic-First Refusal:** When an inquiry requests confidential data (e.g., salaries) or unsupported actions (e.g., bank transfers), the agent firmly refuses and cites policy limitations.
3. **Targeted Optimization:** The critic-optimizer identifies specific failure categories (e.g., retrieval miss vs citation defect) and applies localized hyper-parameter or prompt updates rather than blind regeneration.
4. **Document Boundary Limitations:** The agent cannot answer questions regarding topics absent from the corpus (e.g., health insurance in HR demo, crew payroll in procurement demo), and explicitly documents these limitations in `final_report.md`.

---

*Authored for the OceanAI Jr. GenAI Engineer Campus Recruitment Assignment.*
