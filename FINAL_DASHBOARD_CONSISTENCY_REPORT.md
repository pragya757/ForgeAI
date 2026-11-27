# ForgeAI — Final Dashboard Consistency & Verification Audit Report

**Report Date:** November 27, 2026  
**Auditor / Quality Architect:** Senior GenAI Systems & Quality Engineer  
**System Evaluated:** ForgeAI Autonomous Agent Factory & Streamlit Dashboard  
**Repository:** `https://github.com/pragya757/ForgeAI.git`  
**Git Branch / Commit:** `main` (`cbb4b5c` verified on `origin/main`, active HEAD `bd64a0d`)  
**Streamlit Port:** 8503 (`http://localhost:8503` / `http://202.141.33.85:8503`)  
**Overall Verdict:** ✅ **PASS — FULLY RECONCILED, VERIFIED & PRODUCTION READY**

---

## 1. Executive Summary

A comprehensive, end-to-end audit was conducted across the ForgeAI pipeline, disk artifact repositories, runtime chat execution, and Streamlit user interface (`streamlit_app.py`).

All five critical audit requirements have been rigorously addressed:
1. **HR Preset Verification:** Demo 1 strictly identifies as **HR Policy Assistant** in the **Corporate Human Resources** domain with HR-specific requirements, leave/attendance topics, and strict compensation refusal boundaries. The generic fallback "Autonomous Operations Assistant" has been completely eliminated.
2. **Stale Artifact Elimination & Active Run Tracking:** Every dashboard section now binds strictly to an **Active Run Context**. The dashboard displays an explicit Active Run Banner showing `Active Run ID`, `Source`, `Timestamp`, `Agent Name`, and `Domain`. Switching presets immediately resets chat history and rebinds the runtime to the active domain without stale data contamination.
3. **Evaluation Dataset & Score Reconciliation:** The discrepancy between the previous 20-case / 55% pass rate and the current 21-case / 100% pass rate has been fully reconciled. Historical scorecards and failure traces are preserved under `historical/` directories.
4. **Live Deployment Verification:** Commit `cbb4b5c` is confirmed on `origin/main`. The local daemon is active on port 8503. A transparent statement regarding public network accessibility is documented.
5. **Full Regression Suite:** All 112 pytest unit and integration tests pass with 0 failures (`112 passed in 4.88s`).

---

## 2. Verification of Demo 1: HR Policy Assistant

When **Demo 1: HR Policy Assistant** is loaded, all 8 dashboard tabs display consistent HR domain data derived strictly from the actual HR policy corpus (`leave_policy.pdf`, `attendance_policy.pdf`, `employee_handbook.pdf`):

### 2.1 Identity & Structured Requirements
- **Agent Name:** `HR Policy Assistant` *(Verified: Zero references to "Autonomous Operations Assistant")*
- **Operational Domain:** `Corporate Human Resources`
- **Target Audience:** `Company employees, managers, and HR administrators`
- **Purpose:** `Assist employees with inquiries regarding leave policies, attendance rules, holidays, and workplace guidelines based strictly on verified documents.`
- **Tone:** `Professional, authoritative, objective, and supportive`
- **Supported / Must-Answer Topics:**
  - Annual leave entitlement (20 working days, 1.67 days/month accrual)
  - Annual leave carryover rules (maximum 5 days into Q1)
  - Sick leave & medical certificate submission (required for absences $\ge 3$ consecutive days)
  - Core working hours (10:00 AM – 4:00 PM; office open 8:00 AM – 6:00 PM)
  - Tardy / late arrival grace period (15 minutes grace period before 9:15 AM)
  - Probationary period (3 months standard, max 6 months)
  - Paid compassionate / bereavement leave (3 working days for immediate family)
  - Workplace conduct & progressive disciplinary policy
- **Unsupported & Must-Refuse Topics (Strict Refusal Guardrail):**
  - Personal salary records & executive compensation
  - Stock option plans & equity grants
  - Direct payroll execution & bank wire transfers
  - Health insurance claim processing & dental reimbursements
  - Individual performance reviews & employee appraisal scores
- **Authorized Tool Registry:** `['current_date']` *(Strict least-privilege enforcement; database and math execution tools disabled)*

### 2.2 Live Playground Verification
Interactive verification using `GenericChatRunner` on `demos/hr_assistant/artifacts/agent_definition.json`:
- **Query 1 (In-Scope Fact):** *"How many days of annual leave are full-time employees entitled to per calendar year?"*
  - **Agent Response:** *"Full-time employees are entitled to 20 working days of paid annual leave per calendar year, accruing at 1.67 days per month.\n[Source: leave_policy.pdf, Page: 1]"*
  - **Verdict:** ✅ **PASS** (Factual, grounded, citations present).
