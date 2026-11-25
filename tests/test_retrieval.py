import os
import pytest
import pandas as pd
from app.retrieval import DocumentLoader, Chunker, RawDocument, FAISSRetriever

def test_document_loader_txt(tmp_path):
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("This is a sample document for testing retrieval pipeline.", encoding="utf-8")

    docs = DocumentLoader.load_file(str(txt_file))
    assert len(docs) == 1
    assert docs[0].source == "sample.txt"
    assert "testing retrieval pipeline" in docs[0].content
    assert docs[0].file_type == "txt"

def test_document_loader_csv(tmp_path):
    csv_file = tmp_path / "catalog.csv"
    df = pd.DataFrame([
        {"id": 1, "item": "Pump", "price": 100},
        {"id": 2, "item": "Valve", "price": 50}
    ])
    df.to_csv(str(csv_file), index=False)

    docs = DocumentLoader.load_file(str(csv_file))
    assert len(docs) >= 1
    assert docs[0].source == "catalog.csv"
    assert docs[0].file_type == "csv"
    assert "Pump" in docs[0].content

def test_chunker_metadata_preservation():
    docs = [
        RawDocument(
            content="Paragraph one with information.\n\nParagraph two with distinct details.",
            source="manual.pdf",
            page=2,
            file_type="pdf",
            metadata={"custom_key": "val"}
        )
    ]
    chunker = Chunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk_documents(docs)

    assert len(chunks) >= 2
    for c in chunks:
        assert c.source == "manual.pdf"
        assert c.page == 2
        assert c.file_type == "pdf"
        assert c.metadata.get("custom_key") == "val"

def test_faiss_retriever_indexing_and_search(tmp_path):
    docs = [
        RawDocument(content="The annual leave entitlement is 20 days.", source="leave.pdf", page=1, file_type="pdf"),
        RawDocument(content="Office business hours are 8:30 AM to 5:30 PM.", source="hours.pdf", page=1, file_type="pdf")
    ]
    retriever = FAISSRetriever(chunk_size=100, chunk_overlap=20, top_k=2, similarity_threshold=0.2)
    indexed_count = retriever.index_documents(docs)
    assert indexed_count == 2

    # Query matching first document
    results = retriever.retrieve("annual leave days")
    assert len(results) >= 1
    assert results[0].source == "leave.pdf"
    assert "20 days" in results[0].content

    # Save and reload index
    save_dir = str(tmp_path / "index_store")
    retriever.save(save_dir)

    new_retriever = FAISSRetriever()
    loaded = new_retriever.load(save_dir)
    assert loaded is True
    reloaded_results = new_retriever.retrieve("office hours")
    assert len(reloaded_results) >= 1
    assert reloaded_results[0].source == "hours.pdf"
