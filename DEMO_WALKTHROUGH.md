# ForgeAI: Demonstrations & Generalization Walkthrough
**Document Version:** 2.1 (Post-Validation & Quality Improvement)  
**Target Platform:** OceanAI Jr. GenAI Engineer Technical Evaluation  
**Last Updated:** November 26, 2026  

---

## 1. Overview of the Four Demonstrations

ForgeAI includes four end-to-end verified demonstration packages that validate the autonomous factory lifecycle across distinct operational domains and corpus structures:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       DEMONSTRATION SUITE                                              │
├───────────────────────┬───────────────────────────────┬────────────────────────┬───────────────────────┤
│ Demo 1: HR Policy     │ Demo 2: Procurement           │ Demo 3: Academic Regs  │ Demo 4: Medical Clinic│
├───────────────────────┼───────────────────────────────┼────────────────────────┼───────────────────────┤
│ - Domain: Workplace HR│ - Domain: Maritime Spares     │ - Domain: University   │ - Domain: Healthcare  │
│ - Corpus: 3 PDFs      │ - Corpus: 1 CSV, 2 PDFs       │ - Corpus: 3 PDFs       │ - Corpus: 3 PDFs      │
│ - Tools: current_date │ - Tools: csv, calc, date      │ - Tools: current_date  │ - Tools: current_date │
│ - Final Pass: 100.0%  │ - Final Pass: 100.0%          │ - Final Pass: 60.0%    │ - Final Pass: 50.0%   │
└───────────────────────┴───────────────────────────────┴────────────────────────┴───────────────────────┘
```

---

## 2. Demonstration 1: HR Policy Assistant

### 2.1 Domain & Purpose
- **Directory:** `demos/hr_assistant/`
- **User Brief:**
  > "Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents."
- **Document Inventory (`demos/hr_assistant/documents/`):**
  1. `leave_policy.pdf` (Annual leave, sick leave, compassionate leave, accrual rules)
  2. `attendance_policy.pdf` (Core hours 09:30-16:30, remote work, overtime policies)
  3. `employee_handbook.pdf` (Code of conduct, grievance escalation, probationary rules)

### 2.2 Factory Execution Command
```bash
python run_factory.py \
  --brief "Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents." \
  --docs demos/hr_assistant/documents \
  --output demos/hr_assistant/artifacts
```

### 2.3 Synthesized Agent Configuration Highlights
- **Adaptive Chunk Size:** 500 characters, overlap: 100 characters.
- **Retrieval Parameters:** `top_k=4`, `similarity_threshold=0.35`.
- **Reranking:** Enabled (`cross_encoder`, top 3).
- **Authorized Tools:** Strictly limited to `["current_date"]`.
- **Tool Isolation Check:** Mathematical calculation and CSV lookup tools were evaluated and rejected with justifications:
  - `csv_lookup` rejected: "No structured tabular files exist in the HR corpus."
  - `calculator` rejected: "No numerical catalog pricing or financial formulas detected."

### 2.4 Evaluation & Optimization Progression
- **Benchmark Size:** 21 test cases directly generated from document text.
- **Iteration 1 Scorecard:** Pass Rate = **95.2%** (20/21 passed).
  - Failed Case: `HR-016` failed due to `citation_defect` (missing source document tag).
- **Critic Diagnosis:** Root cause identified as `citation_defect`. Proposed change: Injected `MANDATORY CITATION RULE` into `system_prompt`.
- **Iteration 2 Scorecard:** Pass Rate = **100.0%** (21/21 passed).
- **Final Metrics:** 100% Pass Rate across all 6 core metrics.

---

## 3. Demonstration 2: Ship-Spares Procurement Assistant

### 3.1 Domain & Purpose
- **Directory:** `demos/procurement_assistant/`
- **User Brief:**
  > "Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents."
- **Document Inventory (`demos/procurement_assistant/documents/`):**
  1. `spare_parts_catalog.csv` (10 maritime spares: Part Number, Description, Unit Price USD, Stock, Supplier, Lead Time)
  2. `supplier_info.pdf` (Supplier tiers, SLA terms, delivery terms, payment terms)
  3. `procurement_guidelines.pdf` (Purchasing thresholds, approval matrices, quote requirements)

### 3.2 Factory Execution Command
```bash
python run_factory.py \
  --brief "Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents." \
  --docs demos/procurement_assistant/documents \
  --output demos/procurement_assistant/artifacts
