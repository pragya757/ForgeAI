# ForgeAI — Universal Document Ingestion Architecture

**Document Version:** 1.0  
**Date:** November 27, 2026  
**Auditor / Architect:** Senior GenAI Systems & Quality Engineer  
**Status:** ✅ Fully Implemented, Verified & Integrated

---

## 1. Overview & Objectives

ForgeAI is designed as an autonomous, declarative **Agent Factory** that transforms natural language briefs and domain documents into enterprise-grade AI agents.

Previously, demonstration presets relied on predefined directories (e.g., `demos/hr_assistant/documents/`). To guarantee that ForgeAI is **genuinely universal** and completely independent of predefined folders, the document ingestion pipeline has been refactored into a session-isolated, multi-format ingestion architecture.

### Core Guarantees:
1. **Zero Domain-Specific Ingestion Code:** No separate parsers, directories, or conditions for HR, maritime, academic, medical, or other domains.
2. **Arbitrary File Formats Supported:** Full parsing support for **PDF**, **TXT**, **CSV**, and **Markdown (`.md`)**.
3. **Session-Isolated Run Directories:** Every agent creation session is given an independent, collision-proof session directory (`outputs/sessions/{session_id}/`).
4. **Data Integrity & Provenance:** Every ingested file is validated, checked for empty content, and assigned a SHA-256 cryptographic checksum stored in `corpus_manifest.json`.
5. **Brief Decoupling:** Uploading custom documents in the dashboard automatically decouples the prompt brief from demo presets, preventing domain contamination.
6. **Agent Corpus Binding:** Generated `agent_definition.json` files persist explicit `corpus_directory` and `indexed_documents` metadata, eliminating directory-guessing heuristics at runtime.
7. **Multi-Interface Access:** Works identically via Streamlit Dashboard, Python CLI (`run_factory.py`), and FastAPI multipart REST API (`POST /api/factory/upload-and-build`).

---

## 2. Directory Structure & Session Isolation

```
outputs/sessions/
└── session_20261127_134500_a1b2c3d4/
    ├── documents/                         <-- Isolated Document Corpus
    │   ├── corpus_manifest.json           <-- Provenance & SHA-256 Manifest
    │   ├── operations_guide.pdf
    │   ├── equipment_specs.csv
    │   └── emergency_procedures.md
    └── artifacts/                         <-- Generated Agent Artifacts
        ├── requirements.json
        ├── groundability_report.json
        ├── agent_definition.json          <-- Persists corpus_directory path
        ├── eval_set.json
        ├── scorecards.json
        ├── iteration_logs.json
        ├── final_report.md
        └── quality_report.json
```

### Manifest Schema (`corpus_manifest.json`)
```json
{
  "session_id": "session_20261127_134500_a1b2c3d4",
  "created_at": "2026-11-27 13:45:00",
  "total_documents": 3,
  "total_bytes": 184520,
  "document_directory": "/abs/path/outputs/sessions/.../documents",
  "artifacts_directory": "/abs/path/outputs/sessions/.../artifacts",
  "documents": [
    {
      "filename": "operations_guide.pdf",
      "format": "PDF",
      "size_bytes": 124800,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "file_path": "/abs/path/.../operations_guide.pdf",
      "created_at": "2026-11-27 13:45:00"
    }
  ]
}
```

---

## 3. Ingestion Manager (`app/retrieval/ingestion.py`)

The reusable `IngestionManager` class manages document ingestion across both the Streamlit UI and the FastAPI backend:

- **`sanitize_filename(filename: str) -> str`**: Prevents path traversal vulnerabilities (`../`, `..\\`) and normalizes filenames.
- **`validate_file(filename: str, content: bytes) -> str`**: Enforces allowed extensions (`.pdf`, `.txt`, `.csv`, `.md`) and rejects 0-byte empty files with descriptive errors.
- **`create_session(session_id, base_dir) -> Tuple[str, str, str]`**: Mints collision-proof session IDs (`session_<timestamp>_<uuid8>`) and prepares directories.
- **`ingest_files(files, session_id, base_dir) -> IngestionResult`**: Processes tuples of `(name, bytes)`, file-like objects, Streamlit `UploadedFile`, or FastAPI `UploadFile`. Computes SHA-256 hashes and generates `corpus_manifest.json`.
- **`load_manifest(doc_dir) -> Optional[Dict]`**: Reads manifest from disk for verification.

---

## 4. UI Custom Upload Workflow (`streamlit_app.py`)

1. **Step 1: Ingestion Zone**
   - The user drags and drops or browses arbitrary `.pdf`, `.txt`, `.csv`, `.md` files.
   - The file fingerprint triggers `IngestionManager.ingest_files()`.
   - A new unique session directory is minted immediately.
   - The UI automatically switches to **Custom Upload Ingestion Mode**.
   - The user brief is reset to a neutral domain prompt, clearing any HR/procurement text.
   - An interactive table displays uploaded filenames, formats, sizes, and truncated SHA-256 checksums.

