import os
import json
import pytest
from app.llm.mock_client import MockLLMClient
from app.factory.eval_generator import AutomaticEvalGenerator
from app.schemas.agent_definition import AgentDefinition, OutputContract, CitationRequirements, ModelConfig
from app.schemas.evaluation import EvalSet, EvalCase
from app.retrieval.document_loader import DocumentLoader, RawDocument

@pytest.fixture
def multi_doc_corpus(tmp_path):
    """Multi-document collection with cross-document dependencies and specs."""
    doc_dir = tmp_path / "telecom_docs"
    doc_dir.mkdir()

    doc_a = doc_dir / "satellite_transceiver_specs.txt"
    doc_a.write_text(
        "SATELLITE TRANSCEIVER SUBSYSTEM (KU-BAND):\n"
        "Operating Frequency: 14.0 to 14.5 GHz uplink, 11.7 to 12.2 GHz downlink.\n"
        "Maximum Transmit Power: 40 Watts RF output via Solid-State Power Amplifier (SSPA).\n"
        "Parabolic Reflector Diameter: 1.2 meters carbon-fiber composite.\n"
        "Pointing Accuracy Threshold: 0.15 degrees RMS tracking error.\n"
        "Emergency Transmit Mute: Cut power to SSPA within 5 milliseconds upon loss of lock.\n"
    )

    doc_b = doc_dir = tmp_path / "telecom_docs"
    doc_b_file = doc_b / "network_operations_protocol.txt"
    doc_b_file.write_text(
        "NETWORK OPERATIONS PROTOCOL:\n"
        "Transceiver Uplink Authorization: Ku-band transmission requires Level-2 NOC operator sign-off.\n"
        "Weather Depolarization Threshold: Switch to rain fade margin profile when attenuation exceeds 3.5 dB.\n"
        "Emergency Shutdown Procedure: Trigger emergency transmit mute and notify hub controller via terrestrial link.\n"
        "Operating Frequency Limit: Do not exceed 14.5 GHz under any circumstances.\n"
    )

    return str(doc_b)

@pytest.fixture
def telecom_agent_def():
    return AgentDefinition(
        agent_name="Satellite Ground-Station Assistant",
        description="Operational assistant for Ku-band satellite transceivers and uplink protocols.",
        system_prompt="Answer satellite operations queries based solely on provided documentation.",
        target_audience="NOC operators and field RF engineers",
        supported_topics=[
            "Operating Frequency",
            "Maximum Transmit Power",
            "Pointing Accuracy Threshold",
            "Emergency Transmit Mute",
            "Weather Depolarization Threshold"
        ],
        unsupported_topics=[
            "Cryptographic telemetry key generation",
            "Ground station real estate acquisition",
            "Orbital slot bidding"
        ],
        must_refuse_topics=[
            "Cryptographic telemetry key generation",
            "Ground station real estate acquisition",
            "Orbital slot bidding"
        ],
        document_references=[
            "satellite_transceiver_specs.txt",
            "network_operations_protocol.txt"
        ],
        chunk_size=450,
        chunk_overlap=90,
        embedding_model="all-MiniLM-L6-v2",
        retrieval_method="dense_vector_faiss",
        top_k=4,
        similarity_threshold=0.35,
        tool_selection=["current_date", "calculator"],
        output_contract=OutputContract(
            format="markdown",
            require_citations=True,
            citation_format="[Source: <document_name>, Page: <page>]",
            refusal_phrase="I cannot answer this question as it is outside my verified documentation scope."
        ),
        citation_requirements=CitationRequirements(
            must_cite=True,
            format="[Source: <filename>, Page: <page>]",
            granularity="sentence_level"
        ),
        refusal_policy="Strict refusal on unauthorized frequency override, crypto keys, or real estate.",
        model_config=ModelConfig()
    )

