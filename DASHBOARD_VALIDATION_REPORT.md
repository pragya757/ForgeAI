# ForgeAI: Dashboard Validation and End-to-End Consistency Audit Report

**Audit Date:** November 26, 2026  
**Auditor:** ForgeAI Quality Engineering & GenAI Architecture Team  
**Scope:** Streamlit Application Runtime (`streamlit_app.py`), Mock LLM Client (`app/llm/mock_client.py`), Intake Interviewer (`app/factory/interviewer.py`), and Pipeline Isolation (`app/factory/pipeline.py`).  
**Status:** **ALL ISSUES RESOLVED — 112/112 TESTS PASSING (100%)**

---

## Executive Summary

During live dashboard testing of ForgeAI, two major runtime and behavioral inconsistencies were reported:
1. **Streamlit Runtime Crash:** `AttributeError: ... object has no attribute 'item'` (and `'get'`) in `streamlit_app.py` around line 680 during optimization log rendering.
2. **Corpus Contamination:** Selecting the HR Policy Assistant preset while uploading an unrelated custom document (e.g., `IT - Interns JD.pdf`) resulted in requirements analysis, groundability checks, agent definitions, and evaluation test cases referencing canned HR documents (`leave_policy.pdf`, `attendance_policy.pdf`) rather than the active uploaded file.
3. **Spurious Clarification Questions:** The intake interviewer flagged standard instruction words (`create`, `about`, `assistant`, `company`, `answers`) as missing knowledge and fell back to 5 generic boilerplate questions even for crystal-clear, fully-grounded briefs.

This audit report documents the forensic root-cause analysis, exact technical fixes applied across the codebase, and formal regression verification proving complete data isolation and runtime stability.

---

## 1. Forensic Root-Cause Analysis & Fixes

### 1.1 Issue 1: Optimization Log Pydantic Model vs. Dictionary Crash

#### Symptom:
When rendering the Critic-Optimizer progression in Step 6 (Tab 6), Streamlit threw an unhandled runtime error:
```
AttributeError: 'IterationLog' object has no attribute 'get'
```
or an error attempting to call `.item()` / `.items()` on non-dict objects.

#### Root Cause:
1. `app.factory.pipeline.ForgeAIFactory.build_agent()` returns `iteration_logs` as a list of typed Pydantic `IterationLog` model instances (`from app.schemas.scorecard import IterationLog`).
2. When loading pre-built demos from JSON, `iteration_logs` was loaded as raw Python `dict` objects.
3. In `streamlit_app.py`, the rendering loop assumed dictionary objects and called `log.get("iteration")`, `log.get("score_before")`, `log.get("score_after")`, `log.get("root_cause_diagnosis")`.
4. Crucially, the Pydantic schema `IterationLog` defines fields as:
   - `iteration_number: int` (NOT `iteration`)
   - `previous_score: float` (NOT `score_before`)
   - `new_score: float` (NOT `score_after`)
   - `identified_root_causes: str` (NOT `root_cause_diagnosis`)
   - `failure_categories: List[str]` (NOT `failure_category`)
5. Calling `.get()` on the Pydantic model caused `AttributeError`, while accessing non-existent legacy keys returned `None` or zeroes.

#### Technical Resolution:
- Implemented recursive `safe_to_dict(obj)` and `safe_to_dict_list(items)` helpers in `streamlit_app.py` that handle Pydantic models (via `.model_dump()` / `.dict()`) and dictionaries transparently.
- Implemented robust dual-name field extraction supporting both schema field names and legacy dictionary keys:
  ```python
  iter_num = log.get("iteration_number") or log.get("iteration", 1)
  diagnosis = log.get("identified_root_causes") or log.get("root_cause_diagnosis") or "Targeted optimization refinement"
  score_before = log.get("previous_score", log.get("score_before", 0.0))
  score_after = log.get("new_score", log.get("score_after", 0.0))
  ```
- Verified that missing or optional fields default gracefully without broad exception suppression.

---

### 1.2 Issue 2: Document & Demo Data Contamination

