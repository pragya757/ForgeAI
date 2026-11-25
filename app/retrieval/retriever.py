import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.retrieval.document_loader import DocumentLoader, RawDocument
from app.retrieval.chunker import Chunker, Chunk
from app.retrieval.embeddings import EmbeddingModel

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    source: str
    page: Optional[int] = None
    file_type: str
    score: float
    metadata: Dict[str, Any] = {}

class FAISSRetriever:
    """FAISS-based dense vector retriever with source metadata preservation and threshold filtering."""

    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        top_k: int = 4,
        similarity_threshold: float = 0.35,
    ):
        self.embedding_model_name = embedding_model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

        self.embedder = EmbeddingModel(model_name=embedding_model_name)
        self.index: Optional[faiss.Index] = None
        self.chunks: List[Chunk] = []

    def index_documents(self, documents: List[RawDocument]) -> int:
        """Chunk documents, compute embeddings, and build the FAISS index."""
        chunker = Chunker(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        self.chunks = chunker.chunk_documents(documents)

        if not self.chunks:
            # Empty index
            dim = self.embedder.dimension
            self.index = faiss.IndexFlatIP(dim)
            return 0

        texts = [c.content for c in self.chunks]
        embeddings = self.embedder.encode(texts)

        # Normalize for Inner Product (Cosine Similarity)
        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        return len(self.chunks)

    def index_directory(self, dir_path: str) -> int:
        """Load directory and build FAISS index."""
        docs = DocumentLoader.load_directory(dir_path)
        return self.index_documents(docs)

    def retrieve(self, query: str, top_k: Optional[int] = None, threshold: Optional[float] = None) -> List[SearchResult]:
        """Retrieve most relevant chunks for query with score filtering."""
        if self.index is None or len(self.chunks) == 0:
            return []

        k = top_k or self.top_k
        k = min(k, len(self.chunks))
        thresh = threshold if threshold is not None else self.similarity_threshold

        query_emb = self.embedder.encode([query])
        faiss.normalize_L2(query_emb)

        scores, indices = self.index.search(query_emb, k)

        results: List[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            # Cosine similarity score range [-1, 1]
            float_score = float(score)
            if float_score >= thresh:
                c = self.chunks[idx]
                results.append(SearchResult(
                    chunk_id=c.chunk_id,
                    content=c.content,
                    source=c.source,
                    page=c.page,
                    file_type=c.file_type,
                    score=round(float_score, 4),
                    metadata=c.metadata
                ))

        return results

    def save(self, directory: str) -> None:
        """Persist index and metadata to disk."""
        os.makedirs(directory, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, os.path.join(directory, "faiss.index"))
        chunks_data = [c.model_dump() for c in self.chunks]
        with open(os.path.join(directory, "chunks.json"), "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2)

    def load(self, directory: str) -> bool:
        """Load persisted index and metadata."""
        idx_path = os.path.join(directory, "faiss.index")
        chunks_path = os.path.join(directory, "chunks.json")
        if not (os.path.exists(idx_path) and os.path.exists(chunks_path)):
            return False

        self.index = faiss.read_index(idx_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)
        self.chunks = [Chunk(**c) for c in chunks_data]
        return True
