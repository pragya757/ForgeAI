import os
import json
import copy
from typing import Optional, List, Dict, Any, Tuple, Set
from pydantic import BaseModel, Field

from app.llm import get_llm_client, BaseLLMClient
from app.schemas.agent_definition import AgentDefinition
from app.schemas.scorecard import IterationScorecard, IterationLog, CaseEvaluationResult
from app.schemas.evaluation import EvalSet
from app.factory.judge import HybridJudge
from app.runtime.chat_runner import GenericChatRunner

class FailureDiagnosis(BaseModel):
    """Structured diagnosis of a single test case failure."""
    test_id: str
    category: str  # One of: retrieval_miss, prompt_defect, hallucination, wrong_refusal, citation_defect, output_contract_violation
    root_cause: str
    relevant_config_field: str
    proposed_change: Dict[str, Any]
    affected_test_ids: List[str] = Field(default_factory=list)

class CriticOptimizer:
    """
    Module 6: Critic-Optimizer Loop
    Autonomous targeted failure diagnosis, repair proposal, validation, and rollback safeguards.
    Strictly capped at a maximum of 3 optimization iterations.
    """

    ALLOWED_TARGET_FIELDS = {
        "top_k",
        "similarity_threshold",
        "chunk_overlap",
        "chunk_size",
        "system_prompt",
        "output_contract",
        "citation_requirements",
        "refusal_policy"
    }

    def __init__(self, llm_client: Optional[BaseLLMClient] = None, max_iterations: int = 3):
        self.llm = llm_client or get_llm_client()
        # Strictly enforce maximum 3 iterations ceiling regardless of input
        self.max_iterations = min(max(int(max_iterations), 1), 3)
        self.original_agent: Optional[AgentDefinition] = None
        self.snapshot_paths: List[str] = []

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
            outcome = getattr(case, "outcome_classification", "").lower()

            # 1. Wrong Refusal Check
            if (
                "wrong_refusal" in reasons_text
                or outcome == "incorrect_refusal"
                or (case.refusal_correctness < 0.8 and ("refus" in reasons_text or "scope" in reasons_text))
            ):
                classifications["wrong_refusal"].append(tid)

            # 2. Citation Defect Check
            elif (
                "citation" in reasons_text
                or case.citation_correctness < 0.5
            ):
                classifications["citation_defect"].append(tid)

            # 3. Retrieval Miss Check
            elif (
                "retrieval" in reasons_text
                or not case.retrieved_sources
                or (case.grounding_score == 0.0 and "context" in reasons_text)
            ):
                classifications["retrieval_miss"].append(tid)

            # 4. Hallucination Check
            elif (
                "hallucination" in reasons_text
                or outcome == "correct_without_evidence"
                or (case.grounding_score < 0.7 and case.factual_correctness > 0.0)
            ):
                classifications["hallucination"].append(tid)

            # 5. Output Contract Violation Check
            elif (
                "contract" in reasons_text
                or case.output_contract_compliance < 0.8
            ):
                classifications["output_contract_violation"].append(tid)

            # 6. Prompt Defect (default semantic / structural shortfall)
            else:
                classifications["prompt_defect"].append(tid)

        return classifications

    def diagnose_failures(self, failed_cases: List[CaseEvaluationResult]) -> List[FailureDiagnosis]:
        """
        Step 1 & 2: Identify failure category, root cause, relevant configuration,
        and propose targeted change for each failed evaluation.
        """
        diagnoses: List[FailureDiagnosis] = []
        classifications = self.classify_failures(failed_cases)

        for category, tids in classifications.items():
            if not tids:
                continue

            for tid in tids:
                matching_case = next((c for c in failed_cases if c.test_id == tid), None)
                reason_detail = "; ".join(matching_case.failure_reasons) if matching_case else "Evaluation criteria not met."

                if category == "retrieval_miss":
                    root_cause = f"Retrieval recall shortfall: source document chunks were not fetched or similarity barrier was too strict. ({reason_detail})"
                    config_field = "top_k, similarity_threshold"
                    proposed_change = {
                        "target": "top_k",
                        "field": "top_k",
                        "action": "increment",
                        "delta": 1,
                        "secondary_target": "similarity_threshold",
                        "secondary_delta": -0.05,
                        "reason": f"Broaden retrieval top_k and relax similarity threshold for missed test: {tid}"
                    }

                elif category == "citation_defect":
                    root_cause = f"Citation formatting defect: response omitted or malformed [Source: <filename>] tag. ({reason_detail})"
                    config_field = "system_prompt (citation directive)"
                    proposed_change = {
                        "target": "system_prompt",
                        "field": "system_prompt",
                        "clause_type": "citation_rule",
                        "content": (
                            "\nMANDATORY CITATION RULE: Every statement of fact MUST end with an explicit citation tag "
                            "in the format [Source: <document_name>]. If multiple documents apply, list each source tag."
                        ),
                        "reason": f"Remediate citation omissions for test: {tid}"
                    }

                elif category == "wrong_refusal":
                    root_cause = f"Refusal boundary ambiguity: agent either refused an in-scope question or answered an out-of-scope inquiry. ({reason_detail})"
                    config_field = "system_prompt (refusal policy)"
                    proposed_change = {
                        "target": "system_prompt",
                        "field": "system_prompt",
                        "clause_type": "refusal_rule",
                        "content": (
                            "\nREFUSAL BOUNDARY RULE: Only refuse questions that clearly fall outside the supported documentation scope. "
                            "For supported topics, search the context thoroughly and synthesize the answer before concluding refusal."
                        ),
                        "reason": f"Clarify refusal boundary criteria for test: {tid}"
                    }

                elif category == "hallucination":
                    root_cause = f"Grounding violation: agent extrapolated figures, dates, or assertions unsupported by retrieved text. ({reason_detail})"
                    config_field = "system_prompt (grounding constraint)"
                    proposed_change = {
                        "target": "system_prompt",
                        "field": "system_prompt",
                        "clause_type": "grounding_rule",
                        "content": (
                            "\nSTRICT GROUNDING CONSTRAINT: Never guess, extrapolate, or assume numbers or dates not explicitly written in the text. "
                            "If a specific figure is missing from context, state that it is not documented."
                        ),
                        "reason": f"Enforce strict non-extrapolation grounding rule for test: {tid}"
                    }

                elif category == "output_contract_violation":
                    root_cause = f"Output contract compliance defect: format deviated from structured Markdown or required headings. ({reason_detail})"
                    config_field = "output_contract.format"
                    proposed_change = {
                        "target": "output_contract.format",
                        "field": "output_contract.format",
                        "new_value": "markdown",
                        "reason": f"Enforce markdown output contract for test: {tid}"
                    }

                else:  # prompt_defect
                    root_cause = f"Prompt clarity defect: response lacked directness, structured synthesis, or concise organization. ({reason_detail})"
                    config_field = "system_prompt (structure directive)"
                    proposed_change = {
                        "target": "system_prompt",
                        "field": "system_prompt",
                        "clause_type": "structure_directive",
                        "content": "\nCLARITY DIRECTIVE: Structure all responses concisely with direct answers first, followed by supporting citations.",
                        "reason": f"Enhance prompt directness and structure for test: {tid}"
                    }

                diagnoses.append(FailureDiagnosis(
                    test_id=tid,
                    category=category,
                    root_cause=root_cause,
                    relevant_config_field=config_field,
                    proposed_change=proposed_change,
                    affected_test_ids=[tid]
                ))

        return diagnoses

    def validate_repair(self, proposed_change: Dict[str, Any], current_agent: AgentDefinition) -> bool:
        """
        Step 5: Validate that proposed change addresses the diagnosed failure,
        remains within safe parameter bounds, and does not touch unrelated components.
        """
        target = proposed_change.get("target") or proposed_change.get("field", "")
        base_field = target.split(".")[0].split(" ")[0]

        # 1. Target must be in allowed list of optimizable configuration fields
        if base_field not in self.ALLOWED_TARGET_FIELDS:
            return False

        # 2. Validate bounds for numeric parameters
        if base_field == "top_k":
            delta = proposed_change.get("delta", 1)
            proposed_val = current_agent.top_k + delta
            if proposed_val < 1 or proposed_val > 12:
                return False

        if base_field == "similarity_threshold" or proposed_change.get("secondary_target") == "similarity_threshold":
            delta = proposed_change.get("secondary_delta", -0.05)
            proposed_val = current_agent.similarity_threshold + delta
            if proposed_val < 0.10 or proposed_val > 0.90:
                return False

        # 3. Validate text insertions
        if base_field == "system_prompt":
            content = proposed_change.get("content", "")
            if not content or not isinstance(content, str):
                return False

        return True

    def apply_targeted_optimizations(
        self,
        current_agent: AgentDefinition,
        classifications: Dict[str, List[str]],
        iteration: int
    ) -> Tuple[AgentDefinition, List[Dict[str, Any]], str]:
        """
        Step 4, 5, 6: Propose, validate, and apply targeted incremental modifications.
        Never regenerates the entire agent; preserves all untargeted fields.
        """
        updated = current_agent.model_copy(deep=True)
        changes_applied: List[Dict[str, Any]] = []
        root_causes: List[str] = []

        # 1. Handle Retrieval Misses (locate: top_k, similarity_threshold)
        if classifications.get("retrieval_miss"):
            prev_k = updated.top_k
            new_k = min(prev_k + 1, 8)
            change_k = {
                "target": "top_k",
                "field": "top_k",
                "previous_value": prev_k,
                "new_value": new_k,
                "delta": 1,
                "reason": f"Broaden retrieval top_k for missed tests: {classifications['retrieval_miss']}",
                "affected_tests": classifications["retrieval_miss"]
            }
            if self.validate_repair(change_k, current_agent):
                updated.top_k = new_k
                changes_applied.append(change_k)
                root_causes.append(f"Retrieval coverage insufficient for tests {classifications['retrieval_miss']}")

            if updated.similarity_threshold > 0.25:
                prev_thresh = updated.similarity_threshold
                new_thresh = round(prev_thresh - 0.05, 2)
                change_thresh = {
                    "target": "similarity_threshold",
                    "field": "similarity_threshold",
                    "previous_value": prev_thresh,
                    "new_value": new_thresh,
                    "reason": "Lower similarity threshold to admit borderline relevant chunks.",
                    "affected_tests": classifications["retrieval_miss"]
                }
                if self.validate_repair(change_thresh, current_agent):
                    updated.similarity_threshold = new_thresh
                    changes_applied.append(change_thresh)

        # 2. Handle Citation Defects (locate: system_prompt citation clause)
        if classifications.get("citation_defect"):
            citation_clause_1 = (
                "\nMANDATORY CITATION RULE: Every statement of fact MUST end with an explicit citation tag "
                "in the format [Source: <document_name>]. If multiple documents apply, list each source tag."
            )
            citation_clause_2 = (
                "\nSTRICT CITATION ENFORCEMENT: Citations must appear inline immediately following each factual statement. "
                "Do not group citations only at the end of the response."
            )
            clause_to_add = citation_clause_1 if citation_clause_1 not in updated.system_prompt else (
                citation_clause_2 if citation_clause_2 not in updated.system_prompt else ""
            )
            if clause_to_add:
                change_cite = {
                    "target": "system_prompt (citation clause)",
                    "field": "system_prompt",
                    "content": clause_to_add,
                    "previous_value": "standard prompt" if clause_to_add == citation_clause_1 else "level 1 citation rule",
                    "new_value": "appended strict citation tag directive",
                    "reason": f"Remediate citation omissions for tests: {classifications['citation_defect']}",
                    "affected_tests": classifications["citation_defect"]
                }
                if self.validate_repair(change_cite, current_agent):
                    updated.system_prompt += clause_to_add
                    changes_applied.append(change_cite)
                    root_causes.append(f"Citation instructions lacked explicit punctuation and tagging rules for tests {classifications['citation_defect']}")

        # 3. Handle Wrong Refusals (locate: system_prompt refusal policy)
        if classifications.get("wrong_refusal"):
            refusal_clause_1 = (
                "\nREFUSAL BOUNDARY RULE: Only refuse questions that clearly fall outside the supported documentation scope. "
                "For supported topics, search the context thoroughly and synthesize the answer before concluding refusal."
            )
            refusal_clause_2 = (
                "\nREFUSAL VERIFICATION DIRECTIVE: Double-check all retrieved document excerpts before issuing a refusal. "
                "If relevant facts exist in context, synthesize the answer rather than refusing."
            )
            refusal_to_add = refusal_clause_1 if refusal_clause_1 not in updated.system_prompt else (
                refusal_clause_2 if refusal_clause_2 not in updated.system_prompt else ""
            )
            if refusal_to_add:
                change_refusal = {
                    "target": "system_prompt (refusal boundary clause)",
                    "field": "system_prompt",
                    "content": refusal_to_add,
                    "previous_value": "standard refusal policy" if refusal_to_add == refusal_clause_1 else "level 1 refusal rule",
                    "new_value": "clarified refusal criteria and required evidence synthesis",
                    "reason": f"Fix over-refusal / under-refusal on tests: {classifications['wrong_refusal']}",
                    "affected_tests": classifications["wrong_refusal"]
                }
                if self.validate_repair(change_refusal, current_agent):
                    updated.system_prompt += refusal_to_add
                    changes_applied.append(change_refusal)
                    root_causes.append(f"Refusal boundary ambiguity caused misclassified inquiries on tests {classifications['wrong_refusal']}")

        # 4. Handle Hallucinations (locate: system_prompt grounding constraint)
        if classifications.get("hallucination"):
            hallucination_clause_1 = (
                "\nSTRICT GROUNDING CONSTRAINT: Never guess, extrapolate, or assume numbers or dates not explicitly written in the text. "
                "If a specific figure is missing from context, state that it is not documented."
            )
            hallucination_clause_2 = (
                "\nZERO-TOLERANCE GROUNDING: If an exact answer cannot be quoted or directly derived from retrieved documents, "
                "state 'The documentation does not contain this information.' without speculation."
            )
            halluc_to_add = hallucination_clause_1 if hallucination_clause_1 not in updated.system_prompt else (
                hallucination_clause_2 if hallucination_clause_2 not in updated.system_prompt else ""
            )
            if halluc_to_add:
                change_halluc = {
                    "target": "system_prompt (grounding constraint)",
                    "field": "system_prompt",
                    "content": halluc_to_add,
                    "previous_value": "standard grounding" if halluc_to_add == hallucination_clause_1 else "level 1 grounding rule",
                    "new_value": "added explicit prohibition against extrapolating figures",
                    "reason": f"Prevent unsupported factual claims in tests: {classifications['hallucination']}",
                    "affected_tests": classifications["hallucination"]
                }
                if self.validate_repair(change_halluc, current_agent):
                    updated.system_prompt += halluc_to_add
                    changes_applied.append(change_halluc)
                    root_causes.append(f"Model extrapolated unsupported details when context was partial on tests {classifications['hallucination']}")

        # 5. Handle Contract Violations (locate: output_contract.format)
        if classifications.get("output_contract_violation"):
            change_contract = {
                "target": "output_contract.format",
                "field": "output_contract",
                "previous_value": updated.output_contract.format,
                "new_value": "markdown",
                "reason": f"Ensure output contract conformance for tests: {classifications['output_contract_violation']}",
                "affected_tests": classifications["output_contract_violation"]
            }
            if self.validate_repair(change_contract, current_agent):
                updated.output_contract.format = "markdown"
                changes_applied.append(change_contract)
                root_causes.append(f"Output formatting violated contract specifications on tests {classifications['output_contract_violation']}")

        # 6. Handle Prompt Defects (locate: system_prompt structure clause)
        if not changes_applied and classifications.get("prompt_defect"):
            structure_clause = "\nCLARITY DIRECTIVE: Structure all responses concisely with direct answers first, followed by supporting citations."
            change_prompt = {
                "target": "system_prompt (structure clause)",
                "field": "system_prompt",
                "content": structure_clause,
                "previous_value": "original prompt",
                "new_value": "added concise answer-first structure directive",
                "reason": f"Improve answer directness and relevance for tests: {classifications['prompt_defect']}",
                "affected_tests": classifications["prompt_defect"]
            }
            if self.validate_repair(change_prompt, current_agent) and structure_clause not in updated.system_prompt:
                updated.system_prompt += structure_clause
                changes_applied.append(change_prompt)
                root_causes.append(f"Answer structure lacked directness on tests {classifications['prompt_defect']}")

        # Safeguard check: Verify untouched core fields are preserved without mutation
        assert updated.agent_name == current_agent.agent_name, "Unrelated field agent_name mutated!"
        assert updated.target_audience == current_agent.target_audience, "Unrelated field target_audience mutated!"
        assert updated.supported_topics == current_agent.supported_topics, "Unrelated field supported_topics mutated!"
        assert updated.unsupported_topics == current_agent.unsupported_topics, "Unrelated field unsupported_topics mutated!"

        root_cause_summary = "; ".join(root_causes) if root_causes else "Minor prompt instruction tuning."
        return updated, changes_applied, root_cause_summary

    def save_snapshot(self, agent: AgentDefinition, filepath: str) -> str:
        """Save an immutable configuration snapshot."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(agent.model_dump_json(indent=2, by_alias=True))
        return filepath

    def run_optimization_loop(
        self,
        initial_agent: AgentDefinition,
        eval_set: EvalSet,
        doc_folder: str,
        artifacts_dir: str,
        target_pass_rate: float = 0.90
    ) -> Tuple[AgentDefinition, List[IterationScorecard], List[IterationLog]]:
        """
        Step 7: Rerun complete fixed evaluation set across optimization iterations (max 3).
        Enforces safeguards:
        - Strict ceiling: at most 3 iterations.
        - Preserves original configuration.
        - Saves configuration snapshots at every stage.
        - Never modifies unrelated components.
        - Tracks regressions in previously passing tests.
        - Rejects changes causing unacceptable regressions (rollback).
        - Early stopping on target achievement or convergence.
        - Comprehensive score comparison logging.
        """
        scorecards: List[IterationScorecard] = []
        iteration_logs: List[IterationLog] = []
        judge = HybridJudge(self.llm)

        os.makedirs(artifacts_dir, exist_ok=True)

        # Safeguard 1: Preserve original baseline configuration
        self.original_agent = initial_agent.model_copy(deep=True)
        initial_snapshot_path = os.path.join(artifacts_dir, "agent_definition_initial.json")
        self.save_snapshot(self.original_agent, initial_snapshot_path)
        self.snapshot_paths.append(initial_snapshot_path)

        # Active agent definition path loaded by GenericChatRunner
        active_agent_path = os.path.join(artifacts_dir, "agent_definition.json")

        current_agent = initial_agent.model_copy(deep=True)
        accepted_agent = current_agent.model_copy(deep=True)
        prev_passed_ids: Set[str] = set()

        iteration = 1
        # Safeguard 2: Strict ceiling of maximum 3 iterations
        while iteration <= self.max_iterations and iteration <= 3:
            # Save configuration snapshot for this iteration
            iter_snapshot_path = os.path.join(artifacts_dir, f"agent_definition_iter_{iteration}.json")
            self.save_snapshot(current_agent, iter_snapshot_path)
            self.snapshot_paths.append(iter_snapshot_path)

            # Also update active agent definition
            self.save_snapshot(current_agent, active_agent_path)

            # Initialize generic runner pointing to active agent definition
            runner = GenericChatRunner(
                definition_path=active_agent_path,
                doc_folder=doc_folder,
                llm_client=self.llm
            )

            # Step 7: Rerun complete fixed evaluation set
            scorecard = judge.evaluate_eval_set(eval_set, runner, iteration=iteration)
            scorecards.append(scorecard)

            current_score = scorecard.pass_rate
            curr_passed_ids = set(c.test_id for c in scorecard.case_results if c.passed)
            failed_cases = [r for r in scorecard.case_results if not r.passed]
            failed_ids = [c.test_id for c in failed_cases]

            # Safeguard 3: Regression tracking on previously passing tests
            if iteration > 1:
                regressed_ids = sorted(list(prev_passed_ids - curr_passed_ids))
                resolved_ids = sorted(list(curr_passed_ids - prev_passed_ids))
                prev_score = scorecards[iteration - 2].pass_rate
                score_diff = round(current_score - prev_score, 4)

                # Update the preceding iteration log with the actual rerun outcome
                if iteration_logs:
                    prev_log = iteration_logs[-1]
                    prev_log.new_score = current_score
                    prev_log.score_difference = score_diff
                    prev_log.resolved_test_ids = resolved_ids
                    prev_log.regressed_test_ids = regressed_ids

                    # Safeguard 4: Unacceptable regression detection & rollback
                    # If previously passing tests broke and net score dropped or regressions exceed resolutions:
                    if len(regressed_ids) > 0 and (current_score < prev_score or len(regressed_ids) > len(resolved_ids)):
                        prev_log.regression_detected = True
                        prev_log.change_accepted = False
                        prev_log.improvement_or_regression = f"REGRESSED ({round(score_diff * 100, 1)}%) [REVERTED]"

                        # ROLLBACK: Revert current agent to accepted snapshot
                        current_agent = accepted_agent.model_copy(deep=True)
                        self.save_snapshot(current_agent, active_agent_path)
                        # Stop optimization after failed repair attempt causes regression
                        break
                    else:
                        prev_log.regression_detected = False
                        prev_log.change_accepted = True
                        if score_diff > 0:
                            prev_log.improvement_or_regression = f"IMPROVED (+{round(score_diff * 100, 1)}%)"
                        elif score_diff == 0:
                            prev_log.improvement_or_regression = "UNCHANGED"
                        else:
                            prev_log.improvement_or_regression = f"REGRESSED ({round(score_diff * 100, 1)}%)"
                        accepted_agent = current_agent.model_copy(deep=True)
            else:
                accepted_agent = current_agent.model_copy(deep=True)

            prev_passed_ids = curr_passed_ids

            # Safeguard 5: Early stopping checks
            # 5a. Target pass rate reached or all tests pass
            if current_score >= target_pass_rate or not failed_cases:
                break

            # 5b. Max iteration limit reached
            if iteration >= self.max_iterations or iteration >= 3:
                break

            # 5c. Stagnation: failure set identical to previous iteration with no score improvement
            if iteration > 1 and len(scorecards) >= 2:
                prev_failed_ids = [c.test_id for c in scorecards[-2].case_results if not c.passed]
                if set(failed_ids) == set(prev_failed_ids) and current_score <= scorecards[-2].pass_rate:
                    break

            # Step 1-3: Failure classification and diagnosis
            classifications = self.classify_failures(failed_cases)
            failure_categories = [cat for cat, ids in classifications.items() if ids]

            # Step 4-6: Apply validated targeted optimizations
            optimized_agent, changes, root_cause_summary = self.apply_targeted_optimizations(
                current_agent=current_agent,
                classifications=classifications,
                iteration=iteration
            )

            # If no valid changes proposed, stop early
            if not changes:
                break

            # Create detailed iteration log entry
            log = IterationLog(
                iteration_number=iteration,
                previous_score=current_score,
                failed_test_ids=failed_ids,
                failure_categories=failure_categories,
                identified_root_causes=root_cause_summary,
                changes_applied=changes,
                reason_for_each_change="Targeted adjustments addressing specific diagnosed failure modes without full regeneration.",
                updated_configuration={
                    "top_k": optimized_agent.top_k,
                    "similarity_threshold": optimized_agent.similarity_threshold,
                    "chunk_size": optimized_agent.chunk_size,
                    "chunk_overlap": optimized_agent.chunk_overlap,
                    "system_prompt_length": len(optimized_agent.system_prompt)
                },
                new_score=current_score,  # Updated after rerun in next iteration
                score_difference=0.0,
                resolved_test_ids=[],
                regressed_test_ids=[],
                regression_detected=False,
                change_accepted=True,
                snapshot_path=iter_snapshot_path,
                improvement_or_regression="PENDING_RERUN"
            )
            iteration_logs.append(log)

            # Advance to candidate agent for next evaluation loop
            current_agent = optimized_agent
            iteration += 1

        # Post-process final iteration log if last entry is still pending
        if iteration_logs and iteration_logs[-1].improvement_or_regression == "PENDING_RERUN":
            last_score = scorecards[-1].pass_rate
            diff = round(last_score - iteration_logs[-1].previous_score, 4)
            iteration_logs[-1].new_score = last_score
            iteration_logs[-1].score_difference = diff
            if diff > 0:
                iteration_logs[-1].improvement_or_regression = f"IMPROVED (+{round(diff * 100, 1)}%)"
            elif diff == 0:
                iteration_logs[-1].improvement_or_regression = "UNCHANGED"
            else:
                iteration_logs[-1].improvement_or_regression = f"REGRESSED ({round(diff * 100, 1)}%)"

        # Final persistent artifacts
        final_snapshot_path = os.path.join(artifacts_dir, "agent_definition_final.json")
        self.save_snapshot(accepted_agent, final_snapshot_path)
        self.save_snapshot(accepted_agent, active_agent_path)

        # Write iteration_logs.json
        logs_path = os.path.join(artifacts_dir, "iteration_logs.json")
        with open(logs_path, "w", encoding="utf-8") as f:
            f.write(json.dumps([l.model_dump() for l in iteration_logs], indent=2))

        # Write scorecards.json
        scorecards_path = os.path.join(artifacts_dir, "scorecards.json")
        with open(scorecards_path, "w", encoding="utf-8") as f:
            f.write(json.dumps([sc.model_dump() for sc in scorecards], indent=2))

        return accepted_agent, scorecards, iteration_logs
