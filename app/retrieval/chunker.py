from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.retrieval.document_loader import RawDocument

class Chunk(BaseModel):
    chunk_id: str
    content: str
    source: str
    page: Optional[int] = None
    file_type: str
    metadata: Dict[str, Any] = {}

class Chunker:
    """Splits documents into overlapping chunks while preserving sentence boundaries and source metadata."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_documents(self, documents: List[RawDocument]) -> List[Chunk]:
        chunks: List[Chunk] = []
        chunk_counter = 0

        for doc in documents:
            text = doc.content.strip()
            if not text:
                continue

            if len(text) <= self.chunk_size:
                chunk_counter += 1
                chunks.append(Chunk(
                    chunk_id=f"{doc.source}_p{doc.page or 1}_{chunk_counter}",
                    content=text,
                    source=doc.source,
                    page=doc.page,
                    file_type=doc.file_type,
                    metadata=doc.metadata
                ))
                continue

            # Split text by paragraphs, splitting long blocks on line boundaries
            raw_blocks = text.split("\n\n")
            paragraphs: List[str] = []
            for rb in raw_blocks:
                rb = rb.strip()
                if not rb:
                    continue
                if len(rb) > self.chunk_size and "\n" in rb:
                    lines = [l.strip() for l in rb.split("\n") if l.strip()]
                    paragraphs.extend(lines)
                else:
                    paragraphs.append(rb)

            current_chunk = ""

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    if current_chunk:
                        chunk_counter += 1
                        chunks.append(Chunk(
                            chunk_id=f"{doc.source}_p{doc.page or 1}_{chunk_counter}",
                            content=current_chunk,
                            source=doc.source,
                            page=doc.page,
                            file_type=doc.file_type,
                            metadata=doc.metadata
                        ))
                        # Retain overlap from end of previous chunk
                        if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                            current_chunk = current_chunk[-self.chunk_overlap:].strip() + " " + para
                        else:
                            current_chunk = para
                    else:
                        # Single paragraph exceeds chunk_size, split by characters/sentences
                        step = self.chunk_size - self.chunk_overlap
                        for i in range(0, len(para), step):
                            slice_text = para[i:i + self.chunk_size].strip()
                            if slice_text:
                                chunk_counter += 1
                                chunks.append(Chunk(
                                    chunk_id=f"{doc.source}_p{doc.page or 1}_{chunk_counter}",
                                    content=slice_text,
                                    source=doc.source,
                                    page=doc.page,
                                    file_type=doc.file_type,
                                    metadata=doc.metadata
                                ))
                        current_chunk = ""

            if current_chunk.strip():
                chunk_counter += 1
                chunks.append(Chunk(
                    chunk_id=f"{doc.source}_p{doc.page or 1}_{chunk_counter}",
                    content=current_chunk.strip(),
                    source=doc.source,
                    page=doc.page,
                    file_type=doc.file_type,
                    metadata=doc.metadata
                ))

        return chunks
