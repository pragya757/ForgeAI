import os
import json
import pytest
from app.llm.mock_client import MockLLMClient
from app.factory.agent_generator import AgentGenerator
from app.schemas.requirements import Requirements, DocumentItem
from app.schemas.groundability import GroundabilityReport, SupportedTopic, UnsupportedTopic
from app.schemas.agent_definition import AgentDefinition, RerankingConfig, MetadataConfig
from app.tools.registry import registry

@pytest.fixture
def wind_turbine_requirements():
    """Unseen domain: Wind Turbine Telemetry & Maintenance Assistant."""
    return Requirements(
        agent_name="Turbine Operations Assistant",
        purpose="Assist offshore wind farm engineers with turbine blade inspections, gearbox temperature thresholds, and emergency yaw brakes.",
        user_intent="Lookup turbine operational limits, check gearbox temperature thresholds, and follow emergency shutdown protocols.",
        target_audience="Offshore wind farm field engineers and remote SCADA operators",
        domain="Renewable Wind Energy Systems",
        scope="Offshore turbine models V164-9.5, yaw braking protocols, and gearbox lubrication intervals.",
        tone="Technical, authoritative, and concise",
        constraints=["Adhere strictly to OEM wind turbine documentation", "No remote electrical grid trip execution"],
        must_answer_topics=["Gearbox operating temperatures", "Blade inspection intervals", "Emergency yaw braking", "Pitch control calibration"],
        must_refuse_topics=["Remote grid breaker tripping", "Turbine lease land deeds", "Corporate executive salaries"],
        required_tools=["current_date", "calculator"],
        document_inventory=[
            DocumentItem(
                filename="turbine_scada_specs.pdf",
                format="PDF",
                description="Technical limits for V164-9.5 MW wind turbines",
                page_count=4,
                detected_topics=["Gearbox Temps", "Yaw Brakes", "SCADA Limits"]
            ),
            DocumentItem(
                filename="maintenance_intervals.pdf",
                format="PDF",
                description="Scheduled preventive maintenance schedules",
                page_count=2,
                detected_topics=["Blade Inspection", "Lubrication Cycles"]
            )
        ],
        assumptions=["Documents represent current OEM rev 3.2 guidelines."],
        ambiguities=[],
        unsupported_requirements=["Remote grid breaker tripping", "Corporate executive salaries"]
    )

@pytest.fixture
def wind_turbine_groundability():
    return GroundabilityReport(
        supported_topics=[
            SupportedTopic(
                topic="Gearbox operating temperatures",
                evidence_sources=["turbine_scada_specs.pdf"],
                coverage_summary="Normal operating range 45C to 80C; shutdown at 95C.",
                confidence_score=0.98
            ),
            SupportedTopic(
                topic="Blade inspection intervals",
                evidence_sources=["maintenance_intervals.pdf"],
                coverage_summary="Visual inspection every 6 months; ultrasonic non-destructive testing every 24 months.",
                confidence_score=0.95
            ),
            SupportedTopic(
                topic="Emergency yaw braking",
                evidence_sources=["turbine_scada_specs.pdf"],
                coverage_summary="Engage aerodynamic feathering before mechanical caliper lock.",
                confidence_score=0.96
            )
        ],
        partially_supported_topics=[],
        unsupported_topics=[
            UnsupportedTopic(
                topic="Remote grid breaker tripping",
                reason="Substation breaker controls require SCADA level-4 hardline authorization.",
                absence_nature="unsupported_capability",
                confidence_score=0.99
            ),
            UnsupportedTopic(
                topic="Corporate executive salaries",
                reason="Executive compensation is not included in wind turbine technical manuals.",
                absence_nature="missing_from_corpus",
                confidence_score=0.98
            )
        ],
        document_coverage_map={
            "turbine_scada_specs.pdf": ["Gearbox operating temperatures", "Emergency yaw braking"],
            "maintenance_intervals.pdf": ["Blade inspection intervals"]
        },
        refusal_recommendations=[
            "Refuse grid trip execution commands.",
            "Refuse corporate compensation queries."
        ],
        sanitized_answerable_topics=[
            "Gearbox operating temperatures",
            "Blade inspection intervals",
            "Emergency yaw braking"
        ],
        overall_groundability_score=0.88
    )

