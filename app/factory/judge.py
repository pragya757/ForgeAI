import os
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.evaluation import EvalCase, EvalSet
from app.schemas.scorecard import CaseEvaluationResult, IterationScorecard
from app.runtime.chat_runner import ChatResponse

class HybridJudge:
    """Module 5: Automated Judge - Robust hybrid deterministic + LLM evaluation architecture."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def check_deterministic_refusal(self, case: EvalCase, resp_text: str, refused_flag: bool) -> Tuple[float, List[str]]:
        """Evaluate refusal expectations deterministically."""
        refusal_keywords = [
            "cannot answer", "outside my verified", "not authorized",
            "refuse", "outside the scope", "policy limitations",
            "outside verified", "not supported", "is absent from the uploaded",
            "do not contain", "cannot execute", "strictly refused"
        ]
        is_refusal = any(kw in resp_text.lower() for kw in refusal_keywords) or refused_flag
        failures = []

        if case.expected_action == "refuse":
            if is_refusal:
                return 1.0, []
            else:
                failures.append("wrong_refusal: Expected refusal for out-of-scope question, but agent provided an answer.")
                return 0.0, failures
        else:
            if is_refusal:
                failures.append("wrong_refusal: Agent refused an answerable in-scope question.")
                return 0.0, failures
            else:
                return 1.0, []

    def check_deterministic_citations(self, case: EvalCase, resp_text: str) -> Tuple[float, List[str]]:
        """Evaluate citation existence and source document references deterministically."""
        if case.expected_action == "refuse":
            return 1.0, []

        citation_tags = re.findall(r"\[Source:[^\]]+\]", resp_text, re.IGNORECASE)
        failures = []

        if not citation_tags:
            failures.append("citation_defect: Response omitted mandatory citation tag [Source: <filename>].")
            return 0.0, failures

        if case.expected_sources:
            found_sources = []
            for src in case.expected_sources:
                src_base = os.path.basename(src).lower()
                matched = any(src_base in tag.lower() for tag in citation_tags)
                if matched:
                    found_sources.append(src)

            if len(found_sources) == len(case.expected_sources):
                return 1.0, []
            elif len(found_sources) > 0:
                failures.append(f"citation_defect: Partially cited sources. Missing citations for: {set(case.expected_sources) - set(found_sources)}")
                return 0.70, failures
            else:
                failures.append(f"citation_defect: Cited sources {citation_tags} do not match expected sources {case.expected_sources}.")
                return 0.25, failures

        return 1.0, []

    def check_deterministic_facts(self, case: EvalCase, resp_text: str) -> Tuple[float, List[str]]:
        """Evaluate required facts deterministically via lexical and numerical matching."""
        if case.expected_action == "refuse":
            return 1.0, []

        facts_to_check = case.expected_facts if case.expected_facts else [case.expected_answer]
        resp_lower = resp_text.lower()
        failures = []

        matched_facts = 0
        for fact in facts_to_check:
            # Check numerical accuracy if expected fact contains numbers
            expected_numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", fact)
            if expected_numbers:
                resp_numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", resp_lower)
                matching_num = any(num.lower() in resp_lower or num.rstrip("%") in resp_lower for num in expected_numbers)
                if not matching_num and resp_numbers:
                    failures.append(f"hallucination: Expected numerical fact {expected_numbers} contradicted or missing in response.")
                    continue

            # Extract content words (>= 3 chars, non-stopwords)
            tokens = [w for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", fact.lower())
                      if w not in {"must", "state", "that", "this", "from", "with", "should", "will", "according", "the", "and", "for", "are"}]
            if not tokens:
                matched_facts += 1
                continue
            matches = sum(1 for tok in tokens if tok in resp_lower or (len(tok) >= 5 and any(part in resp_lower for part in [tok[:4], tok[:5]])))
            if (matches / len(tokens)) >= 0.40:
                matched_facts += 1

        coverage = matched_facts / max(1, len(facts_to_check))
        if coverage >= 0.80:
            return 1.0, failures
        elif coverage >= 0.40:
            failures.append("hallucination: Response omitted some mandatory expected facts.")
            return 0.50, failures
        else:
            failures.append("hallucination: Response failed to contain the required ground-truth facts.")
            return 0.0, failures

    def check_deterministic_grounding(self, case: EvalCase, resp_text: str, retrieved_chunks_text: str) -> Tuple[float, List[str]]:
        """Evaluate whether response claims are substantiated by retrieved context chunks and ground truth evidence."""
        if case.expected_action == "refuse":
            return 1.0, []

        if not retrieved_chunks_text or not retrieved_chunks_text.strip():
            return 0.0, ["retrieval_miss: No document chunks were retrieved for the question."]

        # Clean response of citation boilerplate
        clean_resp = re.sub(r"\[Source:[^\]]+\]", "", resp_text, flags=re.IGNORECASE)
        stopwords = {
            "according", "verified", "documentation", "state", "states", "that", "this",
            "answer", "the", "and", "for", "with", "all", "your", "our", "you", "their",
            "from", "each", "both", "have", "been", "also", "into", "than", "then"
        }
        resp_tokens = [w for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", clean_resp.lower()) if w not in stopwords]

        if not resp_tokens:
            return 1.0, []

        context_lower = (
            retrieved_chunks_text.lower()
            + " " + case.question.lower()
            + " " + (case.ground_truth_evidence or "").lower()
            + " " + (case.expected_answer or "").lower()
        )
        context_words = set(context_lower.split())
        grounded_count = 0
        for tok in resp_tokens:
            # Direct match, morphological normalization, or bidirectional root matching
            if (
                tok in context_lower
                or tok.rstrip("s") in context_lower
                or tok.rstrip("th") in context_lower
                or tok.rstrip("ed") in context_lower
                or tok.rstrip("ing") in context_lower
                or any(w in tok for w in context_words if len(w) >= 5)
                or any(tok in w for w in context_words if len(tok) >= 5)
            ):
                grounded_count += 1

        grounded_ratio = grounded_count / len(resp_tokens)

        if grounded_ratio >= 0.50:
            return 1.0, []
        elif grounded_ratio >= 0.25:
            return 0.60, ["hallucination: Response contains assertions partially ungrounded in retrieved context."]
        else:
            return 0.20, ["hallucination: Response assertions cannot be substantiated by retrieved context."]

    def check_deterministic_contract(self, case: EvalCase, resp_text: str) -> Tuple[float, List[str]]:
        """Evaluate structured output validation deterministically."""
        failures = []
        if len(resp_text.strip()) < 10:
            failures.append("output_contract_violation: Response is empty or too short.")
            return 0.0, failures

        # Check for unescaped code blocks or raw JSON error dumps
        if resp_text.strip().startswith("```json") and "cases" in resp_text:
            failures.append("output_contract_violation: Agent returned raw evaluator JSON instead of user answer.")
            return 0.0, failures

        return 1.0, []

    def classify_outcome(
        self,
        case: EvalCase,
        factual_score: float,
        grounding_score: float,
        citation_score: float,
        refusal_score: float
    ) -> str:
        """Classify evaluation outcome into one of 6 distinct categories."""
        if case.expected_action == "refuse":
            return "correct_refusal" if refusal_score >= 0.8 else "incorrect_refusal"
        else:
            if refusal_score < 0.8:
                return "incorrect_refusal"  # Erroneously refused an answerable question
            if factual_score >= 0.75 and grounding_score >= 0.70 and citation_score >= 0.70:
                return "correct_with_evidence"
            elif factual_score >= 0.75 and (grounding_score < 0.70 or citation_score < 0.50):
                return "correct_without_evidence"
            elif 0.35 <= factual_score < 0.75:
                return "partially_correct"
            else:
                return "incorrect"

    def evaluate_case(
        self,
        case: EvalCase,
        agent_response: ChatResponse,
        retrieved_chunks_text: str = ""
    ) -> CaseEvaluationResult:
        """Run hybrid evaluation architecture (deterministic checks + semantic LLM judge)."""
        failures: List[str] = []
        resp_text = agent_response.answer.strip()

        # 1. Deterministic Checks
        refusal_score, ref_fails = self.check_deterministic_refusal(case, resp_text, agent_response.refused)
        failures.extend(ref_fails)

        citation_score, cit_fails = self.check_deterministic_citations(case, resp_text)
        failures.extend(cit_fails)

        det_fact_score, fact_fails = self.check_deterministic_facts(case, resp_text)
        failures.extend(fact_fails)

        det_grounding_score, ground_fails = self.check_deterministic_grounding(case, resp_text, retrieved_chunks_text)
        failures.extend(ground_fails)

        contract_score, contract_fails = self.check_deterministic_contract(case, resp_text)
        failures.extend(contract_fails)

        # 2. Semantic LLM Judge (Completeness, Semantic Accuracy, Relevance, Bias Mitigations)
        evidence_reasoning = "Deterministic evaluation applied."
        verdict_confidence = 1.0
        uncertainty_flag = False
        explanation = "Automated hybrid evaluation complete."

        if case.expected_action == "refuse":
            if refusal_score >= 0.8:
                llm_grounding = 1.0
                llm_factual = 1.0
                llm_relevance = 1.0
                evidence_reasoning = "Refusal correctly executed for out-of-scope question."
            else:
                llm_grounding = 0.0
                llm_factual = 0.0
                llm_relevance = 0.0
                evidence_reasoning = "Agent provided answer when refusal was required."
        else:
            # Query LLM Judge for semantic comparison
            prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "judge.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()

            judge_prompt = template.format(
                test_case_json=case.model_dump_json(indent=2),
                agent_response=resp_text,
                retrieved_chunks=retrieved_chunks_text[:1200] if retrieved_chunks_text else "None"
            )

            judge_output = self.llm.generate(
                prompt=judge_prompt,
                json_mode=True,
                temperature=0.0
            )

            try:
                clean_json = judge_output.strip()
                if clean_json.startswith("```json"): clean_json = clean_json[7:]
                if clean_json.startswith("```"): clean_json = clean_json[3:]
                if clean_json.endswith("```"): clean_json = clean_json[:-3]
                judge_data = json.loads(clean_json.strip())

                llm_grounding = float(judge_data.get("grounding_score", 1.0))
                llm_factual = float(judge_data.get("factual_correctness", 1.0))
                llm_relevance = float(judge_data.get("relevance_score", 1.0))
                verdict_confidence = float(judge_data.get("verdict_confidence", 1.0))
                uncertainty_flag = bool(judge_data.get("uncertainty_flag", False))
                evidence_reasoning = judge_data.get("evidence_reasoning", "Evidence analyzed.")
                explanation = judge_data.get("explanation", "Judge evaluated response.")

                for f in judge_data.get("failure_reasons", []):
                    if f not in failures:
                        failures.append(f)
            except Exception:
                llm_grounding = det_grounding_score
                llm_factual = det_fact_score
                llm_relevance = 1.0 if det_fact_score >= 0.5 else 0.5
                evidence_reasoning = "Fallback semantic evaluation."

        # 3. Hybrid Score Fusion
        # Factual correctness uses conservative minimum to prevent false passes when mandatory criteria are omitted
        final_factual = min(det_fact_score, llm_factual)

        # Grounding allows semantic LLM evaluation to substantiate claims when lexical overlap is reduced by paraphrasing
        if llm_grounding >= 0.8 and verdict_confidence >= 0.8 and det_grounding_score >= 0.20:
            final_grounding = max(det_grounding_score, 0.7 * llm_grounding + 0.3 * det_grounding_score)
            if final_grounding >= 0.70:
                failures = [f for f in failures if not f.startswith("hallucination: Response assertions cannot be substantiated")]
        else:
            final_grounding = min(det_grounding_score, llm_grounding)

        final_relevance = llm_relevance

        # 4. Outcome Classification
        outcome_classification = self.classify_outcome(
            case=case,
            factual_score=final_factual,
            grounding_score=final_grounding,
            citation_score=citation_score,
            refusal_score=refusal_score
        )

        # 5. Pass/Fail Decision
        passed = (
            outcome_classification in {"correct_with_evidence", "correct_refusal"}
            and contract_score >= 0.8
        )

        if not passed and not failures:
            failures.append(f"Evaluation failed outcome threshold: classified as '{outcome_classification}'.")

        return CaseEvaluationResult(
            test_id=case.test_id,
            question=case.question,
            passed=passed,
            outcome_classification=outcome_classification,
            grounding_score=round(final_grounding, 2),
            factual_correctness=round(final_factual, 2),
            citation_correctness=round(citation_score, 2),
            refusal_correctness=round(refusal_score, 2),
            relevance_score=round(final_relevance, 2),
            output_contract_compliance=round(contract_score, 2),
            verdict_confidence=round(verdict_confidence, 2),
            uncertainty_flag=uncertainty_flag,
            evidence_reasoning=evidence_reasoning,
            failure_reasons=failures,
            agent_response=resp_text,
            retrieved_sources=agent_response.sources,
            tool_calls=agent_response.tool_calls,
            explanation=explanation
        )

    def evaluate_eval_set(
        self,
        eval_set: EvalSet,
        agent_runner: Any,
        iteration: int = 1
    ) -> IterationScorecard:
        """Run full evaluation suite across all cases and produce scorecard with metric and outcome distributions."""
        results: List[CaseEvaluationResult] = []
        failure_dist: Dict[str, int] = {
            "retrieval_miss": 0,
            "prompt_defect": 0,
            "hallucination": 0,
            "wrong_refusal": 0,
            "citation_defect": 0,
            "output_contract_violation": 0
        }
        outcome_dist: Dict[str, int] = {
            "correct_with_evidence": 0,
            "correct_without_evidence": 0,
            "partially_correct": 0,
            "incorrect": 0,
            "correct_refusal": 0,
            "incorrect_refusal": 0
        }

        for case in eval_set.cases:
            response = agent_runner.ask(case.question)
            retrieved_chunks = agent_runner.retriever.retrieve(case.question)
            retrieved_text = "\n".join([f"[{c.source}] {c.content}" for c in retrieved_chunks])

            case_res = self.evaluate_case(case, response, retrieved_text)
            results.append(case_res)

            # Tally outcomes
            if case_res.outcome_classification in outcome_dist:
                outcome_dist[case_res.outcome_classification] += 1

            # Tally failures
            for f in case_res.failure_reasons:
                for cat in failure_dist.keys():
                    if cat in f.lower():
                        failure_dist[cat] += 1

        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = round(passed_count / max(1, total), 4)

        avg_grounding = round(sum(r.grounding_score for r in results) / max(1, total), 3)
        avg_factual = round(sum(r.factual_correctness for r in results) / max(1, total), 3)
        avg_citation = round(sum(r.citation_correctness for r in results) / max(1, total), 3)
        avg_refusal = round(sum(r.refusal_correctness for r in results) / max(1, total), 3)
        avg_relevance = round(sum(r.relevance_score for r in results) / max(1, total), 3)
        avg_contract = round(sum(r.output_contract_compliance for r in results) / max(1, total), 3)

        status = "PASS" if pass_rate >= 0.85 else ("NEEDS_OPTIMIZATION" if pass_rate >= 0.60 else "FAIL")

        return IterationScorecard(
            iteration=iteration,
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed_count,
            pass_rate=pass_rate,
            metric_breakdown={
                "grounding": avg_grounding,
                "factual_correctness": avg_factual,
                "citation_correctness": avg_citation,
                "refusal_correctness": avg_refusal,
                "relevance": avg_relevance,
                "output_contract_compliance": avg_contract
            },
            failure_distribution=failure_dist,
            outcome_distribution=outcome_dist,
            status=status,
            case_results=results
        )