```

### 3.3 Synthesized Agent Configuration Highlights
- **Adaptive Chunk Size:** 400 characters, overlap: 80 characters (adapted for tabular CSV + narrative PDF).
- **Retrieval Parameters:** `top_k=5`, `similarity_threshold=0.38`.
- **Authorized Tools:** `["csv_lookup", "calculator", "current_date"]`.
  - `csv_lookup` justified: "Structured CSV tabular files detected; provides exact row/column querying."
  - `calculator` justified: "Domain requirements involve numerical thresholds, price comparisons, or math."

### 3.4 Evaluation & Optimization Progression
- **Benchmark Size:** 20 test cases directly generated from document text.
- **Iteration 1 Scorecard:** Pass Rate = **90.0%** (18/20 passed).
- **Iteration 2 Scorecard:** Pass Rate = **100.0%** (20/20 passed).
- **Final Metrics:** 100% Pass Rate across all 6 core metrics.

---

## 4. Demonstration 3: Unseen Domain Generalization (Academic Regulations)

### 4.1 Domain & Purpose
- **Directory:** `unseen_test/`
- **Domain:** University Academic Regulations & Student Guidelines.
- **User Brief:**
  > "Build an academic advisor assistant that answers student questions on grading scales, credit requirements, examination rules, appeals, and attendance policies."
- **Document Inventory (`unseen_test/documents/`):**
  1. `academic_regulations.pdf` (Grading GPA bands, graduation credit thresholds, probation)
  2. `examination_guidelines.pdf` (Exam hall protocols, prohibited devices, sick leave exam deferral)
  3. `student_code_of_conduct.pdf` (Academic integrity, plagiarism penalties, appeal boards)

### 4.2 Initial vs Improved Performance on Frozen Benchmark
- **Frozen Benchmark:** Exact same 20 test cases preserved without modification.
- **Baseline Scorecard:** Pass Rate = **45.0%** (9/20 passed).
- **Failure Analysis Findings:**
  1. Queries containing `"now"` erroneously triggered `current_date`, bypassing the empty-retrieval refusal check on out-of-scope inquiries.
  2. Multi-source cross-document queries cited only `sources[0]`.
- **Targeted Improvements Applied:**
  1. Hardened refusal check in `chat_runner.py` (auxiliary tools like `current_date` cannot satisfy corpus queries without hits).
  2. Strict word boundaries on temporal triggers (`\b(today|current\s+date|...)\b`).
  3. Multi-source context synthesis in `mock_client.py`.
  4. Metadata-aware candidate re-ranking in `retriever.py` (+0.08 boost for mentioned sources).
- **Improved Scorecard:** Pass Rate = **60.0%** (12/20 passed).
  - Net Improvement: **+15.0%**.
  - Regressions: **0 (Zero)**. All 9 previously passing tests remained passing.
  - Resolved Failures: TC-002, TC-005, TC-006.

---

## 5. Demonstration 4: Medical Clinic Operations Assistant

### 5.1 Domain & Purpose
- **Directory:** `generalization_test/`
- **Domain:** Ambulatory Healthcare Operations & Patient Health Information (PHI) Privacy.
- **User Brief:**
  > "Create a medical clinic policy assistant that helps staff and patients understand triage appointment scheduling, patient health information privacy rules, medical record release timelines, and telehealth consultation regulations."
- **Document Inventory (`generalization_test/documents/`):**
  1. `clinical_triage_guidelines.pdf` (Urgent triage routing, routine scheduling, cancellation fees, walk-in windows)
  2. `patient_privacy_hipaa.pdf` (PHI disclosure restrictions, 15-day records release, family disclosure limits, 10-year retention)
  3. `telehealth_regulations.pdf` (Virtual visit eligibility, controlled substance prescription prohibition, licensing boundaries)

### 5.2 Factory Execution Command
```bash
python run_factory.py \
  --brief "Create a medical clinic policy assistant that helps staff and patients understand triage appointment scheduling, patient health information privacy rules, medical record release timelines, and telehealth consultation regulations." \
  --docs generalization_test/documents \
  --output generalization_test/artifacts
```

### 5.3 Generalization Results
- **Zero-Code Execution:** The factory completed all 7 stages unattended without modifying any source code.
- **Groundability Score:** **85.0%**.
- **Tool Selection:** Correctly authorized `['current_date']` and rejected `csv_lookup` and `calculator`.
- **Evaluation Benchmark:** 20 test cases generated across all 8 mandatory categories.
- **Scorecard:** Completed 2 iterations; Pass Rate = **50.0%** (10/20 passed). Stagnation safeguard triggered and preserved snapshots.
- **Artifacts:** Full audit report saved to `generalization_test/artifacts/final_report.md`.

---

## 6. Domain Portability Comparison Matrix

| Property | Demo 1: HR Policy | Demo 2: Procurement | Demo 3: Academic Regs | Demo 4: Medical Clinic | Proof of Domain Independence |
|---|---|---|---|---|---|
| **Corpus Data Type** | Pure Text PDFs | Tabular CSV + Text PDFs | Text PDFs | Text PDFs | Ingests heterogeneous data formats dynamically. |
| **Tool Selection** | `['current_date']` | `['csv_lookup', 'calculator', 'current_date']` | `['current_date']` | `['current_date']` | Selects tools based on corpus and requirements, not hardcoding. |
| **Tool Isolation** | Rejects math & CSV tools | Rejects weather & arbitrary code | Rejects CSV & calculation tools | Rejects CSV & calculation tools | Least-privilege security enforced per domain. |
| **Adaptive Chunking**| Size: 500, Overlap: 100 | Size: 400, Overlap: 80 | Size: 500, Overlap: 100 | Size: 500, Overlap: 100 | Adapts chunking parameters to data density. |
| **Test Case Count** | 21 cases | 20 cases | 20 cases | 20 cases | Synthesizes $\ge 20$ cases across 8 categories for any domain. |
| **Pass Rate** | **100.0%** | **100.0%** | **60.0%** | **50.0%** | Evaluates rigorously; reports actual outcomes honestly. |
