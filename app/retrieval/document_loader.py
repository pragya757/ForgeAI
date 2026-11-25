import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pymupdf
import pandas as pd

class RawDocument(BaseModel):
    content: str
    source: str
    page: Optional[int] = None
    file_type: str
    metadata: Dict[str, Any] = {}

class DocumentLoader:
    """Extracts text and metadata from PDF, TXT, CSV, MD documents."""

    @staticmethod
    def load_file(file_path: str) -> List[RawDocument]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        docs: List[RawDocument] = []

        if ext == ".pdf":
            try:
                pdf_doc = pymupdf.open(file_path)
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc[page_num]
                    text = page.get_text() or ""
                    if text.strip():
                        docs.append(RawDocument(
                            content=text.strip(),
                            source=filename,
                            page=page_num + 1,
                            file_type="pdf",
                            metadata={"total_pages": len(pdf_doc), "page": page_num + 1}
                        ))
                pdf_doc.close()
            except Exception as e:
                raise RuntimeError(f"Error reading PDF {filename}: {str(e)}")

        elif ext in (".txt", ".md"):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if text.strip():
                    docs.append(RawDocument(
                        content=text.strip(),
                        source=filename,
                        page=1,
                        file_type=ext.replace(".", ""),
                        metadata={"size_bytes": os.path.getsize(file_path)}
                    ))
            except Exception as e:
                raise RuntimeError(f"Error reading text file {filename}: {str(e)}")

        elif ext == ".csv":
            try:
                df = pd.read_csv(file_path)
                records = df.to_dict(orient="records")
                # Group records into chunks of 5 rows for better context
                batch_size = 5
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    lines = []
                    for idx, r in enumerate(batch, start=i + 1):
                        row_str = ", ".join([f"{k}: {v}" for k, v in r.items() if pd.notna(v)])
                        lines.append(f"[Row {idx}] {row_str}")
                    text = "\n".join(lines)
                    docs.append(RawDocument(
                        content=text,
                        source=filename,
                        page=i // batch_size + 1,
                        file_type="csv",
                        metadata={"row_start": i + 1, "row_end": min(i + batch_size, len(records)), "total_rows": len(df)}
                    ))
            except Exception as e:
                raise RuntimeError(f"Error reading CSV {filename}: {str(e)}")

        return docs

    @staticmethod
    def load_directory(dir_path: str) -> List[RawDocument]:
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        supported_exts = {".pdf", ".txt", ".csv", ".md"}
        all_docs: List[RawDocument] = []

        for root, _, files in os.walk(dir_path):
            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_exts:
                    full_path = os.path.join(root, file)
                    docs = DocumentLoader.load_file(full_path)
                    all_docs.extend(docs)

        return all_docs
