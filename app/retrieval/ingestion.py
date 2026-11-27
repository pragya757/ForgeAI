import os
import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv", ".md"}

class DocumentMetadata(BaseModel):
    """Metadata for an ingested document in the session corpus."""
    filename: str
    format: str
    size_bytes: int
    sha256: str
    file_path: str
    created_at: str

class IngestionResult(BaseModel):
    """Result of an ingestion operation with isolated paths and manifest."""
    session_id: str
    document_dir: str
    artifacts_dir: str
    manifest_path: str
    documents: List[DocumentMetadata]
    total_files: int
    total_bytes: int

class IngestionManager:
    """
    Universal Document Ingestion Manager
    - Handles arbitrary document uploads across PDF, TXT, CSV, and Markdown.
    - Validates file formats and guards against empty or corrupted files.
    - Generates isolated, collision-proof session directories per agent build.
    - Computes SHA-256 hashes for provenance and auditability.
    - Maintains a persistent `corpus_manifest.json` for each corpus.
    """

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal or invalid characters."""
        base = os.path.basename(filename.strip().replace("\\", "/"))
        # Strip illegal characters but preserve dots, underscores, dashes
        clean = "".join(c for c in base if c.isalnum() or c in "._- ")
        if not clean or clean.startswith("."):
            clean = f"document_{uuid.uuid4().hex[:6]}{os.path.splitext(base)[1]}"
        return clean

    @staticmethod
    def validate_file(filename: str, content: bytes) -> str:
        """Validate filename extension and non-empty content."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file format '{ext}' for file '{filename}'. Supported: {allowed}")

        if len(content) == 0:
            raise ValueError(f"Uploaded file '{filename}' is empty (0 bytes).")

        return ext

    @classmethod
    def create_session(
        cls,
        session_id: Optional[str] = None,
        base_dir: str = "outputs/sessions"
    ) -> Tuple[str, str, str]:
        """Create isolated session directories for documents and artifacts."""
        if not session_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:8]
            session_id = f"session_{timestamp}_{short_uuid}"

        session_root = os.path.join(base_dir, session_id)
        doc_dir = os.path.join(session_root, "documents")
        artifacts_dir = os.path.join(session_root, "artifacts")

        os.makedirs(doc_dir, exist_ok=True)
        os.makedirs(artifacts_dir, exist_ok=True)

        return session_id, doc_dir, artifacts_dir

    @classmethod
    def ingest_files(
        cls,
        files: List[Any],
        session_id: Optional[str] = None,
        base_dir: str = "outputs/sessions"
    ) -> IngestionResult:
        """
        Ingest arbitrary files (tuples of (name, bytes), file-like objects, or FastAPI UploadFiles).
        Stores files in an isolated session directory and writes corpus_manifest.json.
        """
        if not files:
            raise ValueError("No files provided for document ingestion.")

        session_id, doc_dir, artifacts_dir = cls.create_session(session_id=session_id, base_dir=base_dir)

        doc_meta_list: List[DocumentMetadata] = []
        total_bytes = 0

        for file_item in files:
            # Extract filename and bytes across different interfaces
            if isinstance(file_item, tuple) and len(file_item) == 2:
                name, raw_bytes = file_item
                if hasattr(raw_bytes, "read"):
                    raw_bytes = raw_bytes.read()
            elif hasattr(file_item, "name") and hasattr(file_item, "read"):
                name = file_item.name
                raw_bytes = file_item.read()
            elif hasattr(file_item, "filename") and hasattr(file_item, "file"):
                # FastAPI UploadFile
                name = file_item.filename
                raw_bytes = file_item.file.read()
            elif hasattr(file_item, "name") and hasattr(file_item, "getbuffer"):
                # Streamlit UploadedFile
                name = file_item.name
                raw_bytes = bytes(file_item.getbuffer())
            else:
                raise TypeError(f"Unsupported file item type: {type(file_item)}")

            clean_name = cls.sanitize_filename(name)
            ext = cls.validate_file(clean_name, raw_bytes)

            file_dest = os.path.join(doc_dir, clean_name)
            with open(file_dest, "wb") as f:
                f.write(raw_bytes)

            sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
            size = len(raw_bytes)
            total_bytes += size

            doc_meta_list.append(DocumentMetadata(
                filename=clean_name,
                format=ext.replace(".", "").upper(),
                size_bytes=size,
                sha256=sha256_hash,
                file_path=os.path.abspath(file_dest),
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        manifest = {
            "session_id": session_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_documents": len(doc_meta_list),
            "total_bytes": total_bytes,
            "document_directory": os.path.abspath(doc_dir),
            "artifacts_directory": os.path.abspath(artifacts_dir),
            "documents": [d.model_dump() for d in doc_meta_list]
        }

        manifest_path = os.path.join(doc_dir, "corpus_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return IngestionResult(
            session_id=session_id,
            document_dir=os.path.abspath(doc_dir),
            artifacts_dir=os.path.abspath(artifacts_dir),
            manifest_path=os.path.abspath(manifest_path),
            documents=doc_meta_list,
            total_files=len(doc_meta_list),
            total_bytes=total_bytes
        )

    @classmethod
    def load_manifest(cls, doc_dir: str) -> Optional[Dict[str, Any]]:
        """Load manifest from a document directory if present."""
        manifest_path = os.path.join(doc_dir, "corpus_manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