#### Symptom:
When a user selected the "HR Policy Assistant" preset but uploaded a custom document (`IT - Interns JD.pdf`), the dashboard continued to display `leave_policy.pdf`, `attendance_policy.pdf`, and `employee_handbook.pdf` across requirements, groundability, agent definitions, and evaluation test cases.

#### Root Cause:
1. **Mock LLM Keyword Match on Brief Text:** In `app/llm/mock_client.py`, the interviewer, groundability guard, agent generator, eval generator, and runner checked domain matching using brief keywords:
   ```python
   is_hr = bool(re.search(r"\b(hr|leave|attendance|handbook|holiday)\b", text.lower()))
   ```
   Because the user selected the HR preset, the brief contained words like "leave" and "attendance". Even though an unrelated file (`IT - Interns JD.pdf`) was uploaded, `is_hr` evaluated to `True`, triggering the hardcoded HR demo outputs.
2. **Shared Upload Destination:** Uploaded files were written to a static folder `outputs/custom_agent/documents`, while `output_dir_input` remained pointed at `demos/hr_assistant/artifacts`.
3. **Stale Session State:** `st.session_state["loaded_demo"]` remained active if pre-built artifacts had been previously loaded, overriding the newly generated run.

#### Technical Resolution:
1. **Strict Active Document Verification:** Updated `_mock_interviewer`, `_mock_groundability`, `_mock_agent_generator`, `_mock_eval_generator`, and `_mock_runner_response` in `app/llm/mock_client.py` to verify that HR or procurement demo files are *actually present* in the active document text:
   ```python
   has_hr_docs = any(d in text.lower() for d in ["leave_policy", "attendance_policy", "employee_handbook"])
   has_procurement_docs = any(d in text.lower() for d in ["spare_parts_catalog", "supplier_information", "procurement_guidelines"])
   
   is_hr = has_hr_docs and bool(re.search(r"\b(hr|leave|attendance|handbook|holiday)\b", text.lower()))
   is_procurement = has_procurement_docs and bool(re.search(r"\b(procurement|spares?|supplier|catalog|vessel|marine)\b", text.lower()))
   ```
   If custom documents (e.g. `IT_Interns_JD.txt`) are provided without the specific demo files, the mock routes cleanly to the dynamic generic extraction logic, grounding strictly on the uploaded corpus.
2. **Isolated Session Directories:** In `streamlit_app.py`, custom uploads are saved to isolated, timestamped directories:
   - `outputs/runs/<session_id>/documents`
   - `outputs/runs/<session_id>/artifacts`
3. **Explicit State Invalidation:**
   - When custom files are uploaded, `st.session_state["loaded_demo"] = None`.
   - When pre-built artifacts are loaded, `st.session_state["last_run"] = None`.
4. **Visual Corpus Indicator:** Added a clear dashboard banner indicating the exact active corpus (`Custom Upload (N files: ...)` vs `Preset (...)`).
5. **Playground Dynamic Path Binding:** Tab 8 now dynamically defaults to the active run's artifacts directory rather than a hardcoded preset path.

---

### 1.3 Issue 3: Spurious Clarification Questions

#### Symptom:
When requesting clarification questions on a clear brief, the system returned 5 generic questions (`Who is the primary target audience?`, `Are there specific topics the assistant must refuse?`, etc.) or flagged instruction words as missing knowledge.

#### Root Cause:
1. `detect_information_gaps` only excluded 14 basic stopwords. Words like `create`, `assistant`, `company`, `answers`, `using`, `guidelines`, `procedures`, `rotations` were compared against raw text.
2. In `generate_clarifying_questions`, if the LLM returned an empty or unparseable response, the code had a fallback:
   ```python
   if not deterministic_qs:
       deterministic_qs = [ ... 5 generic questions ... ]
   ```
   This forced 5 generic questions to be returned even when the brief was 100% complete and unambiguous.

