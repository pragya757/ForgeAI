import pytest
from pydantic import ValidationError
from app.schemas.requirements import Requirements, DocumentItem
from app.schemas.groundability import GroundabilityReport, SupportedTopic, UnsupportedTopic
from app.schemas.agent_definition import AgentDefinition, OutputContract, CitationRequirements, ModelConfig
from app.schemas.evaluation import EvalSet, EvalCase
from app.schemas.scorecard import IterationScorecard, CaseEvaluationResult

def test_requirements_schema_validation():
    req = Requirements(
        agent_name="Test Agent",
        purpose="Test purpose",
        target_audience="Engineers",
        scope="Internal tools",
        tone="Professional",
        must_answer_topics=["Topic A"],
        must_refuse_topics=["Topic B"],
        required_tools=["current_date"],
        document_inventory=[DocumentItem(filename="doc.pdf", format="PDF")],
        assumptions=["Current year"],
        ambiguities=[],
        unsupported_requirements=["Topic B"]
    )
    assert req.agent_name == "Test Agent"
    assert len(req.document_inventory) == 1

def test_groundability_schema_validation():
    report = GroundabilityReport(
        supported_topics=[SupportedTopic(topic="Topic A", evidence_sources=["doc.pdf"], coverage_summary="Verified")],
        partially_supported_topics=[],
        unsupported_topics=[UnsupportedTopic(topic="Topic B", reason="Missing docs")],
        document_coverage_map={"doc.pdf": ["Topic A"]},
        refusal_recommendations=["Refuse Topic B"],
        overall_groundability_score=0.85
    )
    assert report.overall_groundability_score == 0.85
    assert len(report.supported_topics) == 1

def test_agent_definition_schema_validation():
    agent_def = AgentDefinition(
        agent_name="Valid Agent",
        description="Valid description",
        system_prompt="Answer strictly from context.",
        target_audience="General audience",
        supported_topics=["Topic A"],
        unsupported_topics=["Topic B"],
        must_refuse_topics=["Topic B"],
        document_references=["doc.pdf"],
        chunk_size=500,
        chunk_overlap=100,
        embedding_model="all-MiniLM-L6-v2",
        retrieval_method="dense_vector_faiss",
        top_k=4,
        similarity_threshold=0.35,
        tool_selection=["current_date"],
        output_contract=OutputContract(),
        citation_requirements=CitationRequirements(),
        refusal_policy="Refuse ungrounded queries.",
        model_config=ModelConfig()
    )
    assert agent_def.agent_name == "Valid Agent"
    data = agent_def.model_dump(by_alias=True)
    assert "model_config" in data

def test_eval_set_schema():
    case = EvalCase(
        test_id="TC-001",
        question="How many days?",
        test_category="answerable",
        expected_answer="20 days",
        expected_sources=["doc.pdf"],
        expected_action="answer",
        ground_truth_evidence="Direct text evidence",
        evaluation_criteria="Must state 20 days"
    )
    eval_set = EvalSet(cases=[case])
    assert len(eval_set.cases) == 1
    assert eval_set.cases[0].test_id == "TC-001"
