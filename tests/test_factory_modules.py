import os
import json
import pytest
from app.llm.mock_client import MockLLMClient
from app.factory.interviewer import IntakeInterviewer
from app.factory.groundability import GroundabilityGuard
from app.factory.agent_generator import AgentGenerator
from app.factory.eval_generator import AutomaticEvalGenerator
from app.factory.judge import HybridJudge
from app.factory.critic_optimizer import CriticOptimizer
from app.factory.reporter import HonestReportGenerator

@pytest.fixture
def mock_llm():
    return MockLLMClient()

def test_intake_interviewer(mock_llm):
    interviewer = IntakeInterviewer(llm_client=mock_llm)
    reqs = interviewer.conduct_interview(
        brief="Create an HR assistant for leave and attendance",
        doc_folder="demos/hr_assistant/documents",
        unattended=True
    )
    assert reqs.agent_name == "HR Policy Assistant"
    assert "Annual leave" in reqs.must_answer_topics
    assert "current_date" in reqs.required_tools

def test_groundability_guard(mock_llm):
    interviewer = IntakeInterviewer(llm_client=mock_llm)
    reqs = interviewer.conduct_interview(
        brief="Create an HR assistant for leave and attendance",
        doc_folder="demos/hr_assistant/documents",
        unattended=True
    )
    guard = GroundabilityGuard(llm_client=mock_llm)
    report = guard.inspect_groundability(requirements=reqs, doc_folder="demos/hr_assistant/documents")
    assert report.overall_groundability_score >= 0.8
    assert len(report.supported_topics) > 0
    assert len(report.unsupported_topics) > 0

def test_agent_generator(mock_llm):
    interviewer = IntakeInterviewer(llm_client=mock_llm)
    reqs = interviewer.conduct_interview(
        brief="Create an HR assistant for leave and attendance",
        doc_folder="demos/hr_assistant/documents",
        unattended=True
    )
    guard = GroundabilityGuard(llm_client=mock_llm)
    report = guard.inspect_groundability(requirements=reqs, doc_folder="demos/hr_assistant/documents")

    generator = AgentGenerator(llm_client=mock_llm)
    agent_def = generator.generate_agent(requirements=reqs, groundability=report, doc_folder="demos/hr_assistant/documents")
    assert agent_def.agent_name == "HR Policy Assistant"
    assert "leave_policy.pdf" in agent_def.document_references
    assert agent_def.chunk_size > 0

def test_eval_generator_at_least_20_cases(mock_llm):
    interviewer = IntakeInterviewer(llm_client=mock_llm)
    reqs = interviewer.conduct_interview(
        brief="Create an HR assistant for leave and attendance",
        doc_folder="demos/hr_assistant/documents",
        unattended=True
    )
    guard = GroundabilityGuard(llm_client=mock_llm)
    report = guard.inspect_groundability(requirements=reqs, doc_folder="demos/hr_assistant/documents")
    generator = AgentGenerator(llm_client=mock_llm)
    agent_def = generator.generate_agent(requirements=reqs, groundability=report, doc_folder="demos/hr_assistant/documents")

    eval_gen = AutomaticEvalGenerator(llm_client=mock_llm)
    eval_set, prompt_text = eval_gen.generate_evaluation_set(agent_def=agent_def, doc_folder="demos/hr_assistant/documents", target_count=20)
    assert len(eval_set.cases) >= 20
    # Check category distribution
    categories = {c.test_category for c in eval_set.cases}
    assert "answerable" in categories
    assert "out_of_scope" in categories
    assert "edge_case" in categories

def test_critic_optimizer_max_iterations(mock_llm, tmp_path):
    critic = CriticOptimizer(llm_client=mock_llm, max_iterations=3)
    assert critic.max_iterations == 3