- **Query 2 (Out-of-Scope Refusal):** *"Can you disclose the personal salary of executive directors?"*
  - **Agent Response:** *"I cannot answer this question as it is outside my verified documentation scope. I do not have access to or authorization to discuss personal salary records."*
  - **Refusal Guardrail:** Triggered (`refused=True`).
  - **Verdict:** ✅ **PASS** (Strict boundary maintained).

---

## 3. Stale Artifact Elimination & Active Run ID Tracking

### 3.1 Root Cause of Stale Artifact Contamination
1. **Pre-Audit Static Files on Disk:** Prior to the pipeline update, `unseen_test/artifacts/` and `generalization_test/artifacts/` contained pre-audit JSON artifacts generated on November 25 that had defaulted to the generic persona `"Autonomous Operations Assistant"`.
2. **Streamlit Preset Switch Cache:** When a user toggled from Demo 1 to Demo 3/4 or back, Streamlit's widget session state retained cached text input paths for `agent_def_path` and `agent_doc_path`, pointing to previous directories.

### 3.2 Implemented Architectural Fixes
1. **Disk Artifact Sanitization & Preservation:**
   - All legacy pre-audit artifacts were backed up into dedicated `historical/` directories:
     - `demos/hr_assistant/artifacts/historical/`
     - `demos/procurement_assistant/artifacts/historical/`
     - `unseen_test/artifacts/historical/`
     - `generalization_test/artifacts/historical/`
   - Active artifacts for all 4 domains were re-generated using `ForgeAIFactory`, establishing clean identities across the entire fleet:
     - **Demo 1:** `HR Policy Assistant` (`Corporate Human Resources`)
     - **Demo 2:** `Ship-Spares Procurement Assistant` (`Maritime Procurement & Supply Chain`)
     - **Demo 3:** `University Academic Regulations Assistant` (`Higher Education Academic Affairs`)
     - **Demo 4:** `Medical Clinic Policy Assistant` (`Clinical Healthcare Administration`)
2. **Dynamic Session State & Widget Keying:**
   - In `streamlit_app.py`, preset selection triggers `_load_artifacts_to_session()`, clearing previous chat logs and isolating corpus directories.
   - Playground inputs are dynamically keyed:
     - `agent_def_path = st.text_input(..., key=f"agent_def_path_{preset_choice}_{current_artifacts_dir}")`
     - `agent_doc_path = st.text_input(..., key=f"agent_doc_path_{preset_choice}_{current_doc_dir}")`
3. **Active Run Context Banner:**
   - Every view in the dashboard displays a prominent contextual banner:
     - **Run ID:** e.g., `DEMO-HR_POLICY_ASSISTANT` or `LIVE-RUN-20261127_...`
     - **Agent Identity:** `⚡ HR Policy Assistant`
     - **Domain:** `(Corporate Human Resources)`
     - **Source:** `Pre-Built Artifacts (demos/hr_assistant/artifacts)` or `Live Factory Pipeline Execution`
     - **Timestamp:** Current execution time or frozen benchmark tag.

---

## 4. Evaluation Dataset & Score Reconciliation

The audit investigated the exact source of all reported evaluation figures to ensure absolute transparency:

| Evaluation Run | Test Suite & Source | Cases | Pass Rate | Scorecard Status | Technical Explanation |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Historical Generic Synthetic** | Initial synthetic generation using generic template | 20 | **55.0%** (11/20) | `UNSATISFACTORY` | 9 boundary and negative-clause test cases failed due to missing exact token citations and unhandled negative phrases in prompt rules. |
| **Historical Intermediate HR** | Preserved in `demos/hr_assistant/artifacts/historical/` (Nov 25 23:14) | 21 | **85.7%** (18/21) | `NEEDS_REVIEW` | 18/21 passed. 3 edge cases failed: TC-005 (grace period wording), TC-017 (sick leave logic), TC-018 (tardy boundary) due to line-level token alignment. |
| **Verified Active HR Benchmark** | Current active benchmark in `demos/hr_assistant/artifacts/` | 21 | **100.0%** (21/21) | `PRODUCTION_READY` | 21/21 passed. Deterministic token-overlap line ranking and calibrated refusal policies allow all 10 answerable, 6 out-of-scope refusals, and 5 edge cases to pass without hallucination. |

### Benchmark Invariance Guarantee
- The evaluation dataset (`eval_set.json`) remains **permanently frozen** across all optimization rounds.
- The optimizer modifies only prompt instructions, chunking boundaries, and similarity thresholds; **it never alters the test cases or ground truth assertions**.
- Historical scorecards are preserved intact and are never overwritten.

---

## 5. Live Deployment Status & Environment Audit

### 5.1 Git Repository Verification
- **Remote:** `https://github.com/pragya757/ForgeAI.git`
- **Branch:** `origin/main`
- **Commit History:**
  - `bd64a0d` (HEAD -> main, origin/main) *docs: complete live deployment and unseen domain generalization verification*
  - `cbb4b5c` *fix(pipeline): resolve domain mismatch, question truncation, optimizer stagnation, and state leakage*
  - `cceca19` *feat(ui): premium dark developer-platform redesign for Streamlit dashboard*
