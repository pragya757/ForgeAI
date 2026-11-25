import pytest
from app.factory.critic_optimizer import CriticOptimizer
from app.factory.interviewer import IntakeInterviewer
from app.schemas.scorecard import CaseEvaluationResult
from app.schemas.agent_definition import AgentDefinition, OutputContract, CitationRequirements, ModelConfig
from app.llm.mock_client import MockLLMClient

def test_all_six_failure_classifications():
    critic = CriticOptimizer(llm_client=MockLLMClient())

    cases = [
        CaseEvaluationResult(
            test_id="TC-REFUSE",
            question="Refusal query",
            passed=False,
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=1.0,
            refusal_correctness=0.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            failure_reasons=["wrong_refusal: Expected refusal for out-of-scope question, but agent answered."],
            agent_response="Answered when should refuse",
            retrieved_sources=["doc.pdf"]
        ),
        CaseEvaluationResult(
            test_id="TC-CITE",
            question="Citation query",
            passed=False,
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=0.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            failure_reasons=["citation_defect: Response omitted mandatory citation tag."],
            agent_response="Factual answer without citation",
            retrieved_sources=["doc.pdf"]
        ),
        CaseEvaluationResult(
            test_id="TC-RETR",
            question="Retrieval query",
            passed=False,
            grounding_score=0.5,
            factual_correctness=0.5,
            citation_correctness=0.5,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            failure_reasons=["retrieval_miss: Relevant document chunk was not retrieved."],
            agent_response="Vague answer",
            retrieved_sources=[]
        ),
        CaseEvaluationResult(
            test_id="TC-HALLUC",
            question="Hallucination query",
            passed=False,
            grounding_score=0.2,
            factual_correctness=0.5,
            citation_correctness=1.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=1.0,
            failure_reasons=["hallucination: Response contains unsupported factual speculation."],
            agent_response="Fabricated text",
            retrieved_sources=["doc.pdf"]
        ),
        CaseEvaluationResult(
            test_id="TC-CONTRACT",
            question="Contract query",
            passed=False,
            grounding_score=1.0,
            factual_correctness=1.0,
            citation_correctness=1.0,
            refusal_correctness=1.0,
            relevance_score=1.0,
            output_contract_compliance=0.0,
            failure_reasons=["output_contract_violation: Response text violates markdown structure."],
            agent_response="bad format",
            retrieved_sources=["doc.pdf"]
        ),
        CaseEvaluationResult(
            test_id="TC-PROMPT",
            question="Prompt query",
            passed=False,
            grounding_score=0.8,
            factual_correctness=0.6,
            citation_correctness=0.8,
            refusal_correctness=1.0,
            relevance_score=0.5,
            output_contract_compliance=1.0,
            failure_reasons=["prompt_defect: Answer structure lacked directness."],
            agent_response="Indirect answer",
            retrieved_sources=["doc.pdf"]
        ),
    ]

    classifications = critic.classify_failures(cases)
    assert "TC-REFUSE" in classifications["wrong_refusal"]
    assert "TC-CITE" in classifications["citation_defect"]
    assert "TC-RETR" in classifications["retrieval_miss"]
    assert "TC-HALLUC" in classifications["hallucination"]
    assert "TC-CONTRACT" in classifications["output_contract_violation"]
    assert "TC-PROMPT" in classifications["prompt_defect"]

def test_targeted_optimizations():
    critic = CriticOptimizer(llm_client=MockLLMClient())
    agent = AgentDefinition(
        agent_name="Base Agent",
        description="Base",
        system_prompt="Initial instructions.",
        target_audience="Staff",
        supported_topics=["Topic A"],
        unsupported_topics=[],
        must_refuse_topics=[],
        document_references=["doc.pdf"],
        top_k=4,
        similarity_threshold=0.35,
        output_contract=OutputContract(),
        citation_requirements=CitationRequirements(),
        refusal_policy="Strict",
        model_config=ModelConfig()
    )

    # Apply retrieval miss fix
    updated, changes, root = critic.apply_targeted_optimizations(
        current_agent=agent,
        classifications={"retrieval_miss": ["TC-001"]},
        iteration=1
    )
    assert updated.top_k == 5
    assert updated.similarity_threshold == 0.30
    assert any(c["target"] == "top_k" for c in changes)

    # Apply citation defect fix
    updated2, changes2, root2 = critic.apply_targeted_optimizations(
        current_agent=agent,
        classifications={"citation_defect": ["TC-002"]},
        iteration=1
    )
    assert "MANDATORY CITATION RULE" in updated2.system_prompt

def test_maximum_five_clarifying_questions():
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    questions = interviewer.generate_clarifying_questions(
        brief="Create an assistant for technical ship operations",
        doc_folder="demos/procurement_assistant/documents"
    )
    assert isinstance(questions, list)
    assert len(questions) > 0
    assert len(questions) <= 5
