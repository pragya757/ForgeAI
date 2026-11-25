import os
import pytest
from app.llm.mock_client import MockLLMClient
from app.factory.interviewer import IntakeInterviewer
from app.factory.groundability import GroundabilityGuard
from app.factory.agent_generator import AgentGenerator
from app.schemas.requirements import Requirements, InformationGapAnalysis
from app.schemas.groundability import GroundabilityReport

@pytest.fixture
def unfamiliar_domain_docs(tmp_path):
    """Create an unfamiliar domain document collection (Deep-Sea Submersible Mission)
    containing intentional contradictions, duplicates, incomplete sections, and missing data.
    """
    doc_dir = tmp_path / "deep_sea_docs"
    doc_dir.mkdir()

    # Doc 1: Vehicle Specifications (with limit = 3000m)
    spec_file = doc_dir / "vehicle_specifications.txt"
    spec_file.write_text(
        "VEHICLE SPECIFICATIONS: TRITON-X DEEP SEA ROV\n"
        "Maximum Depth: 3000m rated titanium pressure hull.\n"
        "Battery Capacity: 120 kWh lithium-polymer pack.\n"
        "Max Speed: 4.5 knots forward thrust.\n"
        "Thruster Configuration: 6 vectored brushless DC thrusters.\n"
        "Emergency Ascent Procedure: Drop ballast weights, inflate flotation collar, and transmit acoustic beacon.\n"
    )

    # Doc 2: Mission Safety Guidelines (Contradicts Doc 1 with limit = 4500m, and duplicates emergency ascent)
    safety_file = doc_dir / "mission_safety_protocol.txt"
    safety_file.write_text(
        "MISSION SAFETY PROTOCOL\n"
        "Operating Limits:\n"
        "Maximum Depth: 4500m emergency crush ceiling per naval bulletin 2026.\n"
        "Emergency Ascent Procedure: Drop ballast weights, inflate flotation collar, and transmit acoustic beacon.\n"
        "Acoustic Comms Frequency: 12 kHz ultra-short baseline transponder.\n"
        "Emergency Abort Criteria: Battery level dropping below 15%.\n"
    )

    # Doc 3: Sensor Payload Guide (contains incomplete marker [TBD])
    sensor_file = doc_dir / "payload_sensors.txt"
    sensor_file.write_text(
        "SCIENTIFIC PAYLOAD SENSOR SUITE\n"
        "Bathymetric Multibeam Sonar: 400 kHz resolution.\n"
        "CTD Profiler: Conductivity, temperature, depth sensor suite.\n"
        "Methane Sniffer: Electrochemical hydrocarbon detector.\n"
        "Thermal Calibration Threshold: [TBD] - Pending final lab calibration before dive deployment.\n"
    )

    return str(doc_dir)

def test_document_inventory_and_topics(unfamiliar_domain_docs):
    """Verify document inspection produces detailed inventory with detected topics, formats, and character counts."""
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    inventory = interviewer.inspect_documents(unfamiliar_domain_docs)

    assert len(inventory) == 3
    filenames = {item.filename for item in inventory}
    assert "vehicle_specifications.txt" in filenames
    assert "mission_safety_protocol.txt" in filenames
    assert "payload_sensors.txt" in filenames

    for item in inventory:
        assert item.format == "TXT"
        assert item.page_count == 1
        assert len(item.description) > 0
        assert item.content_summary is not None
        assert len(item.detected_topics) > 0

def test_detect_information_gaps_contradictions_and_incompleteness(unfamiliar_domain_docs):
    """Verify that gaps, contradictions, duplicates, and incomplete markers are detected across unfamiliar documents."""
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    inventory = interviewer.inspect_documents(unfamiliar_domain_docs)
    
    brief = "Create an assistant for deep-sea ROV diving operations, checking vehicle depth, emergency ascent, payload sensors, and atmospheric ionosphere radiation telemetry."
    gaps = interviewer.detect_information_gaps(inventory, unfamiliar_domain_docs, brief)

    assert isinstance(gaps, InformationGapAnalysis)

    # 1. Contradiction detected (3000m vs 4500m depth)
    assert len(gaps.contradictory_information) > 0
    contradiction = gaps.contradictory_information[0]
    assert "depth" in contradiction.topic.lower()
    assert len(contradiction.conflicting_sources) >= 2
    assert "vehicle_specifications.txt" in contradiction.conflicting_sources
    assert "mission_safety_protocol.txt" in contradiction.conflicting_sources
    assert len(contradiction.resolution_strategy) > 0

    # 2. Duplicate passage detected (Emergency Ascent Procedure)
    assert len(gaps.duplicated_information) > 0
    assert any("ascent" in d.lower() or "ballast" in d.lower() for d in gaps.duplicated_information)

    # 3. Incomplete information detected ([TBD] marker)
    assert len(gaps.incomplete_information) > 0
    assert any("[tbd]" in inc.lower() for inc in gaps.incomplete_information)

    # 4. Missing information detected (ionosphere radiation telemetry not in underwater docs)
    assert len(gaps.missing_information) > 0

