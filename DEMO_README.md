# ForgeAI Demonstration Audit & Verification Guide

This document presents the execution audit, architecture validation, tool security analysis, and evaluation scorecards for the two mandatory production demonstrations built autonomously by **ForgeAI**:

1. **DEMO 1: HR Policy Assistant** (`demos/hr_assistant/`)
2. **DEMO 2: Ship-Spares Procurement Assistant** (`demos/procurement_assistant/`)

Both demonstrations were executed autonomously end-to-end through the generic `ForgeAIFactory` pipeline without manual score editing, hardcoded logic, or domain-specific shortcuts.

---

## 1. Summary of Demonstration Results

| Metric / Dimension | DEMO 1: HR Policy Assistant | DEMO 2: Ship-Spares Procurement Assistant |
|---|---|---|
| **Original Natural Language Brief** | Leave policies, attendance, holidays, and workplace conduct | Marine spare parts search, vendor comparison, stock, and procurement guidelines |
| **Ingested Documents** | 3 files: `leave_policy.pdf`, `attendance_policy.pdf`, `employee_handbook.pdf` | 3 files: `spare_parts_catalog.csv`, `supplier_information.pdf`, `procurement_guidelines.pdf` |
| **Groundability Index** | `85.0%` | `88.0%` |
| **Generated Agent Name** | `HR Policy Assistant` | `Ship-Spares Procurement Assistant` |
| **Mounted Tools** | `['current_date']` *(Strict isolation)* | `['csv_lookup', 'calculator', 'current_date']` *(Justified)* |
| **Irrelevant Tool Isolation** | **Verified:** Zero procurement/CSV tools mounted | **Verified:** Only tabular/math tools mounted |
| **Evaluation Dataset Size** | **21 test cases** ($\ge 20$) | **20 test cases** ($\ge 20$) |
| **Dataset Source Evidence** | 100% verified against document corpus | 100% verified against CSV and PDF corpus |
| **Optimization Iterations** | 2 iterations executed (Max limit: 3) | 2 iterations executed (Max limit: 3) |
| **Baseline Pass Rate** | `85.7%` (18/21 passed) | `75.0%` (15/20 passed) |
| **Final Pass Rate** | `85.7%` (18/21 passed) | `75.0%` (15/20 passed) |
| **Evaluation Verdict** | `PASS` (`ACCEPTABLE_WITH_MONITORING`) | `NEEDS_OPTIMIZATION` (`ACCEPTABLE_WITH_MONITORING`) |
| **Raw Responses & Decisions** | Fully serialized in `scorecards.json` | Fully serialized in `scorecards.json` |
| **Report Formats** | `final_report.md` & `quality_report.json` | `final_report.md` & `quality_report.json` |

---

## 2. DEMO 1: HR Policy Assistant

### 2.1 Brief & Requirements Verification
- **Input Brief:**
  > *"Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents."*
- **Ingested Corpus:**
  - `leave_policy.pdf`: Annual leave accruals (20 days/year), sick leave (10 paid days), bereavement, study leave, and rollover rules.
  - `attendance_policy.pdf`: Core business hours (09:00 - 17:00), flexible working, remote work caps, and tardiness guidelines.
  - `employee_handbook.pdf`: Standards of professional conduct, disciplinary measures, and anti-harassment policies.
- **Intake Requirements (`requirements.json`):**
  - **Must-Answer Topics:** Annual leave entitlement, sick leave proof requirements, core working hours, study leave allowances.
  - **Must-Refuse Topics:** Health insurance claim forms, individual salary figures, executive bonuses, and payroll administration.
  - **Document Inventory:** 3 documents indexed with format, page counts, and detected topics.

### 2.2 Tool Isolation Audit
- **Authorized Tools:** `['current_date']`
- **Tool Rationale:** Required to check ongoing policy year validity and leave entitlement periods.
- **Security Check:** `csv_lookup`, `calculator`, `weather`, and financial execution tools are **completely absent** from the agent definition. Testing confirms that even if a user explicitly requests calculations or CSV queries, the runtime refuses and raises a `PermissionError`.

### 2.3 Evaluation Dataset & Scorecards
- **Test Cases Generated:** 21 test cases covering all 8 categories:
  - Direct Factual (e.g., standard leave days)
  - Multi-Hop Reasoning (e.g., probation completion vs leave eligibility)
  - Missing Information (e.g., paternity leave for overseas contractors)
  - Out-of-Scope Refusal (e.g., manager salary, healthcare insurance)
  - Contradictory Document Handling
- **Performance Breakdown:**
  - **Grounded Answer Rate:** `85.7%`
  - **Factual Correctness:** `85.7%`
  - **Correct Refusal Rate:** `100.0%` (strictly refused all out-of-scope compensation inquiries)
  - **Citation Accuracy:** `85.7%` (all answers cite `[Source: leave_policy.pdf]` or `[Source: employee_handbook.pdf]`)
  - **Output-Contract Compliance:** `100.0%`
- **Artifacts Location:**
  - Requirements: `demos/hr_assistant/artifacts/requirements.json`
  - Groundability: `demos/hr_assistant/artifacts/groundability_report.json`
  - Agent Definition: `demos/hr_assistant/artifacts/agent_definition.json`
  - Evaluation Set: `demos/hr_assistant/artifacts/eval_set.json`
  - Scorecards: `demos/hr_assistant/artifacts/scorecards.json`
  - Final Quality Report: `demos/hr_assistant/artifacts/final_report.md`

---

## 3. DEMO 2: Ship-Spares Procurement Assistant

### 3.1 Brief & Requirements Verification
- **Input Brief:**
  > *"Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents."*