#### Technical Resolution:
1. **Comprehensive `GENERIC_STOPWORDS`:** Created an extensive set of meta-instruction words (`create`, `make`, `assistant`, `answers`, `company`, `enterprise`, `using`, `guideline`, `policy`, `manual`, `developer`, `operator`, `engineer`, `audience`, etc.).
2. **Morphological Variant Checking:** Enhanced gap detection to check singular, plural, past-tense, and participle stems (`procedures` $\rightarrow$ `procedure`, `rotations` $\rightarrow$ `rotation`), eliminating false gap flags.
3. **Zero Questions on Clear Briefs:** If `gaps` contains no contradictions, incomplete markers, or out-of-scope gaps, `generate_clarifying_questions` immediately returns `[]` (0 questions).
4. **Strict Cap:** Questions are strictly formulated from actual detected gaps and capped at $\le 5$.

---

## 2. Regression Test Suite (`tests/test_dashboard_consistency.py`)

A dedicated regression test suite was authored and verified under pytest:

| Test Name | Test Objective | Result |
|---|---|---|
| `test_iteration_log_pydantic_and_dict_compatibility` | Validates `safe_to_dict` parses both Pydantic models and legacy dicts with 0 errors. | **PASSED** |
| `test_clarifying_questions_generic_stopwords_filtered` | Verifies meta-instruction words are included in `GENERIC_STOPWORDS`. | **PASSED** |
| `test_clarifying_questions_clear_brief_returns_empty` | Verifies a clear brief with grounded corpus returns exactly 0 questions. | **PASSED** |
| `test_clarifying_questions_ambiguous_brief_capped_at_five` | Verifies contradictory or out-of-scope briefs formulate $\le 5$ targeted questions. | **PASSED** |
| `test_hr_brief_with_unrelated_uploaded_doc_prevents_contamination` | Submits an HR brief with `IT_Interns_JD.txt`; verifies 0 HR demo files contaminate requirements, groundability, agent defs, or eval sets. | **PASSED** |
| `test_consecutive_runs_corpus_isolation` | Runs two distinct domains sequentially; verifies artifacts trees are completely isolated with zero leakage. | **PASSED** |

---

## 3. Full Test Suite Execution Results

Executed across the entire project repository:
```bash
.venv/bin/pytest tests/
```

**Output:**
```
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/pragya/Downloads/OceanAI
configfile: pytest.ini
plugins: anyio-4.16.0
collected 112 items

tests/test_agent_generator_advanced.py ..........                        [  8%]
tests/test_critic_optimizer_advanced.py ..........                       [ 17%]
tests/test_dashboard_consistency.py ......                               [ 23%]
tests/test_demo_audit_advanced.py ...                                    [ 25%]
tests/test_eval_generator_advanced.py .......                            [ 32%]
tests/test_factory_modules.py .....                                      [ 36%]
tests/test_failure_classification.py ...                                 [ 39%]
tests/test_interviewer_groundability_advanced.py .......                 [ 45%]
tests/test_judge_advanced.py .........                                   [ 53%]
tests/test_judge_reliability_matrix.py .........                         [ 61%]
tests/test_pipeline_integration.py .                                     [ 62%]
tests/test_real_llm_providers.py ........                                [ 69%]
tests/test_reporting_observability_advanced.py ......                    [ 75%]
tests/test_retrieval.py ....                                             [ 78%]
tests/test_runtime.py ..                                                 [ 80%]
tests/test_runtime_security_advanced.py ..........                       [ 89%]
tests/test_schemas.py ....                                               [ 92%]
tests/test_tools.py .....                                                [ 97%]
tests/test_unseen_generalization.py ...                                  [100%]

======================= 112 passed, 5 warnings in 5.13s ========================
```

---

## 4. Modern Streamlit Best Practices Conformance

In alignment with the Streamlit development guidelines:
- Removed all deprecated `use_container_width=True` calls on buttons, forms, and dataframes; replaced with native defaults and `width="stretch"`.
- Maintained responsive container layouts and clean dark SaaS theme (`#050505` background, `#00D9F5` electric cyan accent).
- Ensured session state initialization is clean, robust, and free of persistent cross-run mutations.