def test_generate_at_least_20_cases_from_documents(multi_doc_corpus, telecom_agent_def):
    """Verify evaluation generator produces at least 20 test cases directly from documents."""
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    eval_set, prompt = eval_gen.generate_evaluation_set(
        agent_def=telecom_agent_def,
        doc_folder=multi_doc_corpus,
        target_count=20
    )

    assert isinstance(eval_set, EvalSet)
    assert len(eval_set.cases) >= 20
    assert len(prompt) > 100

def test_coverage_across_all_mandatory_categories(multi_doc_corpus, telecom_agent_def):
    """Verify test set covers all required categories:
    direct_factual, multi_hop, cross_document, ambiguous, missing_information,
    out_of_scope, contradictory_document, and misleading_assumption.
    """
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    raw_docs = DocumentLoader.load_directory(multi_doc_corpus)
    cases = eval_gen.generate_dynamic_eval_cases(agent_def=telecom_agent_def, docs=raw_docs, target_count=20)

    subcategories = {c.subcategory for c in cases if c.subcategory}
    assert "direct_factual" in subcategories
    assert "multi_hop" in subcategories
    assert "cross_document" in subcategories
    assert "ambiguous" in subcategories
    assert "missing_information" in subcategories
    assert "out_of_scope" in subcategories
    assert "contradictory_document" in subcategories
    assert "misleading_assumption" in subcategories

def test_every_case_has_required_attributes(multi_doc_corpus, telecom_agent_def):
    """Verify every case contains unique ID, question, category, expected action, expected facts, sources, locations, evidence, and criteria."""
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    eval_set, _ = eval_gen.generate_evaluation_set(agent_def=telecom_agent_def, doc_folder=multi_doc_corpus, target_count=20)

    seen_ids = set()
    for case in eval_set.cases:
        # Unique test ID
        assert case.test_id not in seen_ids
        seen_ids.add(case.test_id)

        # Non-empty fields
        assert len(case.question.strip()) > 10
        assert case.test_category in {"answerable", "out_of_scope", "edge_case"}
        assert case.expected_action in {"answer", "refuse", "clarify"}
        assert len(case.expected_answer.strip()) > 5
        assert len(case.expected_facts) > 0
        assert len(case.evaluation_criteria.strip()) > 5

        # Ground-truth evidence must exist
        assert len(case.ground_truth_evidence.strip()) > 5

        # Source locations where answerable
        if case.expected_action == "answer":
            assert len(case.expected_sources) > 0
            assert len(case.source_locations) > 0

def test_validation_ensures_expected_facts_supported_by_source_evidence(multi_doc_corpus, telecom_agent_def):
    """Verify validation flags and rejects expected facts that cannot be traced to source documents."""
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    raw_docs = DocumentLoader.load_directory(multi_doc_corpus)

    # Valid case
    valid_case = EvalCase(
        test_id="TC-001",
        question="What is the maximum transmit power of the Ku-band SSPA?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="Maximum Transmit Power is 40 Watts RF output via Solid-State Power Amplifier (SSPA).",
        expected_facts=["40 Watts RF output via Solid-State Power Amplifier (SSPA)"],
        expected_sources=["satellite_transceiver_specs.txt"],
        source_locations=["Page 1"],
        ground_truth_evidence="Maximum Transmit Power: 40 Watts RF output via Solid-State Power Amplifier (SSPA).",
        evaluation_criteria="Must state 40 Watts RF output."
    )
    is_valid, reason = eval_gen.validate_test_case(valid_case, raw_docs, telecom_agent_def)
    assert is_valid is True
    assert reason is None

    # Invalid case: fabricated fact not present anywhere in documents
    invalid_fact_case = EvalCase(
        test_id="TC-002",
        question="What is the parabolic reflector diameter?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The diameter is 85.5 meters made of solid gold.",
        expected_facts=["85.5 meters made of solid gold titanium alloy with nuclear batteries"],
        expected_sources=["satellite_transceiver_specs.txt"],
        source_locations=["Page 1"],
        ground_truth_evidence="Fabricated text not in document: 85.5 meters gold alloy.",
        evaluation_criteria="Must state 85.5 meters gold."
    )
    is_valid, reason = eval_gen.validate_test_case(invalid_fact_case, raw_docs, telecom_agent_def)
    assert is_valid is False
    assert "not supported" in reason or "cannot be traced" in reason

