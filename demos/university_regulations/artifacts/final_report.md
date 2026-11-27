# ForgeAI Honest Agent Quality & Observability Report

**Generated On:** 2026-11-27 14:17:06  
**Agent Name:** `University Regulations Assistant`  
**Evaluation Status:** `PRODUCTION_READY`  
**Final Pass Rate:** **100.0%** (Baseline: 100.0%)  
**Optimization Iterations Executed:** 1 (Hard Ceiling: 3)  

---

## 1. Original User Brief

> Create an autonomous University Regulations Assistant that answers student and faculty questions regarding graduation requirements, grading scales, examination guidelines, academic probation, and the student code of conduct using university policy manuals.

---

## 2. Document Inventory

A total of **1** documents were indexed and analyzed:

| Filename | Format | Extracted Pages / Records | Description | Topics Covered |
|---|---|---|---|---|
| `University_Regulations_Test_Document.pdf` | PDF | 1 | Format PDF. Approx 5857 chars. Preview: ST. JUDE METROPOLITAN UNIVERSITY COMPREHENSIVE ACADEMIC REGULATIONS & STUDENT POLICY MANUAL Document Reference: REG-ACAD... | SECTION 1 DEGREE REQUIREMENTS & CREDIT STRUCTURE, SECTION 2 GRADING CRITERIA & ACADEMIC STANDING, SECTION 4 EXAMINATION PROTOCOLS & ATTENDANCE, An Incomplete, SECTION 5 GRADE APPEALS & RE-EVALUATION PETITIONS, SECTION 7 SCOPE BOUNDARIES & PROHIBITED REQUESTS |

---

## 3. Structured Requirements

- **Agent Name:** `University Regulations Assistant`
- **Primary Purpose:** Assist students, faculty, and academic advisors with questions regarding graduation requirements, grading scales, academic probation, examination guidelines, and student conduct based strictly on verified university documents.
- **Target Audience:** University students, academic advisors, and faculty members
- **Operational Scope:** Degree graduation requirements, GPA calculation, academic probation rules, examination conduct, and grievance procedures.
- **Conversational Tone:** Authoritative, academic, and clear

### Must-Answer Topics (5)
- [x] Graduation requirements
- [x] Grading scale and GPA calculation
- [x] Academic probation rules
- [x] Examination guidelines
- [x] Student code of conduct

### Must-Refuse Topics (4)
- [ ] **REFUSE:** Tuition fee waiver processing
- [ ] **REFUSE:** Grade tampering requests
- [ ] **REFUSE:** Financial aid disbursement
- [ ] **REFUSE:** Disciplinary hearing bypass

### Intake Assumptions (4)
- *Assumption:* Academic regulations reflect current catalog year.
- *Assumption:* Unattended defaults apply conservative policy interpretation.
- *Assumption:* Provided documents are treated as the sole ground truth; undocumented claims will be strictly refused.
- *Assumption:* Unanswered clarification questions are resolved using conservative, read-only operational defaults.

### Intake Ambiguities Resolved (1)
- *Ambiguity:* Undergraduate vs graduate credit transfer reciprocity.

---

## 4. Groundability Guard Analysis

- **Overall Groundability Index:** `88.0%`
- **Sanitized Answerable Topics:** Graduation requirements, Grading scale and GPA calculation, Academic probation rules, Examination guidelines, Student code of conduct

### Supported Topics (Corpus Evidenced)
- **Graduation requirements** (Confidence: 94%): Direct textual coverage verified in University_Regulations_Test_Document.pdf. *(Sources: `University_Regulations_Test_Document.pdf`)*
- **Grading scale and GPA calculation** (Confidence: 94%): Direct textual coverage verified in University_Regulations_Test_Document.pdf. *(Sources: `University_Regulations_Test_Document.pdf`)*
- **Academic probation rules** (Confidence: 94%): Direct textual coverage verified in University_Regulations_Test_Document.pdf. *(Sources: `University_Regulations_Test_Document.pdf`)*
- **Examination guidelines** (Confidence: 94%): Direct textual coverage verified in University_Regulations_Test_Document.pdf. *(Sources: `University_Regulations_Test_Document.pdf`)*
- **Student code of conduct** (Confidence: 94%): Direct textual coverage verified in University_Regulations_Test_Document.pdf. *(Sources: `University_Regulations_Test_Document.pdf`)*

### Unsupported Topics (Strict Refusal Enforced)
- **Direct transcript alteration** [missing_from_corpus]: Not found in document corpus or requires unsupported capability.
- **Tuition fee refunds** [missing_from_corpus]: Not found in document corpus or requires unsupported capability.

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
| Reranking Active | `False` | Cross-encoder contextual precision |
| LLM Model | `Ollama Default` | Configurable local/remote LLM backbone |
| Temperature | `0.1` | Low temperature for deterministic factual recall |

---

## 6. Selected Tools & Justification

- **Selected Tools:** `current_date`
- **Tool Isolation Policy:** Only explicitly authorized tools are mounted to this agent runtime. All extraneous or unrequested tools are strictly prohibited.

| Tool Name | Selection Justification |
|---|---|
| `current_date` | Required for temporal verification of operational timestamps. |

---

## 7. Evaluation Dataset Summary

- **Total Test Cases Generated:** `21` (Minimum Requirement: $\ge 20$)
- **Ground-Truth Evidence Verified:** Yes (every expected fact verified against source corpus)
- **Dataset Reused Across Iterations:** Yes (identical fixed test set used for baseline and all optimization passes)

### Test Category Distribution
| Category | Case Count |
|---|---|
| `direct_factual` | 4 |
| `multi_hop` | 2 |
| `grading_and_academic_standing` | 3 |
| `attendance_and_examinations` | 2 |
| `graduation_and_appeals` | 2 |
| `out_of_scope` | 5 |
| `missing_information` | 1 |
| `residential_regulations` | 1 |
| `campus_regulations` | 1 |

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
| **Direct transcript alteration** | `missing_from_corpus` | Not found in document corpus or requires unsupported capability. | Strictly Refuse with scope limitation citation |
| **Tuition fee refunds** | `missing_from_corpus` | Not found in document corpus or requires unsupported capability. | Strictly Refuse with scope limitation citation |

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