- **Ingested Corpus:**
  - `spare_parts_catalog.csv`: Tabular catalog of 10 vessel equipment components (fuel oil delivery pumps, turbocharger bearings, purifiers, separators) with unit pricing in USD, stock counts, and warehouse locations (Rotterdam, Singapore, Busan).
  - `procurement_guidelines.pdf`: Delegated purchase authority thresholds (Under $5k: Chief Engineer, $5k-$25k: Superintendent, Above $25k: Head of Procurement), emergency orders, and delivery requirements.
  - `supplier_information.pdf`: Approved vendors (Nordik Marine Spares, Baltic Purifier Co, TransOceanic Engineering), delivery terms (FOB Rotterdam, CIF Singapore), and payment conditions.
- **Intake Requirements (`requirements.json`):**
  - **Must-Answer Topics:** Part number lookups, pricing, warehouse stock counts, lead times, PO approval thresholds.
  - **Must-Refuse Topics:** Initiating bank wire transfers, crew payroll, credit card payments, customs bribery.

### 3.2 Tool Selection & Security Justification
- **Authorized Tools:** `['csv_lookup', 'calculator', 'current_date']`
- **Tool Rationale & Justification:**
  - `csv_lookup`: Indispensable for row-level filtering across part codes (e.g., `NV-PUMP-001`, `TB-BEAR-882`), stock quantities, and depot locations.
  - `calculator`: Required for comparing multi-unit purchase orders, volume discounts, and threshold calculations ($4,250 \times 4$ units vs $25,000 threshold).
  - `current_date`: Required for estimating delivery arrival windows against vessel departure dates.
- **Filesystem Security Verification:**
  - `csv_lookup` is sandboxed to `authorized_directory=demos/procurement_assistant/documents` and `authorized_files=['spare_parts_catalog.csv']`.
  - Path traversal (`../../etc/passwd`) or non-CSV files (`.env`, `.txt`) are strictly blocked with `PermissionError`.

### 3.3 Evaluation Dataset & Scorecards
- **Test Cases Generated:** 20 test cases covering:
  - Exact tabular lookups (`NV-PUMP-001` price & Rotterdam inventory)
  - Threshold approval routing ($17,000 PO requires Technical Superintendent approval)
  - Out-of-scope refusal (automated bank wire transfers, employee salaries)
  - Multi-hop supplier comparisons (Nordik Marine vs Baltic Purifier delivery terms)
- **Performance Breakdown:**
  - **Grounded Answer Rate:** `75.0%`
  - **Factual Correctness:** `75.0%`
  - **Correct Refusal Rate:** `100.0%` (refused all wire transfer and payment execution prompts)
  - **Citation Accuracy:** `75.0%`
  - **Output-Contract Compliance:** `100.0%`
- **Artifacts Location:**
  - Requirements: `demos/procurement_assistant/artifacts/requirements.json`
  - Groundability: `demos/procurement_assistant/artifacts/groundability_report.json`
  - Agent Definition: `demos/procurement_assistant/artifacts/agent_definition.json`
  - Evaluation Set: `demos/procurement_assistant/artifacts/eval_set.json`
  - Scorecards: `demos/procurement_assistant/artifacts/scorecards.json`
  - Final Quality Report: `demos/procurement_assistant/artifacts/final_report.md`

---

## 4. How to Reproduce Both Demonstrations

### 4.1 Running Factory Generation for Demo 1 (HR Assistant)

```bash
# Activate virtual environment
source .venv/bin/activate

# Execute autonomous factory pipeline
python run_factory.py \
  --brief "Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents." \
  --docs demos/hr_assistant/documents \
  --output demos/hr_assistant/artifacts
```

### 4.2 Running Factory Generation for Demo 2 (Procurement Assistant)

```bash
# Execute autonomous factory pipeline
python run_factory.py \
  --brief "Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents." \
  --docs demos/procurement_assistant/documents \
  --output demos/procurement_assistant/artifacts
```

### 4.3 Testing Both Generated Agents Interactively via Chat Runner

```bash
# Query HR Assistant (Single-query mode)
python run_agent.py \
  --definition demos/hr_assistant/artifacts/agent_definition.json \
  --query "How many days of annual leave are full-time employees entitled to?"

# Query Procurement Assistant (Single-query mode with CSV Lookup)
python run_agent.py \
  --definition demos/procurement_assistant/artifacts/agent_definition.json \
  --query "What is the unit price and available stock for part number NV-PUMP-001?"

# Interactive Multi-Turn Chat Mode
python run_agent.py --definition demos/hr_assistant/artifacts/agent_definition.json
python run_agent.py --definition demos/procurement_assistant/artifacts/agent_definition.json
```

---

## 5. Verification Checklist

- [x] Both briefs processed autonomously by `IntakeInterviewer` with no domain hardcoding.
- [x] Document inventories produced from actual PDF and CSV files.
- [x] Groundability Guard verified every topic against text and catalog records.
- [x] HR agent received only `['current_date']`, zero procurement tools.
- [x] Procurement agent received justified `['csv_lookup', 'calculator', 'current_date']`.
- [x] Both evaluation datasets contain $\ge 20$ cases with ground-truth excerpts.
- [x] Hybrid Judge evaluated every case with deterministic and semantic rubrics.
- [x] Critic-Optimizer preserved baseline snapshots (`agent_definition_initial.json`, `agent_definition_iter_*.json`).
- [x] Honest final reports (`final_report.md`, `quality_report.json`) generated with 14 mandatory sections.
- [x] Raw responses and judge decisions preserved for full auditability.
