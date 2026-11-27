# ForgeAI Honest Agent Quality & Observability Report

**Generated On:** 2026-11-27 11:38:25  
**Agent Name:** `HR Policy Assistant`  
**Evaluation Status:** `PRODUCTION_READY`  
**Final Pass Rate:** **100.0%** (Baseline: 100.0%)  
**Optimization Iterations Executed:** 1 (Hard Ceiling: 3)  

---

## 1. Original User Brief

> Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents.

---

## 2. Document Inventory

A total of **3** documents were indexed and analyzed:

| Filename | Format | Extracted Pages / Records | Description | Topics Covered |
|---|---|---|---|---|
| `attendance_policy.pdf` | PDF | 1 | Format PDF. Approx 1483 chars. Preview: APEX GLOBAL TECHNOLOGIES - WORKPLACE ATTENDANCE & HOURS POLICY DOCUMENT REF: POL-HR-002 | REVISED OPERATIONAL STANDARDS ... | SECTION 1 WORKING HOURS & COLLABORATION CORE, Business Hours, SECTION 2 PUNCTUALITY & TARDINESS, SECTION 3 PUBLIC HOLIDAYS & OVERTIME RULES, SECTION 4 UNEXCUSED ABSENCES & JOB ABANDONMENT |
| `employee_handbook.pdf` | PDF | 1 | Format PDF. Approx 1963 chars. Preview: APEX GLOBAL TECHNOLOGIES - GENERAL EMPLOYEE HANDBOOK DOCUMENT REF: HB-CORP-2024 | GENERAL CODE OF CONDUCT & OPERATIONS S... | SECTION 1 INTRODUCTION & ETHICAL CODE, SECTION 2 PROBATIONARY EMPLOYMENT, SECTION 4 PROGRESSIVE DISCIPLINARY PROCEDURE, SECTION 5 RESIGNATION & NOTICE PERIOD, confirmed employees must provide thirty |
| `leave_policy.pdf` | PDF | 1 | Format PDF. Approx 1951 chars. Preview: APEX GLOBAL TECHNOLOGIES - HR POLICY MANUAL DOCUMENT REF: POL-HR-001 | VERSION 3.2 | ANNUAL REVISION SECTION 1: PURPOSE ... | SECTION 1 PURPOSE AND APPLICABILITY, SECTION 2 ANNUAL LEAVE (VACATION), SECTION 3 SICK LEAVE & MEDICAL EMERGENCIES, SECTION 4 COMPASSIONATE & BEREAVEMENT LEAVE, SECTION 5 PARENTAL & PATERNITY LEAVE |

---

## 3. Structured Requirements

- **Agent Name:** `HR Policy Assistant`
- **Primary Purpose:** Assist employees with inquiries regarding leave policies, attendance rules, holidays, and workplace guidelines based strictly on verified documents.
- **Target Audience:** Company employees, managers, and HR administrators
- **Operational Scope:** Company leave rules, attendance standards, working hours, and conduct guidelines.
- **Conversational Tone:** Professional, supportive, and precise

### Must-Answer Topics (6)
- [x] Annual leave
- [x] Sick leave
- [x] Attendance tracking
- [x] Office working hours
- [x] Code of conduct
- [x] Probation period leave

### Must-Refuse Topics (5)
- [ ] **REFUSE:** Personal salary records
- [ ] **REFUSE:** Stock option plans
- [ ] **REFUSE:** Health insurance claim processing
- [ ] **REFUSE:** Individual performance reviews
- [ ] **REFUSE:** Direct payroll execution

### Intake Assumptions (4)
- *Assumption:* Documents provided represent current company policy for the ongoing fiscal year.
- *Assumption:* In unattended mode, unsupported inquiries will be strictly refused.
- *Assumption:* Provided documents are treated as the sole ground truth; undocumented claims will be strictly refused.
- *Assumption:* Unanswered clarification questions are resolved using conservative, read-only operational defaults.

### Intake Ambiguities Resolved (1)
- *Ambiguity:* Overtime eligibility criteria for contractors vs permanent employees.

---

## 4. Groundability Guard Analysis

- **Overall Groundability Index:** `85.0%`
- **Sanitized Answerable Topics:** Annual leave entitlement, Sick leave policy, Working hours and attendance, Workplace conduct, Remote work / Work from home

### Supported Topics (Corpus Evidenced)
- **Annual leave entitlement** (Confidence: 98%): Document specifies 20 days annual leave with carryover limit. *(Sources: `leave_policy.pdf`)*
- **Sick leave policy** (Confidence: 97%): 10 days paid sick leave with medical certificate requirement. *(Sources: `leave_policy.pdf`)*
- **Working hours and attendance** (Confidence: 95%): Standard hours 8:30 AM to 5:30 PM with 15-minute grace period. *(Sources: `attendance_policy.pdf`)*
- **Workplace conduct** (Confidence: 94%): Harassment-free workplace and disciplinary stages detailed. *(Sources: `employee_handbook.pdf`)*

### Partially Supported Topics
- **Remote work / Work from home**: Missing: Equipment reimbursement for home office is not covered. *(Sources: `attendance_policy.pdf`)*

### Unsupported Topics (Strict Refusal Enforced)
- **Health insurance claims** [missing_from_corpus]: No insurance policy or benefits document provided.
- **Salary and bonus calculation** [missing_from_corpus]: Compensation schedules are absent from the document corpus.

