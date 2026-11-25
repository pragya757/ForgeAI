import os
import json
from typing import Optional, Dict, Any, Tuple
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.requirements import Requirements
from app.schemas.groundability import GroundabilityReport
from app.schemas.agent_definition import AgentDefinition
from app.schemas.evaluation import EvalSet
from app.factory.interviewer import IntakeInterviewer
from app.factory.groundability import GroundabilityGuard
from app.factory.agent_generator import AgentGenerator
from app.factory.eval_generator import AutomaticEvalGenerator
from app.factory.critic_optimizer import CriticOptimizer
from app.factory.reporter import HonestReportGenerator

class ForgeAIFactory:
    """Master Factory Orchestrator - End-to-end autonomous agent creation pipeline."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None, max_iterations: int = 3):
        self.llm = llm_client or get_llm_client()
        self.max_iterations = max_iterations

        self.interviewer = IntakeInterviewer(self.llm)
        self.groundability_guard = GroundabilityGuard(self.llm)
        self.agent_generator = AgentGenerator(self.llm)
        self.eval_generator = AutomaticEvalGenerator(self.llm)
        self.critic_optimizer = CriticOptimizer(self.llm, max_iterations=max_iterations)
        self.reporter = HonestReportGenerator()

    def build_agent(
        self,
        brief: str,
        doc_folder: str,
        output_dir: str,
        clarification_answers: Optional[Dict[str, str]] = None,
        unattended: bool = True
    ) -> Dict[str, Any]:
        """Execute all factory stages and produce verified agent artifacts."""
        os.makedirs(output_dir, exist_ok=True)
        print(f"\n=======================================================")
        print(f"[*] ForgeAI: Starting Autonomous Agent Factory Pipeline")
        print(f"[*] Brief: {brief[:100]}...")
        print(f"[*] Document Folder: {doc_folder}")
        print(f"[*] Artifacts Directory: {output_dir}")
        print(f"=======================================================\n")

        # Stage 1: Intake Interviewer
        print("[Stage 1/7] Running Intake Interviewer...")
        requirements = self.interviewer.conduct_interview(
            brief=brief,
            doc_folder=doc_folder,
            clarification_answers=clarification_answers,
            unattended=unattended
        )
        req_path = os.path.join(output_dir, "requirements.json")
        self.interviewer.save_requirements(requirements, req_path)
        print(f"  -> Generated {req_path} (Agent: '{requirements.agent_name}')")

        # Stage 2: Groundability Guard
        print("[Stage 2/7] Running Groundability Guard...")
        groundability = self.groundability_guard.inspect_groundability(
            requirements=requirements,
            doc_folder=doc_folder
        )
        guard_path = os.path.join(output_dir, "groundability_report.json")
        self.groundability_guard.save_report(groundability, guard_path)
        print(f"  -> Generated {guard_path} (Groundability Score: {groundability.overall_groundability_score * 100:.1f}%)")

        # Stage 3: Agent Generator
        print("[Stage 3/7] Running Agent Generator...")
        initial_agent = self.agent_generator.generate_agent(
            requirements=requirements,
            groundability=groundability,
            doc_folder=doc_folder
        )
        agent_def_path = os.path.join(output_dir, "agent_definition.json")
        self.agent_generator.save_definition(initial_agent, agent_def_path)
        print(f"  -> Generated {agent_def_path} (Tools: {initial_agent.tool_selection})")

        # Stage 4: Automatic Evaluation Generator (>= 20 cases)
        print("[Stage 4/7] Generating Automatic Evaluation Set (>= 20 cases)...")
        eval_set, prompt_text = self.eval_generator.generate_evaluation_set(
            agent_def=initial_agent,
            doc_folder=doc_folder,
            target_count=20
        )
        self.eval_generator.save_artifacts(eval_set, prompt_text, output_dir)
        print(f"  -> Generated eval_set.json with {len(eval_set.cases)} test cases.")

        # Stage 5 & 6: Critic-Optimizer Loop (Hybrid Judge + Targeted Refinement)
        print(f"[Stage 5-6/7] Running Critic-Optimizer Loop (Max {self.max_iterations} iterations)...")
        final_agent, scorecards, iteration_logs = self.critic_optimizer.run_optimization_loop(
            initial_agent=initial_agent,
            eval_set=eval_set,
            doc_folder=doc_folder,
            artifacts_dir=output_dir,
            target_pass_rate=0.90
        )
        print(f"  -> Completed {len(scorecards)} evaluation iteration(s).")
        for sc in scorecards:
            print(f"     Iteration {sc.iteration}: Pass Rate = {sc.pass_rate * 100:.1f}% ({sc.passed_tests}/{sc.total_tests})")

        # Stage 7: Honest Report Generator
        print("[Stage 7/7] Generating Honest Final Quality Report...")
        report_md = self.reporter.generate_report(
            brief=brief,
            requirements=requirements,
            groundability=groundability,
            final_agent=final_agent,
            scorecards=scorecards,
            iteration_logs=iteration_logs,
            output_dir=output_dir,
            eval_set=eval_set
        )
        print(f"  -> Generated final_report.md, quality_report.json, scorecards.json, iteration_logs.json")
        print("\n=======================================================")
        print(f"[+] ForgeAI Factory Execution Complete! Status: {scorecards[-1].status if scorecards else 'UNKNOWN'}")
        print("=======================================================\n")

        quality_json_path = os.path.join(output_dir, "quality_report.json")
        report_json = {}
        if os.path.exists(quality_json_path):
            with open(quality_json_path, "r", encoding="utf-8") as f:
                report_json = json.load(f)

        return {
            "requirements": requirements,
            "groundability": groundability,
            "agent_definition": final_agent,
            "eval_set": eval_set,
            "scorecards": scorecards,
            "iteration_logs": iteration_logs,
            "report_md": report_md,
            "report_json": report_json
        }
