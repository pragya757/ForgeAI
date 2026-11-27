import os
import json
import pytest
import pymupdf
from fastapi.testclient import TestClient

from app.retrieval.ingestion import IngestionManager, IngestionResult, SUPPORTED_EXTENSIONS
from app.retrieval.document_loader import DocumentLoader
from app.schemas.requirements import Requirements, DocumentItem
from app.schemas.groundability import GroundabilityReport, SupportedTopic
from app.schemas.agent_definition import AgentDefinition
from app.factory.agent_generator import AgentGenerator
from app.runtime.chat_runner import GenericChatRunner
from app.main import app

def create_sample_pdf(filepath: str, text: str = "Sample PDF Policy Document"):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    doc.save(filepath)
    doc.close()

def test_ingestion_manager_supported_formats(tmp_path):
    base_dir = str(tmp_path / "sessions")
    
    # 1. Prepare sample files: PDF, TXT, CSV, MD
    pdf_path = str(tmp_path / "policy.pdf")
    create_sample_pdf(pdf_path, "Standard Operating Procedures for Flight Operations.")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    txt_bytes = b"Section 1: General Conduct. All personnel must wear badges."
    csv_bytes = b"part_id,name,price\n101,gyroscope,450.00\n102,accelerometer,210.50"
    md_bytes = b"# Flight Manual\n## Section 2: Preflight Checklist\n- Check avionics\n- Verify fuel"

    files = [
        ("flight_ops.pdf", pdf_bytes),
        ("conduct.txt", txt_bytes),
        ("telemetry_parts.csv", csv_bytes),
        ("manual.md", md_bytes)
    ]

    result = IngestionManager.ingest_files(files, base_dir=base_dir)

    assert result.session_id.startswith("session_")
    assert result.total_files == 4
    assert result.total_bytes == len(pdf_bytes) + len(txt_bytes) + len(csv_bytes) + len(md_bytes)
    assert os.path.exists(result.manifest_path)

    # Verify files exist in document_dir
    for name, _ in files:
        assert os.path.exists(os.path.join(result.document_dir, name))

    # Verify manifest structure
    with open(result.manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["total_documents"] == 4
    assert len(manifest["documents"]) == 4
    
    formats = {d["format"] for d in manifest["documents"]}
    assert formats == {"PDF", "TXT", "CSV", "MD"}
    
    for d in manifest["documents"]:
        assert len(d["sha256"]) == 64  # valid SHA-256 length

def test_ingestion_manager_validation_empty_and_unsupported(tmp_path):
    base_dir = str(tmp_path / "sessions")

    # Empty file
    with pytest.raises(ValueError, match="is empty"):
        IngestionManager.ingest_files([("empty.txt", b"")], base_dir=base_dir)

    # Unsupported format (.exe, .zip)
    with pytest.raises(ValueError, match="Unsupported file format"):
        IngestionManager.ingest_files([("script.exe", b"binarycontent")], base_dir=base_dir)

    with pytest.raises(ValueError, match="Unsupported file format"):
        IngestionManager.ingest_files([("archive.zip", b"PK\x03\x04zipcontent")], base_dir=base_dir)

def test_session_isolation_two_consecutive_builds(tmp_path):
    base_dir = str(tmp_path / "sessions")

    # Session 1: Aviation Domain
    files_a = [
        ("avionics.txt", b"Avionics specification document content"),
        ("radar.md", b"# Radar Protocols\nMaintain 5 nautical mile separation.")
    ]
    res_a = IngestionManager.ingest_files(files_a, session_id="build_aviation_001", base_dir=base_dir)

    # Session 2: Renewable Energy Domain
    files_b = [
        ("wind_turbine.txt", b"Turbine rotation limits: 25 RPM max."),
        ("solar_grid.csv", b"inverter_id,voltage\nINV-1,480\nINV-2,480")
    ]
    res_b = IngestionManager.ingest_files(files_b, session_id="build_solar_002", base_dir=base_dir)

    # Verify distinct directories
    assert res_a.document_dir != res_b.document_dir
    assert res_a.artifacts_dir != res_b.artifacts_dir

    # Verify zero document leakage
    docs_a = os.listdir(res_a.document_dir)
    docs_b = os.listdir(res_b.document_dir)

    assert "avionics.txt" in docs_a
    assert "radar.md" in docs_a
    assert "wind_turbine.txt" not in docs_a
    assert "solar_grid.csv" not in docs_a

    assert "wind_turbine.txt" in docs_b
    assert "solar_grid.csv" in docs_b
    assert "avionics.txt" not in docs_b
    assert "radar.md" not in docs_b

def test_agent_definition_persists_and_loads_corpus_metadata(tmp_path):
    # Create a custom corpus
    doc_dir = str(tmp_path / "astronomy_docs")
    os.makedirs(doc_dir, exist_ok=True)
    with open(os.path.join(doc_dir, "telescope_protocol.txt"), "w") as f:
        f.write("Telescope calibration must be completed 30 minutes before astronomical twilight.\nTarget coordinates: RA 12h, Dec +45.")

    generator = AgentGenerator()
    reqs = Requirements(
        agent_name="Observatory Operations Assistant",
        domain="Astronomy & Space Science",
        purpose="Assist astronomers with telescope calibration and observation schedules.",
        target_audience="Staff astronomers and visiting researchers",
        scope="Telescope calibration and twilight observation guidelines",
        tone="Scientific, precise, and objective",
        must_answer_topics=["Telescope calibration", "Twilight schedules"],
        must_refuse_topics=["Military defense satellites"],
        required_tools=["current_date"],
        assumptions=["Observers have valid observation time allocations"],
        ambiguities=[],
        unsupported_requirements=[],
        document_inventory=[
            DocumentItem(
                filename="telescope_protocol.txt",
                format="TXT",
                description="Observation guidelines",
                detected_topics=["Telescope calibration"]
            )
        ]
    )
    ground = GroundabilityReport(
        overall_groundability_score=0.95,
        supported_topics=[
            SupportedTopic(
                topic="Telescope calibration",
                evidence_sources=["telescope_protocol.txt"],
                coverage_summary="Documented in protocol."
            )
        ],
        unsupported_topics=[],
        sanitized_answerable_topics=["Telescope calibration"]
    )

    agent_def = generator.generate_agent(requirements=reqs, groundability=ground, doc_folder=doc_dir)

    # Verify corpus metadata is embedded
    assert agent_def.corpus_directory == os.path.abspath(doc_dir)
    assert "telescope_protocol.txt" in agent_def.indexed_documents

    # Verify GenericChatRunner loads corpus directly from definition without passing doc_folder
    runner = GenericChatRunner(definition=agent_def)
    assert runner.doc_folder == os.path.abspath(doc_dir)
    assert len(runner.retriever.chunks) > 0

    # Test an answerable query
    resp = runner.ask("When must telescope calibration be completed?")
    assert "twilight" in resp.answer.lower() or "calibration" in resp.answer.lower()

def test_fastapi_multipart_upload_and_build_endpoint(tmp_path):
    client = TestClient(app)

    txt_content = b"Harbor Logistics Policy: Container dwell time is capped at 5 calendar days before demurrage penalties apply."
    csv_content = b"dock_id,max_draft_meters,crane_count\nDK-1,14.5,4\nDK-2,12.0,2"

    response = client.post(
        "/api/factory/upload-and-build",
        data={
            "brief": "Create a harbor logistics assistant that answers shipping line inquiries about container dwell times and berth specifications using dock policy documents.",
            "iterations": 1
        },
        files=[
            ("files", ("harbor_dwell_policy.txt", txt_content, "text/plain")),
            ("files", ("dock_specs.csv", csv_content, "text/csv"))
        ]
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "success"
    assert "session_id" in data
    assert "agent_name" in data
    assert "Harbor" in data["agent_name"] or "Logistics" in data["agent_name"] or "Assistant" in data["agent_name"]
    assert "harbor_dwell_policy.txt" in data["documents_ingested"]
    assert "dock_specs.csv" in data["documents_ingested"]
    assert os.path.exists(data["manifest_path"])
    assert os.path.exists(data["agent_definition_path"])

def test_fastapi_multipart_upload_validation_errors():
    client = TestClient(app)

    # 1. Empty brief
    resp1 = client.post(
        "/api/factory/upload-and-build",
        data={"brief": ""},
        files=[("files", ("sample.txt", b"valid text content", "text/plain"))]
    )
    assert resp1.status_code in [400, 422]

    # 2. Unsupported file type
    resp2 = client.post(
        "/api/factory/upload-and-build",
        data={"brief": "Create an assistant for binary files."},
        files=[("files", ("exploit.exe", b"MZ\x90binary", "application/octet-stream"))]
    )
    assert resp2.status_code == 400
    assert "unsupported file format" in resp2.json()["detail"].lower()

    # 3. Empty file content
    resp3 = client.post(
        "/api/factory/upload-and-build",
        data={"brief": "Create an assistant for empty docs."},
        files=[("files", ("empty_file.txt", b"", "text/plain"))]
    )
    assert resp3.status_code == 400
    assert "is empty" in resp3.json()["detail"].lower()
