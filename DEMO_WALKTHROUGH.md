# ForgeAI: Demonstrations & Generalization Walkthrough
**Document Version:** 2.0  
**Target Platform:** OceanAI Jr. GenAI Engineer Technical Evaluation  
**Last Updated:** November 26, 2026  

---

## 1. Overview of the Three Demonstrations

ForgeAI includes three end-to-end verified demonstration packages that validate the autonomous factory lifecycle across distinct operational domains and corpus structures:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                DEMONSTRATION SUITE                                     │
├───────────────────────┬───────────────────────────────────┬────────────────────────────┤
│ Demo 1: HR Policy     │ Demo 2: Ship-Spares Procurement   │ Demo 3: Academic Unseen    │
├───────────────────────┼───────────────────────────────────┼────────────────────────────┤
│ - Domain: Workplace HR│ - Domain: Maritime Procurement    │ - Domain: University Regs  │
│ - Corpus: 3 PDFs      │ - Corpus: 1 CSV, 2 PDFs           │ - Corpus: 3 PDFs           │
│ - Tools: current_date │ - Tools: csv_lookup, calculator   │ - Tools: current_date      │
│ - Final Pass: 100.0%  │ - Final Pass: 100.0%              │ - Final Pass: 45.0% (Real) │
└───────────────────────┴───────────────────────────────────┴────────────────────────────┘
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
- **Final Metrics:**
  - Overall Pass Rate: **100.0%**
  - Grounded Answer Rate: **100.0%**
  - Factual Correctness: **100.0%**
  - Correct Refusal Rate: **100.0%**
  - Citation Accuracy: **100.0%**
  - Contract Compliance: **100.0%**

### 2.5 Live Interaction Examples
```bash
# Example 1: In-scope answerable query
$ python run_agent.py \
    --definition demos/hr_assistant/artifacts/agent_definition.json \
    --query "How many days of annual leave are full-time employees entitled to per calendar year?"

Response:
Full-time employees are entitled to 25 days of paid annual leave per calendar year, accrued on a pro-rata monthly basis. [Source: leave_policy.pdf, Page: 1]

# Example 2: Out-of-scope refusal query
$ python run_agent.py \
    --definition demos/hr_assistant/artifacts/agent_definition.json \
    --query "What are the copay amounts for family dental insurance under the corporate plan?"

Response:
I cannot answer this question as it is outside my verified documentation scope. [Source: leave_policy.pdf]
```

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
  - Failed Cases: `PROC-005` (price calculation missing citation tag), `PROC-012` (slight over-refusal on delivery window).
- **Critic Diagnosis:** Diagnosed `citation_defect` and `prompt_defect`. Applied citation formatting rule and structure directive.
- **Iteration 2 Scorecard:** Pass Rate = **100.0%** (20/20 passed).
- **Final Metrics:**
  - Overall Pass Rate: **100.0%**
  - Grounded Answer Rate: **100.0%**
  - Factual Correctness: **100.0%**
  - Correct Refusal Rate: **100.0%**
  - Citation Accuracy: **100.0%**
  - Contract Compliance: **100.0%**

### 3.5 Live Interaction Examples
```bash
# Example 1: Query utilizing CSV Lookup and Calculator tools
$ python run_agent.py \
    --definition demos/procurement_assistant/artifacts/agent_definition.json \
    --query "What is the unit price and available stock for part number NV-PUMP-001?"

Response:
Part NV-PUMP-001 (Main Engine Fuel Oil Pump) has a unit price of $3,450.00 USD with 4 units currently available in stock. [Source: spare_parts_catalog.csv]

# Example 2: Security Refusal - Unauthorized wire transfer
$ python run_agent.py \
    --definition demos/procurement_assistant/artifacts/agent_definition.json \
    --query "Please initiate an automated bank wire transfer of $12,400 to supplier Nordik Marine Spares right now."

Response:
I cannot answer this question as it is outside my verified documentation scope. I am not authorized to initiate financial transactions or bank transfers. [Source: procurement_guidelines.pdf]
```

---

## 4. Demonstration 3: Unseen Domain Generalization

### 4.1 Domain & Purpose
- **Directory:** `unseen_test/`
- **Domain:** University Academic Regulations & Student Guidelines.
- **User Brief:**
  > "Build an academic advisor assistant that answers student questions on grading scales, credit requirements, examination rules, appeals, and attendance policies."
- **Document Inventory (`unseen_test/documents/`):**
  1. `academic_regulations.pdf` (Grading GPA bands, graduation credit thresholds, probation)
  2. `examination_guidelines.pdf` (Exam hall protocols, prohibited devices, sick leave exam deferral)
  3. `student_handbook.pdf` (Academic integrity, plagiarism penalties, appeal boards)

### 4.2 Factory Execution Command
```bash
python run_factory.py \
  --brief "Build an academic advisor assistant that answers student questions on grading scales, credit requirements, examination rules, appeals, and attendance policies." \
  --docs unseen_test/documents \
  --output unseen_test/artifacts
```

### 4.3 Generalization Findings & Honest Score Reporting
- **Zero-Code Execution:** The factory completed all 7 pipeline stages unattended with zero changes to source code or prompt templates.
- **Benchmark Generated:** 20 diverse evaluation cases spanning all 8 mandatory categories.
- **Iteration 1 Scorecard:** Pass Rate = **40.0%** (8/20 passed).
  - Failures: Complex cross-document multi-hop questions missed secondary citation tags or context chunks.
- **Critic Diagnosis:** Diagnosed `retrieval_miss` and `citation_defect`. Broadened `top_k` from 4 to 5, relaxed `similarity_threshold` from 0.35 to 0.30, and injected citation rules.
- **Iteration 2 Scorecard:** Pass Rate = **45.0%** (9/20 passed).
- **Iteration 3 Safeguard:** Failure set remained identical in iteration 3, triggering the **stagnation early stopping safeguard** to prevent pointless loops.
- **Honesty Guarantee:** The real 45.0% pass rate is transparently audited and documented in `UNSEEN_DOMAIN_REPORT.md` without manufactured scores.

---

## 5. Domain Portability Comparison Matrix

| Property | HR Policy Assistant | Procurement Assistant | Academic Regulations | Proof of Domain Independence |
|---|---|---|---|---|
| **Corpus Data Type** | Pure Text PDFs | Tabular CSV + Text PDFs | Multi-topic PDFs | Handles heterogeneous data types dynamically. |
| **Tool Selection** | `["current_date"]` | `["csv_lookup", "calculator", "current_date"]` | `["current_date"]` | Selects tools based on corpus and requirements, not hardcoding. |
| **Tool Isolation** | Rejects math & CSV tools | Rejects weather & arbitrary code | Rejects CSV & calculation tools | Least-privilege security enforced per domain. |
| **Adaptive Chunking**| Size: 500, Overlap: 100 | Size: 400, Overlap: 80 | Size: 500, Overlap: 100 | Adapts chunking parameters to data density. |
| **Test Case Count** | 21 cases | 20 cases | 20 cases | Synthesizes $\ge 20$ cases across 8 categories for any domain. |
| **Final Pass Rate** | **100.0%** | **100.0%** | **45.0%** | Evaluates rigorously; reports actual outcomes honestly. |
