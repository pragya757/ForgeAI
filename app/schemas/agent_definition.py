from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class OutputContract(BaseModel):
    format: str = "markdown"
    require_citations: bool = True
    citation_format: Optional[str] = "[Source: <document_name>]"
    refusal_phrase: Optional[str] = "I cannot answer this question as it is outside my verified documentation scope."

class CitationRequirements(BaseModel):
    must_cite: bool = True
    format: str = "[Source: <filename>]"

class ModelConfig(BaseModel):
    temperature: float = 0.1
    max_tokens: int = 1024
    model_name: Optional[str] = None

class AgentDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_name: str
    description: str
    system_prompt: str
    target_audience: str
    supported_topics: List[str]
    unsupported_topics: List[str]
    must_refuse_topics: List[str]
    document_references: List[str]
    chunk_size: int = 500
    chunk_overlap: int = 100
    embedding_model: str = "all-MiniLM-L6-v2"
    retrieval_method: str = "dense_vector_faiss"
    top_k: int = 4
    similarity_threshold: float = 0.35
    reranking_config: Optional[Dict[str, Any]] = None
    tool_selection: List[str] = Field(default_factory=list)
    output_contract: OutputContract = Field(default_factory=OutputContract)
    citation_requirements: CitationRequirements = Field(default_factory=CitationRequirements)
    refusal_policy: str
    llm_config: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
