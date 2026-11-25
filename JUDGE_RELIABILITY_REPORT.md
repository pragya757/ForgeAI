# ForgeAI – Judge Reliability & Evaluation Matrix Report

**Document Version:** 1.0  
**Phase:** Phase 7 Validation  
**Date:** 2026-11-26  
**Auditor:** Senior GenAI Architect & Evaluation Engineer  
**Component Evaluated:** `app/factory/judge.py` (`HybridJudge`)  
**Test Suite Reference:** `tests/test_judge_reliability_matrix.py` (9/9 Passed)  

---

## Executive Summary

The integrity of an autonomous Agent Factory hinges entirely on the fidelity of its automated judge. If a judge is too lenient (false passes), defective agents are deployed to production. If a judge is too rigid (false rejections), the critic-optimizer wastes cycles attempting unnecessary repairs.

This report evaluates ForgeAI's `HybridJudge` architecture against a dedicated 9-scenario stress-test matrix representing common evaluation challenges in RAG systems: exact citations, missing citations, conflicting numerical values, partial multi-criteria answers, ungrounded hallucinations, correct refusals, improper refusals, semantic paraphrasing, and plausible irrelevant filler.

---

## 1. Hybrid Evaluation Architecture

ForgeAI utilizes a **two-tier hybrid judge**:
1. **Tier 1 (Deterministic Guardrails):**
   - **Lexical & Numerical Fact Checking:** Extracts content tokens (length $\ge 3$) and numerical patterns (`\b\d+(?:\.\d+)?%?\b`). Directly catches numerical contradictions and missing criteria.
   - **Strict Citation Verification:** Checks for `[Source: <filename>]` tags and verifies that cited sources match expected document sources.
   - **Refusal Classification:** Verifies refusal policy compliance deterministically based on standardized boundary phrases and refused state flags.
   - **Structured Contract Validation:** Enforces character length minimums and validates that raw JSON debug dumps are not returned to end-users.
   - **Context Grounding Overlap:** Calculates lexical/morphological overlap between agent response claims and the combination of retrieved chunks, question, and ground truth evidence.

