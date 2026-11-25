import os
import json
import copy
from typing import Optional, List, Dict, Any, Tuple
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.agent_definition import AgentDefinition
from app.schemas.scorecard import IterationScorecard, IterationLog, CaseEvaluationResult
from app.schemas.evaluation import EvalSet
from app.factory.judge import HybridJudge
from app.runtime.chat_runner import GenericChatRunner

class CriticOptimizer:
    """Module 6: Critic-Optimizer Loop - Autonomous targeted optimization up to 3 iterations."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None, max_iterations: int = 3):
        self.llm = llm_client or get_llm_client()
        self.max_iterations = max_iterations

    def classify_failures(self, failed_cases: List[CaseEvaluationResult]) -> Dict[str, List[str]]:
        """Map failed test cases to one of the 6 root failure categories."""
        classifications: Dict[str, List[str]] = {
            "retrieval_miss": [],
            "prompt_defect": [],
            "hallucination": [],
            "wrong_refusal": [],
            "citation_defect": [],
            "output_contract_violation": []
        }

        for case in failed_cases:
            tid = case.test_id
            reasons_text = " ".join(case.failure_reasons).lower()

            if "refusal" in reasons_text or case.refusal_correctness < 0.8:
                classifications["wrong_refusal"].append(tid)
            elif "citation" in reasons_text or case.citation_correctness < 0.5:
                classifications["citation_defect"].append(tid)
            elif "retrieval" in reasons_text or not case.retrieved_sources:
                classifications["retrieval_miss"].append(tid)
            elif "hallucination" in reasons_text or case.grounding_score < 0.7:
                classifications["hallucination"].append(tid)
            elif "contract" in reasons_text or case.output_contract_compliance < 0.8:
                classifications["output_contract_violation"].append(tid)
            else:
                classifications["prompt_defect"].append(tid)

        return classifications

    def apply_targeted_optimizations(
        self,
        current_agent: AgentDefinition,
        classifications: Dict[str, List[str]],
        iteration: int
    ) -> Tuple[AgentDefinition, List[Dict[str, Any]], str]:
        """Apply targeted, incremental modifications without regenerating the whole agent."""
        updated = current_agent.model_copy(deep=True)
        changes_applied: List[Dict[str, Any]] = []
        root_causes = []

        # 1. Handle Retrieval Misses
        if classifications.get("retrieval_miss"):
            prev_k = updated.top_k
            new_k = min(prev_k + 1, 8)
            updated.top_k = new_k
            changes_applied.append({
                "target": "top_k",
                "previous_value": prev_k,
                "new_value": new_k,
                "reason": f"Broaden retrieval context for missed tests: {classifications['retrieval_miss']}"
            })
            root_causes.append("Retrieval coverage insufficient for multi-chunk reasoning.")

            if updated.similarity_threshold > 0.25:
                prev_thresh = updated.similarity_threshold
                new_thresh = round(prev_thresh - 0.05, 2)
                updated.similarity_threshold = new_thresh
                changes_applied.append({
                    "target": "similarity_threshold",
                    "previous_value": prev_thresh,
                    "new_value": new_thresh,
                    "reason": "Lower similarity barrier to admit borderline relevant paragraphs."
                })

        # 2. Handle Citation Defects
        if classifications.get("citation_defect"):
            prev_prompt = updated.system_prompt
            citation_instruction = (
                "\nMANDATORY CITATION RULE: Every statement of fact MUST end with an explicit citation tag "
                "in the format [Source: <document_name>]. If multiple documents apply, list each source tag."
            )
            if citation_instruction not in updated.system_prompt:
                updated.system_prompt += citation_instruction
                changes_applied.append({
                    "target": "system_prompt (citation clause)",
                    "previous_value": "standard prompt",
                    "new_value": "appended strict citation tag directive",
                    "reason": f"Remediate citation omissions for tests: {classifications['citation_defect']}"
                })
                root_causes.append("Citation instructions lacked explicit punctuation and tagging rules.")

        # 3. Handle Wrong Refusals
        if classifications.get("wrong_refusal"):
            refusal_clause = (
                "\nREFUSAL BOUNDARY RULE: Only refuse questions that clearly fall outside the supported documentation scope. "
                "For supported topics, search the context thoroughly and synthesize the answer before concluding refusal."
            )
            if refusal_clause not in updated.system_prompt:
                updated.system_prompt += refusal_clause
                changes_applied.append({
                    "target": "system_prompt (refusal boundary clause)",
                    "previous_value": "standard refusal policy",
                    "new_value": "clarified refusal criteria and required evidence synthesis",
                    "reason": f"Fix over-refusal / under-refusal on tests: {classifications['wrong_refusal']}"
                })
                root_causes.append("Refusal boundary ambiguity caused misclassified inquiries.")

        # 4. Handle Hallucinations
        if classifications.get("hallucination"):
            hallucination_clause = (
                "\nSTRICT GROUNDING CONSTRAINT: Never guess, extrapolate, or assume numbers or dates not explicitly written in the text. "
                "If a specific figure is missing from context, state that it is not documented."
            )
            if hallucination_clause not in updated.system_prompt:
                updated.system_prompt += hallucination_clause
                changes_applied.append({
                    "target": "system_prompt (grounding constraint)",
                    "previous_value": "standard grounding",
                    "new_value": "added explicit prohibition against extrapolating figures",
                    "reason": f"Prevent unsupported factual claims in tests: {classifications['hallucination']}"
                })
                root_causes.append("Model extrapolated unsupported details when context was partial.")

        # 5. Handle Contract Violations
        if classifications.get("output_contract_violation"):
            updated.output_contract.format = "markdown"
            changes_applied.append({
                "target": "output_contract.format",
                "previous_value": "unstructured",
                "new_value": "markdown with clear headings and bullet points",
                "reason": "Ensure output contract conformance."
            })
            root_causes.append("Output formatting violated contract specifications.")

        # If no specific rule triggered but tests failed, tweak prompt clarity
        if not changes_applied and classifications.get("prompt_defect"):
            updated.system_prompt += "\nClarity Directive: Structure all responses concisely with direct answers first, followed by supporting citations."
            changes_applied.append({
                "target": "system_prompt (structure clause)",
                "previous_value": "original prompt",
                "new_value": "added concise answer-first structure directive",
                "reason": "Improve answer directness and relevance."
            })
            root_causes.append("Answer structure lacked directness.")

        root_cause_summary = "; ".join(root_causes) if root_causes else "Minor prompt instruction tuning."
        return updated, changes_applied, root_cause_summary

    def run_optimization_loop(
        self,
        initial_agent: AgentDefinition,
        eval_set: EvalSet,
        doc_folder: str,
        artifacts_dir: str,
        target_pass_rate: float = 0.90
    ) -> Tuple[AgentDefinition, List[IterationScorecard], List[IterationLog]]:
        """Run iterative evaluation and targeted optimization up to max_iterations."""
        scorecards: List[IterationScorecard] = []
        iteration_logs: List[IterationLog] = []
        judge = HybridJudge(self.llm)

        current_agent = initial_agent.model_copy(deep=True)
        agent_def_path = os.path.join(artifacts_dir, "agent_definition.json")

        for iteration in range(1, self.max_iterations + 1):
            # Save current agent definition for runner to load
            os.makedirs(artifacts_dir, exist_ok=True)
            with open(agent_def_path, "w", encoding="utf-8") as f:
                f.write(current_agent.model_dump_json(indent=2, by_alias=True))

            # Initialize generic runner
            runner = GenericChatRunner(
                definition_path=agent_def_path,
                doc_folder=doc_folder,
                llm_client=self.llm
            )

            # Evaluate full test set
            scorecard = judge.evaluate_eval_set(eval_set, runner, iteration=iteration)
            scorecards.append(scorecard)

            current_score = scorecard.pass_rate
            failed_cases = [r for r in scorecard.case_results if not r.passed]

            # Check termination conditions
            if current_score >= target_pass_rate or not failed_cases:
                # Early stop on target achievement
                break

            if iteration >= self.max_iterations:
                # Reached max iterations
                break

            # Early stop if performance stagnates with identical failure profile
            if iteration > 1 and len(scorecards) >= 2:
                prev_failed_ids = [c.test_id for c in scorecards[-2].case_results if not c.passed]
                if set(failed_ids) == set(prev_failed_ids) and current_score <= scorecards[-2].pass_rate:
                    break

            # Classify failures
            classifications = self.classify_failures(failed_cases)
            failed_ids = [c.test_id for c in failed_cases]
            failure_categories = [cat for cat, ids in classifications.items() if ids]

            # Apply targeted optimizations
            optimized_agent, changes, root_cause_summary = self.apply_targeted_optimizations(
                current_agent=current_agent,
                classifications=classifications,
                iteration=iteration
            )

            # Check if any changes were made
            if not changes:
                # Early stop: No further useful changes
                break

            # Log iteration
            log = IterationLog(
                iteration_number=iteration,
                previous_score=current_score,
                failed_test_ids=failed_ids,
                failure_categories=failure_categories,
                identified_root_causes=root_cause_summary,
                changes_applied=changes,
                reason_for_each_change="Targeted adjustments to resolve identified failure modes without full regeneration.",
                updated_configuration={
                    "top_k": optimized_agent.top_k,
                    "similarity_threshold": optimized_agent.similarity_threshold,
                    "chunk_size": optimized_agent.chunk_size,
                    "chunk_overlap": optimized_agent.chunk_overlap
                },
                new_score=0.0,  # Will be updated after next iteration
                improvement_or_regression="PENDING"
            )
            iteration_logs.append(log)

            # Update current agent for next iteration
            current_agent = optimized_agent

        # Post-process iteration logs with subsequent scores
        for idx, log in enumerate(iteration_logs):
            if idx + 1 < len(scorecards):
                next_score = scorecards[idx + 1].pass_rate
                log.new_score = next_score
                if next_score > log.previous_score:
                    log.improvement_or_regression = f"IMPROVED (+{round((next_score - log.previous_score) * 100, 1)}%)"
                elif next_score == log.previous_score:
                    log.improvement_or_regression = "UNCHANGED"
                else:
                    log.improvement_or_regression = f"REGRESSED ({round((next_score - log.previous_score) * 100, 1)}%)"
            else:
                log.new_score = scorecards[-1].pass_rate
                log.improvement_or_regression = "FINAL_ITERATION"

        # Final save of the best agent definition
        with open(agent_def_path, "w", encoding="utf-8") as f:
            f.write(current_agent.model_dump_json(indent=2, by_alias=True))

        return current_agent, scorecards, iteration_logs