def test_duplicate_question_detection():
    """Verify duplicate question detection rejects near-identical questions."""
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    existing = [
        "What is the maximum transmit power of the Ku-band solid state power amplifier?",
        "When is multi-factor authentication required for production systems?"
    ]

    # Near-identical variation
    duplicate_q = "What is the maximum transmit power of the Ku-band solid state power amplifier?"
    assert eval_gen.is_duplicate_question(duplicate_q, existing) is True

    # High overlap variation
    slight_variation = "What is the maximum transmit power for Ku-band power amplifier?"
    assert eval_gen.is_duplicate_question(slight_variation, existing) is True

    # Distinct question
    distinct_q = "Under what weather conditions does rain fade margin attenuation exceed 3.5 dB?"
    assert eval_gen.is_duplicate_question(distinct_q, existing) is False

def test_validation_rejects_invalid_test_cases(multi_doc_corpus, telecom_agent_def):
    """Verify validation rejects cases with missing IDs, invalid actions, or missing sources."""
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    raw_docs = DocumentLoader.load_directory(multi_doc_corpus)

    # Empty question
    bad_case1 = EvalCase(
        test_id="TC-099",
        question="",
        test_category="answerable",
        expected_action="answer",
        expected_answer="Some answer",
        ground_truth_evidence="Some evidence",
        evaluation_criteria="Some criteria"
    )
    assert eval_gen.validate_test_case(bad_case1, raw_docs, telecom_agent_def)[0] is False

    # Invalid action
    bad_case2 = EvalCase(
        test_id="TC-099",
        question="What is the frequency range of the uplink transceivers?",
        test_category="answerable",
        expected_action="execute_command", # invalid
        expected_answer="Some answer",
        ground_truth_evidence="Operating Frequency: 14.0 to 14.5 GHz uplink",
        evaluation_criteria="Some criteria"
    )
    assert eval_gen.validate_test_case(bad_case2, raw_docs, telecom_agent_def)[0] is False

    # Non-existent source document
    bad_case3 = EvalCase(
        test_id="TC-099",
        question="What is the frequency range of the uplink transceivers?",
        test_category="answerable",
        expected_action="answer",
        expected_answer="14.0 to 14.5 GHz",
        expected_sources=["non_existent_ghost_file.pdf"],
        ground_truth_evidence="Operating Frequency: 14.0 to 14.5 GHz uplink",
        evaluation_criteria="Some criteria"
    )
    assert eval_gen.validate_test_case(bad_case3, raw_docs, telecom_agent_def)[0] is False

def test_eval_set_reused_identically_across_optimizer_iterations(tmp_path, multi_doc_corpus, telecom_agent_def):
    """Verify that the exact same evaluation set is evaluated across all optimization iterations."""
    eval_gen = AutomaticEvalGenerator(llm_client=MockLLMClient())
    eval_set, _ = eval_gen.generate_evaluation_set(agent_def=telecom_agent_def, doc_folder=multi_doc_corpus, target_count=20)

    # Record initial fingerprints
    initial_ids = [c.test_id for c in eval_set.cases]
    initial_questions = [c.question for c in eval_set.cases]

    # Save to disk
    artifacts_dir = str(tmp_path / "artifacts")
    eval_gen.save_artifacts(eval_set, "prompt", artifacts_dir)

    # Reload from disk as would happen in optimization iterations
    reloaded_path = os.path.join(artifacts_dir, "eval_set.json")
    with open(reloaded_path, "r") as f:
        reloaded_data = json.load(f)
    reloaded_eval_set = EvalSet(**reloaded_data)

    reloaded_ids = [c.test_id for c in reloaded_eval_set.cases]
    reloaded_questions = [c.question for c in reloaded_eval_set.cases]

    assert initial_ids == reloaded_ids
    assert initial_questions == reloaded_questions
    assert len(reloaded_eval_set.cases) == len(eval_set.cases)