2. **Tier 2 (Semantic LLM Judge):**
   - Evaluates high-level semantic alignment, cross-document reasoning, and paraphrasing using a structured judge prompt ([judge.txt](file:///Users/pragya/Downloads/OceanAI/app/prompts/judge.txt)).
   - Enforces defenses against known evaluator biases:
     - **Verbosity-bias mitigation:** Penalizes long flowery filler that does not provide required facts.
     - **Position-bias mitigation:** Scores facts regardless of presentation order.
     - **Self-preference mitigation:** Anchors judgment strictly to provided ground truth rather than stylistic elegance.
     - **Uncertainty flag:** Explicitly flags ambiguous evidence when confidence falls below 0.8.

3. **Hybrid Score Fusion:**
   - **Factual Correctness:** Uses conservative minimum fusion:
     $$\text{factual\_score} = \min(\text{det\_fact\_score}, \text{llm\_factual})$$
     This guarantees that if mandatory criteria or numerical facts are missing, an overly lenient LLM judge cannot cause a false pass.
   - **Grounding Score:** Employs confidence-aware blend:
     $$\text{grounding\_score} = \max(\text{det\_grounding}, 0.7 \times \text{llm\_grounding} + 0.3 \times \text{det\_grounding})$$
     when $\text{llm\_grounding} \ge 0.8$ and $\text{confidence} \ge 0.8$, allowing semantic equivalence and paraphrased vocabulary to pass while maintaining strict grounding.

---

## 2. Nine-Scenario Evaluation Matrix Results

The matrix was executed via `pytest tests/test_judge_reliability_matrix.py -v`. All 9 scenarios passed assertions with 100% precision:

| # | Scenario Name | Test Case Type | Agent Response Characteristics | Expected Verdict | Actual Verdict | Outcome Classification | Key Score Metrics | Status |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- | :--- | :-: |
| **1** | **Correct Citation** | Direct Factual | Aligns with ground truth, cites `[Source: academic_handbook.pdf]` | **PASS** | **PASS** | `correct_with_evidence` | Fact: 1.0, Ground: 1.0, Cit: 1.0, Refusal: 1.0 | **PASS** |
| **2** | **Missing Citation** | Direct Factual | Exact factual answer text, but completely omits citation tag | **FAIL** | **FAIL** | `correct_without_evidence` | Fact: 1.0, Ground: 1.0, Cit: 0.0, Refusal: 1.0 | **PASS** |
| **3** | **Wrong Numbers** | Numerical Fact | Claims passing grade is 25% instead of ground truth 50% | **FAIL** | **FAIL** | `incorrect` | Fact: 0.0, Ground: 0.88, Cit: 1.0, Failure: `hallucination (numerical contradiction)` | **PASS** |
| **4** | **Partial Answer** | Multi-Hop Criteria | Mentions GPA 3.8 but omits clean disciplinary record requirement | **FAIL** | **FAIL** | `partially_correct` | Fact: 0.50, Ground: 0.88, Cit: 1.0, Failure: `hallucination (omitted mandatory facts)` | **PASS** |
| **5** | **Hallucination** | Invented Claim | Invents guaranteed $1,500 monthly stipend not in handbook | **FAIL** | **FAIL** | `incorrect` | Fact: 0.0, Ground: 0.20, Cit: 1.0, Failure: `hallucination (unsubstantiated claims)` | **PASS** |
| **6** | **Correct Refusal** | Out-of-Scope Query | Successfully refuses aircraft engine question | **PASS** | **PASS** | `correct_refusal` | Fact: 1.0, Ground: 1.0, Cit: 1.0, Refusal: 1.0 | **PASS** |
| **7** | **Incorrect Refusal**| In-Scope Answerable | Erroneously refuses an in-scope question on withdrawal deadline | **FAIL** | **FAIL** | `incorrect_refusal` | Fact: 0.0, Ground: 0.0, Cit: 1.0, Refusal: 0.0, Failure: `wrong_refusal` | **PASS** |
| **8** | **Paraphrased Answer**| Semantic Equivalence| Uses synonyms ("dissertation", "postgraduate", "may 15th") | **PASS** | **PASS** | `correct_with_evidence` | Fact: 1.0, Ground: 0.88, Cit: 1.0, Refusal: 1.0 | **PASS** |
| **9** | **Plausible Irrelevant**| Tangential Filler | Describes student portal registration hours instead of late fee | **FAIL** | **FAIL** | `incorrect` | Fact: 0.0, Ground: 0.88, Cit: 1.0, Failure: `hallucination (failed ground-truth facts)` | **PASS** |

---

## 3. In-Depth Failure Mode Analysis

### 3.1 Scenario 3: Conflicting Numbers (Numerical Accuracy)
- **Challenge:** LLM judges frequently suffer from "number blindness", treating a response as correct because words match (e.g. "minimum passing score is...").
- **ForgeAI Solution:** The deterministic fact-checker extracts all digits and percentages from ground truth facts (`\b\d+(?:\.\d+)?%?\b`). If numbers exist in the ground truth but are absent or contradicted by different numbers in the response (e.g. 25% vs 50%), the fact is penalized to 0.0 and categorized as `hallucination: Expected numerical fact contradicted or missing`.

### 3.2 Scenario 4: Partial Answer (Omitted Criteria)
- **Challenge:** When a query requires multi-part criteria (GPA $\ge 3.8$ AND zero disciplinary reprimands), agents often answer only one part.
- **ForgeAI Solution:** Each expected fact in `expected_facts` is evaluated independently. Factual coverage is computed as:
  $$\text{coverage} = \frac{\text{matched\_facts}}{\text{total\_facts}}$$
  Coverage of $0.50$ triggers outcome classification `partially_correct` and prevents passing status (`passed = False`), signaling the critic-optimizer to expand retrieval depth.

### 3.3 Scenario 8: Paraphrased Answer (Semantic Equivalence)
- **Challenge:** Pure keyword matching fails when an agent uses natural synonyms (e.g. "dissertation" instead of "thesis", "lodge" instead of "submit").
- **ForgeAI Solution:** Substring root matching and morphological trimming (`postgraduate` containing `graduate`, `15th` resolving to `15`) combined with semantic judge grounding verification allow valid natural language variation to score $1.0$ without false negative penalties.

### 3.4 Scenario 9: Plausible Irrelevant Information (Evasion Detection)
- **Challenge:** The agent responds with accurate, well-formatted text from the document corpus (e.g., student portal registration hours), but completely fails to answer the question asked (late registration fee).
- **ForgeAI Solution:** Because the answer contains zero required tokens or numbers from the expected fact ("$100 per week"), `det_fact_score` drops to $0.0$. The conservative minimum fusion forces `final_factual = 0.0`, correctly classifying the response as `incorrect` and failing the evaluation.

---

## 4. Conclusion

The validation matrix confirms that `HybridJudge` effectively eliminates:
1. **False Passes:** Prevented by conservative minimum fusion on factual facts and mandatory citation verification.
2. **False Rejections:** Prevented by morphological normalization, bidirectional substring matching, and semantic LLM judge confidence fusion for paraphrased responses.
3. **Ambiguity Conflation:** Refusals, citation defects, numerical hallucinations, and missing criteria are categorized into distinct actionable failure classes, enabling precise targeted repair by the Critic–Optimizer.