2. **Step 2: Autonomous Generation**
   - The user clicks **🚀 Run Autonomous Agent Factory Pipeline**.
   - The pipeline executes against the isolated uploaded corpus directory.
   - The agent definition, evaluation cases, and scorecards are saved into the session's isolated `artifacts/` folder.

3. **Step 3: Interactive Playground**
   - The playground loads the generated `agent_definition.json` directly.
   - The runtime automatically loads the isolated session corpus from `agent_def.corpus_directory`.

---

## 5. FastAPI Multipart Upload Endpoint

### Endpoint: `POST /api/factory/upload-and-build`
Enables programmatic, remote client agent creation via `multipart/form-data`:

```bash
curl -X POST "http://localhost:8000/api/factory/upload-and-build" \
  -F "brief=Create a harbor logistics assistant that answers questions about dock specifications and container dwell times." \
  -F "iterations=2" \
  -F "files=@dock_policy.pdf" \
  -F "files=@crane_schedule.csv"
```

### JSON Response:
```json
{
  "status": "success",
  "session_id": "session_20261127_134500_a1b2c3d4",
  "agent_name": "Harbor Logistics Operations Assistant",
  "domain": "Maritime Logistics & Port Operations",
  "pass_rate": 1.0,
  "passed_tests": 20,
  "total_tests": 20,
  "status_verdict": "PRODUCTION_READY",
  "documents_ingested": ["dock_policy.pdf", "crane_schedule.csv"],
  "document_directory": "/abs/path/outputs/sessions/.../documents",
  "artifacts_directory": "/abs/path/outputs/sessions/.../artifacts",
  "agent_definition_path": "/abs/path/outputs/sessions/.../artifacts/agent_definition.json",
  "manifest_path": "/abs/path/outputs/sessions/.../documents/corpus_manifest.json"
}
```

---

## 6. End-to-End Test Procedure on a New Unseen Domain

Follow this verification procedure to validate that ForgeAI builds a complete agent for an unseen domain:

### Domain: Commercial Drone Flight Operations

#### 1. Prepare Document Corpus (`/tmp/drone_corpus/`):
- `flight_limits.txt`:
  ```text
  COMMERCIAL DRONE FLIGHT OPERATING PROCEDURES
  Maximum operating altitude is strictly 400 feet Above Ground Level (AGL).
  Pre-flight visual inspection of rotors, battery locking pins, and GPS lock is mandatory.
  No operations permitted within 5 miles of an active airport without automated LAANC authorization.
  ```
- `battery_specs.csv`:
  ```csv
  battery_model,capacity_mah,max_flight_mins,min_voltage_cutoff
  TB55,7660,38,21.6
  TB60,5935,45,20.8
  ```
- `emergency_checklist.md`:
  ```markdown
  # Drone Emergency Procedures
  ## Section 1: Signal Loss (Failsafe RTH)
  In the event of total remote control link loss exceeding 3 seconds, the aircraft initiates Return-to-Home (RTH) at a minimum climb altitude of 150 feet.
  ```

#### 2. Run Autonomous Pipeline via CLI:
```bash
python run_factory.py \
  --brief "Create a commercial drone flight assistant that answers pilot questions regarding altitude ceilings, battery specs, and emergency return-to-home procedures using flight manuals." \
  --docs /tmp/drone_corpus \
  --output outputs/drone_agent_artifacts \
  --iterations 2
```

#### 3. Test Agent Interaction via Runtime CLI:
```bash
python run_agent.py \
  --definition outputs/drone_agent_artifacts/agent_definition.json \
  --query "What is the maximum allowed flight altitude and what happens during signal loss?"
```

#### 4. Expected Output:
- **Agent Name:** `Commercial Drone Flight Operations Assistant`
- **Answer:** Answers 400 feet AGL and explains 3-second RTH failsafe at 150 feet.
- **Citations:** `[Source: flight_limits.txt, Page: 1]`, `[Source: emergency_checklist.md, Page: 1]`.

---

## 7. Verification Test Suite Results

The comprehensive test suite in `tests/test_dynamic_ingestion.py` was executed alongside the full regression test suite:

```bash
.venv/bin/pytest tests/
======================= 118 passed, 5 warnings in 5.40s =======================
```

All 118 tests passed with 0 failures:
- Ingestion of PDF, TXT, CSV, MD formats.
- Handling and rejection of empty (0-byte) and unsupported (.exe, .zip) files.
- Strict session isolation across consecutive builds in the same process.
- Embedding of `corpus_directory` and `indexed_documents` in `AgentDefinition`.
- Dynamic corpus loading by `GenericChatRunner`.
- FastAPI multipart `/api/factory/upload-and-build` execution and error handling.
- Zero regressions across existing demonstration test suites.
