import os
from typing import Optional
from pydantic import BaseModel, Field

class Settings(BaseModel):
    # LLM Settings
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    ollama_base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"))
    
    # OpenAI compatible settings
    openai_api_base: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_BASE"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    # Resilience & Networking Settings
    llm_request_timeout: int = Field(default_factory=lambda: int(os.getenv("LLM_REQUEST_TIMEOUT", "60")))
    llm_max_retries: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", "3")))
    llm_retry_delay: float = Field(default_factory=lambda: float(os.getenv("LLM_RETRY_DELAY", "1.0")))
    
    # Retrieval defaults
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    default_chunk_size: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_CHUNK_SIZE", "500")))
    default_chunk_overlap: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_CHUNK_OVERLAP", "100")))
    default_top_k: int = Field(default_factory=lambda: int(os.getenv("DEFAULT_TOP_K", "4")))
    default_similarity_threshold: float = Field(default_factory=lambda: float(os.getenv("DEFAULT_SIMILARITY_THRESHOLD", "0.35")))
    
    # Factory optimization
    max_optimization_iterations: int = Field(default_factory=lambda: int(os.getenv("MAX_OPTIMIZATION_ITERATIONS", "3")))
    eval_sample_target: int = Field(default_factory=lambda: int(os.getenv("EVAL_SAMPLE_TARGET", "20")))

settings = Settings()
