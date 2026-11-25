# ForgeAI: Evaluation & Scoring Methodology
**Document Version:** 2.0  
**Target Platform:** OceanAI Jr. GenAI Engineer Technical Evaluation  
**Last Updated:** November 26, 2026  

---

## 1. Overview of Hybrid Evaluation Architecture

Evaluating enterprise AI agents requires balancing two competing engineering goals:
1. **Mathematical Rigor:** Objective, verifiable assertions regarding facts, citations, refusal policies, and structured output formatting.
2. **Semantic Flexibility:** Recognizing linguistic paraphrasing, multi-sentence reasoning, and contextual answer completeness.

Pure LLM judges suffer from notorious vulnerabilities: **verbosity bias** (favoring long-winded answers), **position bias** (favoring specific response orders in pairwise setups), and **self-preference bias** (giving high scores to answers echoing the model's own style). Pure regex or string matching, on the other hand, fails to recognize legitimate rephrasing.

**ForgeAI resolves this via a Hybrid Evaluation Architecture (`app/factory/judge.py`):**
- **First Layer (Deterministic Assertions):** Executes strict programmatic verifications on lexical tokens, citation tags, refusal markers, and schema contracts.
- **Second Layer (Semantic LLM Judge):** Evaluates semantic equivalence, completeness, and query relevance using an isolated prompt template with temperature 0.0.
- **Score Fusion:** Employs a conservative minimum principle (`min(det, llm)`) to eliminate false passes.

```
                          [ Candidate Agent Response ]
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
 [ Deterministic Evaluators ]                           [ Semantic LLM Judge ]
 - Refusal keywords & flags                             - Semantic completeness
 - Citation regex [Source: ...]                         - Paraphrase accuracy
 - Fact token overlap (>= 80% / >= 40%)                 - Query relevance
 - Context chunk grounding overlap                      - Uncertainty scoring
 - Length & raw code dump check                         - Bias mitigation prompts
            │                                                     │
            └──────────────────────────┬──────────────────────────┘
                                       ▼
                       [ Score Fusion & Conservative Min ]
                                       │
                                       ▼
                       [ 6 Discrete Outcome Classifications ]
                                       │
                                       ▼
                       [ Final Pass / Fail Determination ]
```

---

## 2. The Six Standardized Evaluation Metrics

Every response is evaluated on six distinct dimensions scored between `0.0` and `1.0`:

### 1. Grounding Score ($G$)
- **Purpose:** Verifies that all factual claims made in the answer are substantiated by the retrieved document chunks rather than extrapolated from pre-trained parametric memory.
- **Deterministic Check:** Cleans the response of citation boilerplate, extracts content words (length $\ge 4$, non-stopwords), and computes the ratio of content tokens present in the retrieved context:
  $$\text{Grounding Ratio} = \frac{|\text{Tokens}(\text{Response}) \cap \text{Tokens}(\text{Context} \cup \text{Question})|}{|\text{Tokens}(\text{Response})|}$$
  - $\text{Ratio} \ge 0.60 \implies G_{\text{det}} = 1.0$
  - $0.35 \le \text{Ratio} < 0.60 \implies G_{\text{det}} = 0.60$
  - $\text{Ratio} < 0.35 \implies G_{\text{det}} = 0.20$
- **Fused Score:** $G = \min(G_{\text{det}}, G_{\text{llm}})$

### 2. Factual Correctness ($F$)
- **Purpose:** Ensures the agent's answer contains all mandatory facts and figures specified in the ground-truth benchmark.
- **Deterministic Check:** For each required fact in `expected_facts`, extracts content tokens and checks if at least 40% of tokens appear in the answer. Then computes fact coverage:
  $$\text{Fact Coverage} = \frac{\sum_{i=1}^M \mathbf{1}(\text{Fact}_i \text{ covered})}{M}$$
  - $\text{Coverage} \ge 0.80 \implies F_{\text{det}} = 1.0$
  - $0.40 \le \text{Coverage} < 0.80 \implies F_{\text{det}} = 0.50$
  - $\text{Coverage} < 0.40 \implies F_{\text{det}} = 0.0$
- **Fused Score:** $F = \min(F_{\text{det}}, F_{\text{llm}})$

### 3. Citation Accuracy ($C$)
- **Purpose:** Guarantees every claim is attributed to verified source documents with correct citation syntax.
- **Deterministic Check:** Searches for citation tags matching regex `r"\[Source:[^\]]+\]"`.
  - If no citations found $\implies C = 0.0$ (`citation_defect`).
  - If citations match all `expected_sources` $\implies C = 1.0$.
  - If partial sources cited $\implies C = 0.70$.
  - If cited sources do not match expected sources $\implies C = 0.25$.
- For refusal cases, $C$ defaults to $1.0$ because refusals do not require document citations.

### 4. Refusal Correctness ($R$)
- **Purpose:** Prevents over-refusal (refusing valid in-scope questions) and under-refusal (answering out-of-scope or missing topics).
- **Deterministic Check:** Inspects response text for standard refusal keywords (`cannot answer`, `outside my verified`, `not authorized`, `policy limitations`, `not supported`, `do not contain`).
  - If `expected_action == "refuse"`:
    - Standard refusal detected $\implies R = 1.0$.
    - Answer provided $\implies R = 0.0$ (`wrong_refusal`).
  - If `expected_action == "answer"`:
    - Standard refusal detected $\implies R = 0.0$ (`wrong_refusal`).
    - Answer provided $\implies R = 1.0$.

### 5. Relevance Score ($S$)
- **Purpose:** Measures directness and focus on the user's inquiry, penalizing off-topic tangents or non-responsive answers.
- **Evaluator:** Evaluated primarily by the semantic LLM judge based on alignment between the question intent and the answer core.

### 6. Output-Contract Compliance ($O$)
- **Purpose:** Validates formatting, length, and structured presentation constraints.
- **Deterministic Check:**
  - Length $< 10$ characters $\implies O = 0.0$.
  - Response contains raw JSON evaluator code dumps (````json`) $\implies O = 0.0$.
  - Conforms to clean Markdown presentation $\implies O = 1.0$.

---

## 3. The Six Discrete Outcome Classifications

ForgeAI avoids binary pass/fail ambiguity by classifying every evaluation result into one of six distinct outcome states via `classify_outcome()`:

| Outcome Classification | Definition & Trigger Criteria | Pass / Fail Status |
|---|---|---|
| `correct_with_evidence` | Expected answer provided; $F \ge 0.75$, $G \ge 0.70$, $C \ge 0.70$. | **PASS** |
| `correct_without_evidence` | Factual claims correct ($F \ge 0.75$), but ungrounded ($G < 0.70$) or missing citations ($C < 0.50$). | **FAIL** |
| `partially_correct` | Answer contains some required facts, but omits others ($0.35 \le F < 0.75$). | **FAIL** |
| `incorrect` | Factual claims conflict with ground-truth evidence or severe hallucination ($F < 0.35$). | **FAIL** |
| `correct_refusal` | Query was out-of-scope or missing from corpus; agent correctly refused ($R \ge 0.80$). | **PASS** |
| `incorrect_refusal` | Agent erroneously refused an in-scope, answerable question ($R < 0.80$ on answerable case). | **FAIL** |

**Final Case Pass Rule:**
$$\text{Passed} \iff \text{Outcome} \in \{\text{correct\_with\_evidence}, \text{correct\_refusal}\} \land O \ge 0.80$$

---

## 4. Bias Mitigation Protocols

### 1. Position Bias Mitigation
In pairwise LLM judging, models frequently prefer whichever candidate is presented first (Position A vs Position B). ForgeAI eliminates position bias completely by employing **reference-anchored point-wise evaluation**: each response is judged independently against the ground-truth evidence and expected facts without competing against other responses.

### 2. Verbosity Bias Mitigation
LLMs often equate length with quality, awarding high scores to verbose answers. ForgeAI neutralizes verbosity bias through its deterministic lexical grounding ratio:
$$\text{Grounding Ratio} = \frac{|\text{Content Tokens in Context}|}{|\text{Total Content Tokens in Response}|}$$
If an agent pads its response with ungrounded verbose fluff, the denominator grows while the numerator remains bounded by retrieved context, depressing the grounding score below $0.60$ and triggering a hallucination failure.

### 3. Self-Preference Mitigation
LLMs exhibit stylistic favoritism toward outputs generated by the same model architecture. ForgeAI isolates the judge prompt (`app/prompts/judge.txt`) from the agent's generative instructions, mandating that the judge focus exclusively on explicit lexical evidence matching and semantic fact coverage.

### 4. Abstention & Uncertainty Scoring
When retrieved context is ambiguous or borderline, the judge sets `uncertainty_flag = True` and records `verdict_confidence < 1.0` in the evaluation output, signaling to the Critic-Optimizer that failure diagnosis must focus on retrieval recall rather than prompt recalibration.

---

## 5. Standardized Metric Aggregation Formulas

For an evaluation set of $N$ test cases:

1. **Overall Pass Rate:**
   $$\text{Pass Rate} = \frac{\sum_{i=1}^N \mathbf{1}(\text{Passed}_i)}{N}$$
2. **Grounded Answer Rate:**
   $$\text{Grounded Answer Rate} = \frac{\sum_{i \in \text{Answerable}} G_i}{|\text{Answerable}|}$$
3. **Factual Correctness Rate:**
   $$\text{Factual Correctness} = \frac{\sum_{i \in \text{Answerable}} F_i}{|\text{Answerable}|}$$
4. **Correct Refusal Rate:**
   $$\text{Correct Refusal Rate} = \frac{\sum_{i \in \text{Refusal}} R_i}{|\text{Refusal}|}$$
5. **Citation Accuracy Rate:**
   $$\text{Citation Accuracy} = \frac{\sum_{i \in \text{Answerable}} C_i}{|\text{Answerable}|}$$
6. **Output-Contract Compliance Rate:**
   $$\text{Contract Compliance} = \frac{\sum_{i=1}^N O_i}{N}$$

---

## 6. Concrete Calculation Example (From Real Demonstration)

Consider test case `HR-001` from `demos/hr_assistant/artifacts/eval_set.json`:
- **Question:** "How many days of annual leave are full-time employees entitled to per calendar year?"
- **Expected Action:** `answer`
- **Expected Facts:** `["25 days of paid annual leave per calendar year", "Accrued on a pro-rata basis"]`
- **Expected Sources:** `["leave_policy.pdf"]`

**Agent Response:**
> Full-time employees are entitled to 25 days of paid annual leave per calendar year, accrued on a pro-rata monthly basis. [Source: leave_policy.pdf, Page: 1]

**Step-by-Step Score Calculation:**
1. **Refusal Check:** Expected action is `answer`. Response did not trigger refusal keywords. $\implies R = 1.0$.
2. **Citation Check:** Found tag `[Source: leave_policy.pdf, Page: 1]`. Matches `leave_policy.pdf`. $\implies C = 1.0$.
3. **Fact Coverage Check:**
   - Fact 1: `25 days of paid annual leave per calendar year` $\rightarrow$ Tokens: `[days, paid, annual, leave, calendar, year]`. All 6 tokens present in response ($100\%$).
   - Fact 2: `Accrued on a pro-rata basis` $\rightarrow$ Tokens: `[accrued, pro-rata, basis]`. All 3 tokens present in response ($100\%$).
   - Total Fact Coverage: $2/2 = 1.0 \implies F_{\text{det}} = 1.0$.
4. **Grounding Check:**
   - Retrieved chunk contains: `"Full-time employees receive 25 days of paid annual leave per calendar year accrued pro-rata monthly."`
   - Response tokens match context tokens at $94\% \ge 60\% \implies G_{\text{det}} = 1.0$.
5. **Contract Check:** Response length is 142 characters, clean Markdown, no raw code dumps $\implies O = 1.0$.
6. **Outcome Classification:** $F=1.0, G=1.0, C=1.0 \implies \mathbf{correct\_with\_evidence}$.
7. **Verdict:** **PASSED**.