def test_adaptive_chunk_size_and_overlap_selection(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify that chunk size and overlap adapt dynamically based on document characteristics (CSV vs PDF vs mixed)."""
    generator = AgentGenerator(llm_client=MockLLMClient())

    # Case A: Pure Tabular CSV collection
    csv_dir = tmp_path / "csv_docs"
    csv_dir.mkdir()
    (csv_dir / "sensor_data.csv").write_text("id,turbine_id,rpm,vibration\n1,WTG-01,14.2,0.03\n2,WTG-02,15.1,0.04\n")
    csv_inventory = [DocumentItem(filename="sensor_data.csv", format="CSV", record_count=2)]
    chars_csv = generator.analyze_document_characteristics(str(csv_dir), csv_inventory)
    assert chars_csv["adaptive_chunk_size"] <= 350
    assert chars_csv["adaptive_chunk_overlap"] < chars_csv["adaptive_chunk_size"]

    # Case B: Standard Technical PDF collection
    pdf_dir = tmp_path / "pdf_docs"
    pdf_dir.mkdir()
    pdf_inventory = [
        DocumentItem(filename="manual1.pdf", format="PDF", page_count=5),
        DocumentItem(filename="manual2.pdf", format="PDF", page_count=3)
    ]
    chars_pdf = generator.analyze_document_characteristics(str(pdf_dir), pdf_inventory)
    assert chars_pdf["adaptive_chunk_size"] == 500
    assert chars_pdf["adaptive_chunk_overlap"] == 100

    # Case C: Mixed Tabular + PDF collection
    mixed_dir = tmp_path / "mixed_docs"
    mixed_dir.mkdir()
    mixed_inventory = [
        DocumentItem(filename="specs.pdf", format="PDF", page_count=2),
        DocumentItem(filename="readings.csv", format="CSV", record_count=100)
    ]
    chars_mixed = generator.analyze_document_characteristics(str(mixed_dir), mixed_inventory)
    assert chars_mixed["adaptive_chunk_size"] == 400
    assert chars_mixed["is_heterogeneous"] is True

def test_configurable_embedding_model_and_env_override(tmp_path, monkeypatch, wind_turbine_requirements, wind_turbine_groundability):
    """Verify configurable embedding model defaults and honors FORGEAI_EMBEDDING_MODEL environment variable."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()

    # Default model
    chars = generator.analyze_document_characteristics(str(doc_dir), wind_turbine_requirements.document_inventory)
    assert chars["embedding_model"] == "all-MiniLM-L6-v2"

    # Override via environment variable
    monkeypatch.setenv("FORGEAI_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    chars_override = generator.analyze_document_characteristics(str(doc_dir), wind_turbine_requirements.document_inventory)
    assert chars_override["embedding_model"] == "BAAI/bge-small-en-v1.5"

def test_configurable_retrieval_top_k_and_similarity_threshold(tmp_path):
    """Verify adaptive top_k and similarity threshold based on document collection count and heterogeneity."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()

    # Small collection (2 docs)
    small_inv = [
        DocumentItem(filename="doc1.pdf", format="PDF"),
        DocumentItem(filename="doc2.pdf", format="PDF")
    ]
    chars_small = generator.analyze_document_characteristics(str(doc_dir), small_inv)
    assert chars_small["adaptive_top_k"] == 3
    assert chars_small["adaptive_similarity_threshold"] == 0.32

    # Large heterogeneous collection (5 docs with PDF + CSV)
    large_inv = [
        DocumentItem(filename=f"doc_{i}.pdf", format="PDF") for i in range(4)
    ] + [DocumentItem(filename="data.csv", format="CSV")]
    chars_large = generator.analyze_document_characteristics(str(doc_dir), large_inv)
    assert chars_large["adaptive_top_k"] == 5
    assert chars_large["adaptive_similarity_threshold"] == 0.38

def test_optional_reranking_configuration(tmp_path):
    """Verify reranking configuration is enabled for multi-document collections and disabled for minimal collections."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()

    # 1 doc -> Reranking disabled (unnecessary overhead)
    inv_single = [DocumentItem(filename="single.pdf", format="PDF")]
    chars_single = generator.analyze_document_characteristics(str(doc_dir), inv_single)
    assert chars_single["reranking_config"].enabled is False

    # 4 docs -> Reranking enabled
    inv_multi = [DocumentItem(filename=f"part_{i}.pdf", format="PDF") for i in range(4)]
    chars_multi = generator.analyze_document_characteristics(str(doc_dir), inv_multi)
    assert chars_multi["reranking_config"].enabled is True
    assert chars_multi["reranking_config"].method == "cross_encoder"
    assert chars_multi["reranking_config"].top_n >= 1

def test_metadata_aware_retrieval_configuration(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify metadata configuration tracks source and page information with citation format."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()

    agent_def = generator.generate_agent(
        requirements=wind_turbine_requirements,
        groundability=wind_turbine_groundability,
        doc_folder=str(doc_dir)
    )

    assert isinstance(agent_def.metadata_config, MetadataConfig)
    assert "source" in agent_def.metadata_config.tracked_fields
    assert "page" in agent_def.metadata_config.tracked_fields
    assert agent_def.metadata_config.include_in_context is True
    assert "Page" in agent_def.metadata_config.citation_metadata_format

def test_dynamic_tool_selection_and_justification(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify that tools are dynamically selected from the registry with non-empty necessity justifications."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()

    tools, justifications = generator.determine_tool_selection_and_justifications(
        requirements=wind_turbine_requirements,
        doc_folder=str(doc_dir),
        inventory=wind_turbine_requirements.document_inventory
    )

    assert "calculator" in tools
    assert "current_date" in tools
    # csv_lookup should NOT be selected because there are no CSV files in inventory or folder
    assert "csv_lookup" not in tools

    assert "calculator" in justifications
    assert len(justifications["calculator"]) > 10
    assert "current_date" in justifications
    assert len(justifications["current_date"]) > 10

def test_validation_stage_rejects_irrelevant_tools(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify validation stage strips irrelevant tools and rejects invalid tools not in registry."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()

    # Intentionally craft an agent definition with an irrelevant tool (csv_lookup when no CSV exists)
    agent_def = generator.generate_agent(
        requirements=wind_turbine_requirements,
        groundability=wind_turbine_groundability,
        doc_folder=str(doc_dir)
    )

    # Force inject irrelevant tool and invalid tool
    agent_def.tool_selection.append("csv_lookup")
    agent_def.tool_justifications["csv_lookup"] = "Injected without CSV"

    # Run validation stage: csv_lookup must be removed because no CSV exists on disk or inventory
    generator.validate_agent_definition(agent_def, wind_turbine_requirements, str(doc_dir))
    assert "csv_lookup" not in agent_def.tool_selection
    assert "csv_lookup" not in agent_def.tool_justifications

    # Unknown tool not in registry must raise ValueError
    agent_def.tool_selection.append("fake_unregistered_tool")
    with pytest.raises(ValueError, match="not registered in the tool registry"):
        generator.validate_agent_definition(agent_def, wind_turbine_requirements, str(doc_dir))

def test_validation_stage_enforces_groundability_and_chunk_parameters(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify validation stage rejects invalid chunk overlap and ensures unsupported topics are never answerable."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()

    agent_def = generator.generate_agent(
        requirements=wind_turbine_requirements,
        groundability=wind_turbine_groundability,
        doc_folder=str(doc_dir)
    )

    # Overlap >= chunk size must raise ValueError
    agent_def.chunk_overlap = agent_def.chunk_size
    with pytest.raises(ValueError, match="Invalid chunk_overlap"):
        generator.validate_agent_definition(agent_def, wind_turbine_requirements, str(doc_dir))

    # Reset valid overlap
    agent_def.chunk_overlap = 80

    # Ensure unsupported topics cannot enter supported_topics
    agent_def.supported_topics.append("Remote grid breaker tripping")
    generator.validate_agent_definition(agent_def, wind_turbine_requirements, str(doc_dir))
    assert "Remote grid breaker tripping" not in agent_def.supported_topics
    assert "Remote grid breaker tripping" in agent_def.must_refuse_topics

def test_dynamic_system_prompt_and_strict_refusals(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify that dynamic system prompt includes mission, domain, constraints, grounded topics, and strict refusal rules."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()

    agent_def = generator.generate_agent(
        requirements=wind_turbine_requirements,
        groundability=wind_turbine_groundability,
        doc_folder=str(doc_dir)
    )

    prompt = agent_def.system_prompt
    assert "Turbine Operations Assistant" in prompt
    assert "Renewable Wind Energy Systems" in prompt
    assert "STRICT REFUSAL" in prompt
    assert "Remote grid breaker tripping" in prompt
    assert "Corporate executive salaries" in prompt
    assert agent_def.output_contract.refusal_phrase in prompt
    assert agent_def.citation_requirements.format in prompt

def test_full_agent_definition_persisted_to_json(tmp_path, wind_turbine_requirements, wind_turbine_groundability):
    """Verify that agent definition serializes completely to agent_definition.json and can be reloaded."""
    generator = AgentGenerator(llm_client=MockLLMClient())
    doc_dir = tmp_path / "turbine_docs"
    doc_dir.mkdir()
    out_file = str(tmp_path / "artifacts" / "agent_definition.json")

    agent_def = generator.generate_agent(
        requirements=wind_turbine_requirements,
        groundability=wind_turbine_groundability,
        doc_folder=str(doc_dir)
    )
    generator.save_definition(agent_def, out_file)

    assert os.path.exists(out_file)
    with open(out_file, "r") as f:
        data = json.load(f)

    # Validate all 10 requirements stored in agent_definition.json
    assert data["agent_name"] == "Turbine Operations Assistant"
    assert "chunk_size" in data
    assert "chunk_overlap" in data
    assert "embedding_model" in data
    assert "top_k" in data
    assert "similarity_threshold" in data
    assert "metadata_config" in data
    assert "reranking_config" in data
    assert "tool_selection" in data
    assert "tool_justifications" in data
    assert "output_contract" in data
    assert "citation_requirements" in data
    assert "refusal_policy" in data

    # Reconstruct from saved file
    reloaded = AgentDefinition(**data)
    assert reloaded.agent_name == agent_def.agent_name
    assert reloaded.tool_justifications == agent_def.tool_justifications