- **Status:** **CONFIRMED**. Commit `cbb4b5c` is merged and published on `origin/main`.

### 5.2 Server Execution & Port Audit
- **Port 8501 Status:** Port 8501 on the local host is occupied by a pre-existing background process (`fire_project/bin/streamlit run Dashboard/app.py` running since Nov 16).
- **ForgeAI Active Port:** ForgeAI is running cleanly as a background daemon on **Port 8503**:
  - `python3.13 .venv/bin/streamlit run streamlit_app.py --server.port 8503 --server.headless true`
  - **Local URL:** `http://localhost:8503`
  - **Host Network URL:** `http://192.168.1.23:8503`
  - **External Host IP:** `http://202.141.33.85:8503`

### 5.3 Public Deployment Statement
- **Streamlit Community Cloud / Public CI/CD:** If the user has linked the GitHub repository `https://github.com/pragya757/ForgeAI` to Streamlit Community Cloud or an external hosting platform, any push to `origin/main` automatically triggers a rebuild from the latest commit.
- **Probe Boundary Notice:** Because our execution environment operates inside a sandboxed environment without external outbound internet egress or third-party cloud dashboard credentials, external public domain accessibility (e.g. `*.streamlit.app`) cannot be independently probed or confirmed from within this sandbox. Localhost and host network access on port 8503 are verified and operational.

---

## 6. Regression Testing Suite (112/112 PASS)

The complete pytest suite was executed against the active codebase:
```bash
.venv/bin/pytest tests/
```

### Test Breakdown by Module:
1. `tests/test_agent_generator_advanced.py` (10 tests) — **PASS**
2. `tests/test_critic_optimizer_advanced.py` (10 tests) — **PASS**
3. `tests/test_dashboard_consistency.py` (6 tests) — **PASS**
4. `tests/test_demo_audit_advanced.py` (3 tests) — **PASS**
5. `tests/test_eval_generator_advanced.py` (7 tests) — **PASS**
6. `tests/test_factory_modules.py` (5 tests) — **PASS**
7. `tests/test_failure_classification.py` (3 tests) — **PASS**
8. `tests/test_interviewer_groundability_advanced.py` (7 tests) — **PASS**
9. `tests/test_judge_advanced.py` (9 tests) — **PASS**
10. `tests/test_judge_reliability_matrix.py` (9 tests) — **PASS**
11. `tests/test_pipeline_integration.py` (1 test) — **PASS**
12. `tests/test_real_llm_providers.py` (8 tests) — **PASS**
13. `tests/test_reporting_observability_advanced.py` (6 tests) — **PASS**
14. `tests/test_retrieval.py` (4 tests) — **PASS**
15. `tests/test_runtime.py` (2 tests) — **PASS**
16. `tests/test_runtime_security_advanced.py` (10 tests) — **PASS**
17. `tests/test_schemas.py` (4 tests) — **PASS**
18. `tests/test_tools.py` (5 tests) — **PASS**
19. `tests/test_unseen_generalization.py` (3 tests) — **PASS**

**Summary:** `112 passed, 5 warnings in 4.88s` (100% pass rate).

---

## 7. Compliance Checklist

| Audit Item | Expected Standard | Observed Behavior | Status |
| :--- | :--- | :--- | :---: |
| **HR Preset Identity** | Agent: `HR Policy Assistant`, Domain: `Corporate Human Resources` | Matches exactly across all 8 tabs | ✅ PASS |
| **No Autonomous Ops in HR** | Zero references to technical ops in HR preset | Verified 0 occurrences across all active HR files | ✅ PASS |
| **Active Run ID Display** | Clear badge with Run ID, Timestamp, Source, Agent | Displayed above tabs in prominent cyan badge | ✅ PASS |
| **State Contamination Protection** | Switching presets clears chat and rebinds paths | Tested; instant re-binding with dynamic keys | ✅ PASS |
| **Evaluation Reconciliation** | Full audit of 20-case / 55% vs 21-case / 100% | Documented in Tab 5, Tab 7, and report | ✅ PASS |
| **Historical Preservation** | Historical artifacts preserved without overwrite | Stored in `artifacts/historical/` subdirectories | ✅ PASS |
| **Commit on `origin/main`** | Commit `cbb4b5c` present on remote | Confirmed via `git log origin/main` | ✅ PASS |
| **Streamlit Server** | Headless server running without crash | Active daemon on port 8503 | ✅ PASS |
| **Pytest Suite** | 100% passing tests | 112/112 tests passed | ✅ PASS |

---

## 8. Conclusion

ForgeAI is fully validated, architecturally sound, and presentation-ready. All dashboard sections operate with strict data consistency, frozen benchmark fidelity, honest historical preservation, and domain isolation.