---

## 5. Generated Agent Configuration

| Configuration Field | Active Value | Technical Justification |
|---|---|---|
| Embedding Model | `all-MiniLM-L6-v2` | Dense semantic vector representations |
| Retrieval Method | `dense_vector_faiss` | FAISS cosine similarity vector search |
| Chunk Size | `500` chars | Aligned with document paragraph boundaries |
| Chunk Overlap | `100` chars | Cross-chunk context retention |
| Retrieval Top-K | `4` | Context recall vs noise balance |
| Similarity Threshold | `0.35` | Cutoff barrier preventing irrelevant hallucinations |
| Reranking Active | `True` | Cross-encoder contextual precision |
| LLM Model | `Ollama Default` | Configurable local/remote LLM backbone |
| Temperature | `0.1` | Low temperature for deterministic factual recall |

---

## 6. Selected Tools & Justification

- **Selected Tools:** `current_date`
- **Tool Isolation Policy:** Only explicitly authorized tools are mounted to this agent runtime. All extraneous or unrequested tools are strictly prohibited.

| Tool Name | Selection Justification |
|---|---|
| `current_date` | Required for checking ongoing policy year validity and leave balance periods. |

---

## 7. Evaluation Dataset Summary

- **Total Test Cases Generated:** `21` (Minimum Requirement: $\ge 20$)
- **Ground-Truth Evidence Verified:** Yes (every expected fact verified against source corpus)
- **Dataset Reused Across Iterations:** Yes (identical fixed test set used for baseline and all optimization passes)

### Test Category Distribution
| Category | Case Count |
|---|---|
| `answerable` | 10 |
| `out_of_scope` | 6 |
| `edge_case` | 5 |

---

## 8. Baseline Initial Scorecard (Iteration 1)

- **Initial Total Tests:** `21`
- **Initial Passed Tests:** `21`
- **Initial Failed Tests:** `0`
- **Initial Pass Rate:** **100.0%**

| Baseline Metric | Score |
|---|---|
| Overall Pass Rate | `100.0%` |
| Grounded Answer Rate | `100.0%` |
| Factual Correctness | `100.0%` |
| Correct Refusal Rate | `100.0%` |
| Citation Accuracy | `100.0%` |
| Output-Contract Compliance | `100.0%` |

---

## 9. Optimization Iteration History

| Iteration | Total | Passed | Failed | Pass Rate | Grounding | Factual | Citation | Refusal | Contract | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Iteration 1 | 21 | 21 | 0 | **100.0%** | 100% | 100% | 100% | 100% | 100% | `PASS` |

### Critic-Optimizer Action Log

No optimizer iterations required; baseline configuration achieved passing criteria on first pass.
---

## 10. Before-and-After Score Comparison

| Core Evaluation Metric | Baseline Score (Iter 1) | Final Score (Iter 1) | Net Delta | Improvement Status |
|---|---|---|---|---|
| **Overall Pass Rate** | 100.0% | **100.0%** | **0.0%** | `UNCHANGED` |
| **Grounded Answer Rate** | 100.0% | **100.0%** | **0.0%** | `UNCHANGED` |
| **Factual Correctness** | 100.0% | **100.0%** | **0.0%** | `UNCHANGED` |
| **Correct Refusal Rate** | 100.0% | **100.0%** | **0.0%** | `UNCHANGED` |
| **Citation Accuracy** | 100.0% | **100.0%** | **0.0%** | `UNCHANGED` |
| **Output-Contract Compliance** | 100.0% | **100.0%** | **0.0%** | `UNCHANGED` |

---

## 11. Remaining Failed Cases & Raw Audit Logs

All evaluation test cases passed successfully. Zero remaining defects detected.
---

## 12. Unsupported Topics & Refusal Policy

The following topics are explicitly excluded from the agent's answerable scope to prevent hallucinations:

| Topic | Classification / Nature | Rejection Reason | Refusal Policy |
|---|---|---|---|
| **Health insurance claims** | `missing_from_corpus` | No insurance policy or benefits document provided. | Strictly Refuse with scope limitation citation |
| **Salary and bonus calculation** | `missing_from_corpus` | Compensation schedules are absent from the document corpus. | Strictly Refuse with scope limitation citation |

---

## 13. Known Limitations & Operational Boundaries

- 1. Corpus Boundary Constraint: The agent answers strictly from provided text. Topics not documented in indexed sources are systematically refused.
- 2. Non-Extrapolation Grounding: The agent is forbidden from assuming or estimating dates, figures, or policies not explicitly written in source files.
- 3. OCR / Parser Dependency: Text fidelity depends on pre-extracted formatting. Complex scanned PDF diagrams require textual extraction.
- 4. Refusal Policy Conservatism: Inquiries containing partial overlap with prohibited subjects default to conservative refusal to safeguard against misinformation.

---

## 14. Final Agent Status & Reproducibility Verification

- **Operational Readiness:** `PRODUCTION_READY`
- **Final Pass Rate:** **100.0%**
- **Deployment Recommendation:** Approved for production runtime deployment.
- **Mathematical Reproducibility Certificate:** All scores presented in this report are directly derived from the serialized test cases in `scorecards.json`. Re-evaluating the raw case scores yields exact arithmetic parity with the reported metrics.

---
*Generated autonomously by ForgeAI - Autonomous AI Agent Factory*