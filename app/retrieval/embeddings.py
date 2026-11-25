import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
import numpy as np
from typing import List

class EmbeddingModel:
    """Wrapper around SentenceTransformer with macOS thread safety and fallback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dim = 384

    def _load_model(self):
        if self._model is None:
            try:
                import torch
                torch.set_num_threads(1)
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device="cpu")
                # Handle method rename in latest sentence_transformers
                if hasattr(self._model, "get_embedding_dimension"):
                    self._dim = self._model.get_embedding_dimension()
                elif hasattr(self._model, "get_sentence_embedding_dimension"):
                    self._dim = self._model.get_sentence_embedding_dimension()
                else:
                    self._dim = 384
            except Exception as e:
                # Deterministic fallback
                self._model = "fallback"
                self._dim = 384

    @property
    def dimension(self) -> int:
        self._load_model()
        return self._dim

    def encode(self, texts: List[str]) -> np.ndarray:
        self._load_model()
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        if self._model != "fallback":
            try:
                embeddings = self._model.encode(
                    texts,
                    device="cpu",
                    batch_size=4,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True
                )
                return np.ascontiguousarray(embeddings, dtype=np.float32)
            except Exception:
                pass

        # Deterministic feature hashing fallback
        vectors = []
        for t in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            words = t.lower().split()
            for w in words:
                h = abs(hash(w)) % self.dimension
                vec[h] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            vectors.append(vec)
        return np.ascontiguousarray(np.array(vectors), dtype=np.float32)
