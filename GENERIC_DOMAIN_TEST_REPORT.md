# GENERIC DOMAIN TEST REPORT
**ForgeAI Zero-Shot Generalization Audit**  
**Tested Domain:** Maritime Environmental Compliance / MARPOL Vessel Regulations  
**Source Document:** `tests/fixtures/maritime_environmental_compliance.txt` (3,735 bytes)  
**Date:** 2026-11-28  

---

## 1. Domain Unseen Verification

To confirm that the factory genuinely operates as an autonomous agent factory rather than relying on predefined demo directories or hardcoded mock branches:
- **No Domain Hardcoding:** The string `"maritime_environmental_compliance"` was **NOT** added to `MockLLMClient._detect_domain`.
- **Verified Routing:** `MockLLMClient._detect_domain()` evaluated the brief and document text as strictly `'generic'`.
- **Zero Hardcoded Q&A:** No questions or answers from this document exist anywhere in `mock_client.py`.

---

## 2. Stage-by-Stage Generic Pipeline Results

### Stage 1: Document Ingestion & Manifest Generation
- **Ingestion Result:** Successfully stored in an isolated session directory (`data/sessions/session_20261128_010359_542ea937/documents/`).
- **Corpus Manifest:** `corpus_manifest.json` generated with document size (3,735 bytes), format (`TXT`), and SHA-256 hash.
- **Verification:** Succeeded without manual folder creation.

### Stage 2: Brief Understanding & Intake Interview
- **User Brief:** *"Create an autonomous AI assistant for ocean vessel environmental compliance covering MARPOL regulations, bilge oil separators, sewage, ballast water, and garbage disposal."*
- **Requirements Generated:** `requirements.json` produced dynamically.
- **Extracted Agent Name:** `Autonomous Ai Assistant`
- **Extracted Domain:** `Maritime Operations & Environmental Compliance`

### Stage 3: Groundability Guard Analysis
- **Groundability Score:** `88.0%`
- **Supported Topics Identified:** 3 topics (Bilge oily water separation, sewage discharge limits, ballast water management).
- **Unsupported / Scope Gaps Identified:** Vessel charterparty negotiations, crew income taxes, cargo sales contracts.

### Stage 4: Declarative Agent Definition Synthesis
- **Artifact:** `agent_definition.json` generated.
- **Configuration:** Chunk size 400, overlap 50, top_k 4, temperature 0.1, tool `current_date` enabled.
- **Refusal Phrase:** Standardized boundary contract applied.

### Stage 5: Automatic Evaluation Set Generation (>= 20 Cases)
- **Total Test Cases Generated:** **20 cases** (`TC-001` to `TC-020`).
- **Synthesis Mode:** Generated dynamically from document text clauses via `AutomaticEvalGenerator.generate_dynamic_eval_cases()`.
- **Category Coverage:**
  - `direct_factual`: 4 cases (e.g. 15 ppm oily water separator limit)
  - `multi_hop`: 3 cases (e.g. sewage discharge vs ballast water exchange distances)
  - `ambiguous`: 2 cases (e.g. general allowance limits requiring clarification)
  - `missing_information`: 2 cases (e.g. 2035 extended equipment warranty reimbursement)
  - `out_of_scope`: 9 cases (e.g. cargo freight rate negotiations, customs tariff clearance)

### Stage 6: Evaluation & Critic-Optimizer Loop
- **Iteration 1 Pass Rate:** **70.0%** (14 passed / 20 total)
  - Grounding Score: 0.80
  - Factual Correctness: 0.775
  - Citation Correctness: 0.887
  - Refusal Correctness: 0.70
  - Identified Failures: 6 failures (3 retrieval misses, 3 hallucination/refusal boundary mismatches).
- **Critic-Optimizer Proposal:**
  - Increased `top_k` from 4 to 5 to expand context window.
  - Enhanced system prompt with strict sentence-level citation enforcement.
- **Iteration 2 Pass Rate:** **70.0%** (14 passed / 20 total)
  - Pass rate plateaued at 70.0% due to mock retrieval limits on complex multi-hop queries.
- **Total Iterations:** 2 iterations executed (within $\le 3$ limit).
- **Honest Pipeline Status:** **`NEEDS_OPTIMIZATION`** (Score was NOT artificially forced to 100%).

### Stage 7: Reporting & Observability
- All standard artifacts written to isolated directory:
  - `final_report.md`
  - `quality_report.json`
  - `scorecards.json`
  - `iteration_logs.json`
  - `agent_definition.json`

---

## 3. Playground Runtime & Boundary Test

Using `GenericChatRunner` mounted on the generated `AgentDefinition` and the isolated document folder:

1. **Answerable Grounded Factual Query:**
   - **Query:** *"What is the maximum oil discharge limit for oily water separators under MARPOL Annex I?"*
   - **Response:** *"Based on verified documentation: Under MARPOL Annex I, machinery space oily bilge water may only be discharged overboard when the vessel is en route, the oily mixture is processed through an approved 15 ppm oil filtering equipment (oily water separator), and the automatic stopping device activates immediately if oil content exceeds 15 parts per million (15 ppm)..."*
   - **Citation:** `[Source: maritime_environmental_compliance.txt, Page: 1]`
   - **Refused:** `False`
   - **Result:** **PASSED** (Grounded fact retrieved with exact citation).

2. **Out-of-Scope Boundary Refusal Query:**
   - **Query:** *"What is the corporate freight rate and cargo sales commission for chartering this vessel?"*
   - **Response:** *"I cannot answer this question as it is outside my verified documentation scope. This manual establishes environmental compliance standards for ocean-going vessels under international MARPOL protocols. It does not provide maritime insurance dispute advice, crew income tax consulting, cargo charterparty negotiations, or customs tariff determinations..."*
   - **Citation:** `[Source: maritime_environmental_compliance.txt, Page: 1]`
   - **Refused:** `True`
   - **Result:** **PASSED** (Correctly triggered refusal based on boundary clause in Section 1 and Section 9).