def test_clarifying_questions_ceiling_and_gap_targeting(unfamiliar_domain_docs):
    """Verify that clarifying questions do not exceed 5 and specifically target detected ambiguities and contradictions."""
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    brief = "Assist ROV pilots during deep sea missions with specs and procedures."
    questions = interviewer.generate_clarifying_questions(brief, unfamiliar_domain_docs)

    assert isinstance(questions, list)
    assert 1 <= len(questions) <= 5
    # Must target the depth contradiction or gaps
    question_text = " ".join(questions).lower()
    assert "depth" in question_text or "precedence" in question_text or "which" in question_text or "audience" in question_text

def test_structured_requirement_extraction_and_unattended_mode(unfamiliar_domain_docs):
    """Verify structured requirements extraction with intent, domain, constraints, and conservative unattended assumptions."""
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    brief = "Deep-sea ROV operational assistant for pilot teleoperation and mission safety guidelines."

    requirements = interviewer.conduct_interview(
        brief=brief,
        doc_folder=unfamiliar_domain_docs,
        unattended=True
    )

    assert isinstance(requirements, Requirements)
    assert len(requirements.agent_name) > 0
    assert len(requirements.user_intent) > 0
    assert len(requirements.domain) > 0
    assert len(requirements.target_audience) > 0
    assert len(requirements.scope) > 0
    assert len(requirements.tone) > 0
    assert len(requirements.constraints) > 0

    # Unattended conservative assumptions must be documented
    assert len(requirements.assumptions) > 0
    assumptions_text = " ".join(requirements.assumptions).lower()
    assert "conservative" in assumptions_text or "precedence" in assumptions_text or "sole ground truth" in assumptions_text

    # Information gaps embedded in requirements
    assert len(requirements.information_gaps.contradictory_information) > 0

def test_groundability_guard_evidence_references_and_confidence(unfamiliar_domain_docs):
    """Verify that groundability guard maps topics to evidence references, assigns confidence scores, and classifies absence."""
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    requirements = interviewer.conduct_interview(
        brief="Deep-sea ROV operational assistant for vehicle depth, emergency ascent, and thrusters.",
        doc_folder=unfamiliar_domain_docs,
        unattended=True
    )

    guard = GroundabilityGuard(llm_client=MockLLMClient())
    report = guard.inspect_groundability(requirements=requirements, doc_folder=unfamiliar_domain_docs)

    assert isinstance(report, GroundabilityReport)
    assert 0.0 <= report.overall_groundability_score <= 1.0

    # Supported topics must have evidence references and confidence
    assert len(report.supported_topics) > 0
    for st in report.supported_topics:
        assert 0.0 <= st.confidence_score <= 1.0
        assert len(st.evidence_references) > 0
        ref = st.evidence_references[0]
        assert ref.source_document in ["vehicle_specifications.txt", "mission_safety_protocol.txt", "payload_sensors.txt"]
        assert len(ref.excerpt) > 0
        assert 0.0 <= ref.relevance_score <= 1.0

    # Unsupported topics must classify absence nature
    assert len(report.unsupported_topics) > 0
    for ut in report.unsupported_topics:
        assert ut.absence_nature in ["missing_from_corpus", "inherently_nonexistent", "unsupported_capability"]
        assert 0.0 <= ut.confidence_score <= 1.0

def test_absence_nature_differentiation():
    """Verify explicit distinction between missing from corpus vs inherently nonexistent vs unsupported capability."""
    guard = GroundabilityGuard(llm_client=MockLLMClient())

    # Capability / transaction
    assert guard._classify_absence_nature("Execute live thruster fire command", "Direct hardware control") == "unsupported_capability"
    assert guard._classify_absence_nature("Automated wire transfer payment", "Financial transaction") == "unsupported_capability"

    # Inherently non-existent / impossible
    assert guard._classify_absence_nature("Deep sea telepathy communication", "Impossible physics") == "inherently_nonexistent"
    assert guard._classify_absence_nature("Martian ocean atmospheric sampling", "Fictional location") == "inherently_nonexistent"

    # Missing from corpus
    assert guard._classify_absence_nature("Propeller spare part price catalog", "Document not uploaded") == "missing_from_corpus"

def test_unsupported_requirements_excluded_from_answerable_scope(unfamiliar_domain_docs):
    """Verify that unsupported topics are strictly prevented from entering sanitized_answerable_topics and generated agent."""
    interviewer = IntakeInterviewer(llm_client=MockLLMClient())
    requirements = interviewer.conduct_interview(
        brief="Deep-sea ROV assistant that must also execute live thruster fires and Martian weather forecasts.",
        doc_folder=unfamiliar_domain_docs,
        unattended=True
    )
    # Add explicit unsupported topics
    requirements.unsupported_requirements.extend(["Live thruster execution", "Martian weather forecasts"])

    guard = GroundabilityGuard(llm_client=MockLLMClient())
    report = guard.inspect_groundability(requirements=requirements, doc_folder=unfamiliar_domain_docs)

    # Assert sanitized_answerable_topics contains NO unsupported topics
    unsupported_names = {u.topic for u in report.unsupported_topics}
    for answerable in report.sanitized_answerable_topics:
        assert answerable not in unsupported_names

    # Assert AgentGenerator incorporates groundability guard sanitization
    agent_gen = AgentGenerator(llm_client=MockLLMClient())
    agent_def = agent_gen.generate_agent(
        requirements=requirements,
        groundability=report,
        doc_folder=unfamiliar_domain_docs
    )

    for ans in agent_def.supported_topics:
        assert ans not in unsupported_names
    for un in unsupported_names:
        assert un in agent_def.must_refuse_topics
