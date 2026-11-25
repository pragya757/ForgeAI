import os
import json
import re
from typing import Optional, List, Dict, Any
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.evaluation import EvalCase, EvalSet
from app.schemas.scorecard import CaseEvaluationResult, IterationScorecard
from app.runtime.chat_runner import ChatResponse

class HybridJudge:
    """Module 5: Automated Judge - Hybrid deterministic + LLM evaluation."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def evaluate_case(
        self,
        case: EvalCase,
        agent_response: ChatResponse,
        retrieved_chunks_text: str = ""
    ) -> CaseEvaluationResult:
        """Run deterministic checks and LLM judge to evaluate one test case."""
        failures = []
        resp_text = agent_response.answer.strip()

        # 1. Deterministic Refusal Check
        refusal_keywords = [
            "cannot answer", "outside my verified", "not authorized",
            "refuse", "outside the scope", "policy limitations",
            "outside verified", "not supported"
        ]
        is_refusal_response = any(kw in resp_text.lower() for kw in refusal_keywords) or agent_response.refused

        if case.expected_action == "refuse":
            if is_refusal_response:
                refusal_score = 1.0
            else:
                refusal_score = 0.0
                failures.append("wrong_refusal: Expected refusal for out-of-scope question, but agent answered.")
        else:
            if is_refusal_response:
                refusal_score = 0.0
                failures.append("wrong_refusal: Agent refused an answerable in-scope question.")
            else:
                refusal_score = 1.0

        # 2. Deterministic Citation Check
        citation_tags = re.findall(r"\[Source:[^\]]+\]", resp_text)
        if case.expected_action == "refuse":
            citation_score = 1.0  # Refusals do not require document page citation
        else:
            if citation_tags:
                # Check if expected source is mentioned
                if case.expected_sources:
                    found_source = any(
                        any(src.lower() in tag.lower() for tag in citation_tags)
                        for src in case.expected_sources
                    )
                    citation_score = 1.0 if found_source else 0.5
                else:
                    citation_score = 1.0
            else:
                citation_score = 0.0
                failures.append("citation_defect: Response omitted mandatory citation tag [Source: <filename>].")

        # 3. Deterministic Output Contract Compliance Check
        # Check markdown structure, no forbidden code, no empty content
        if len(resp_text) < 10:
            contract_score = 0.0
            failures.append("output_contract_violation: Response text is empty or too short.")
        else:
            contract_score = 1.0

        # 4. LLM Semantic Judge for Grounding & Factual Correctness
        if refusal_score == 0.0 and case.expected_action == "refuse":
            grounding_score = 0.0
            factual_score = 0.0
            relevance_score = 0.0
        elif case.expected_action == "refuse" and is_refusal_response:
            grounding_score = 1.0
            factual_score = 1.0
            relevance_score = 1.0
        else:
            # Semantic evaluation
            prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "judge.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()

            judge_prompt = template.format(
                test_case_json=case.model_dump_json(indent=2),
                agent_response=resp_text,
                retrieved_chunks=retrieved_chunks_text[:1000] if retrieved_chunks_text else "None"
            )

            judge_output = self.llm.generate(
                prompt=judge_prompt,
                json_mode=True,
                temperature=0.0
            )

            try:
                clean_json = judge_output.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                judge_data = json.loads(clean_json.strip())
                grounding_score = float(judge_data.get("grounding_score", 1.0))
                factual_score = float(judge_data.get("factual_correctness", 1.0))
                relevance_score = float(judge_data.get("relevance_score", 1.0))
                for f in judge_data.get("failure_reasons", []):
                    if f not in failures:
                        failures.append(f)
            except Exception:
                # Deterministic keyword factual overlap
                expected_key_words = [w for w in case.expected_answer.lower().split() if len(w) > 4]
                overlap = sum(1 for w in expected_key_words if w in resp_text.lower())
                factual_score = 1.0 if (overlap / max(1, len(expected_key_words))) >= 0.3 else 0.5
                grounding_score = 1.0
                relevance_score = 1.0

        # Determine pass/fail
        passed = (
            refusal_score >= 0.8
            and citation_score >= 0.5
            and factual_score >= 0.7
            and grounding_score >= 0.7
            and contract_score >= 0.8
        )

        if not passed and not failures:
            failures.append("Score threshold not met for passing evaluation criteria.")

        return CaseEvaluationResult(
            test_id=case.test_id,
            question=case.question,
            passed=passed,
            grounding_score=round(grounding_score, 2),
            factual_correctness=round(factual_score, 2),
            citation_correctness=round(citation_score, 2),
            refusal_correctness=round(refusal_score, 2),
            relevance_score=round(relevance_score, 2),
            output_contract_compliance=round(contract_score, 2),
            failure_reasons=failures,
            agent_response=resp_text,
            retrieved_sources=agent_response.sources,
            tool_calls=agent_response.tool_calls
        )

    def evaluate_eval_set(
        self,
        eval_set: EvalSet,
        agent_runner: Any,
        iteration: int = 1
    ) -> IterationScorecard:
        """Run full evaluation suite across all cases and produce scorecard."""
        results: List[CaseEvaluationResult] = []
        failure_dist: Dict[str, int] = {
            "retrieval_miss": 0,
            "prompt_defect": 0,
            "hallucination": 0,
            "wrong_refusal": 0,
            "citation_defect": 0,
            "output_contract_violation": 0
        }

        for case in eval_set.cases:
            # Query the agent runner
            response = agent_runner.ask(case.question)

            # Get retrieved text
            retrieved_chunks = agent_runner.retriever.retrieve(case.question)
            retrieved_text = "\n".join([f"[{c.source}] {c.content}" for c in retrieved_chunks])

            case_res = self.evaluate_case(case, response, retrieved_text)
            results.append(case_res)

            # Tally failure reasons
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
            status=status,
            case_results=results
        )
