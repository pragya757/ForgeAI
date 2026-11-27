from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

class OutputContract(BaseModel):
    format: str = "markdown"
    require_citations: bool = True
    citation_format: Optional[str] = "[Source: <document_name>, Page: <page>]"
    refusal_phrase: str = "I cannot answer this question as it is outside my verified documentation scope."
    section_headers: Optional[List[str]] = None
    disclaimer: Optional[str] = None

class CitationRequirements(BaseModel):
    must_cite: bool = True
    format: str = "[Source: <filename>, Page: <page>]"
    granularity: str = "sentence_level"  # sentence_level, paragraph_level, claim_level
    prohibit_unanchored_claims: bool = True

class ModelConfig(BaseModel):
    temperature: float = 0.1
    max_tokens: int = 1024
    model_name: Optional[str] = None

class RerankingConfig(BaseModel):
    enabled: bool = False
    method: str = "cross_encoder"  # cross_encoder, reciprocal_rank_fusion, heuristic_boost
    top_n: int = 3
    model_name: Optional[str] = "cross-encoder/ms-marco-MiniLM-L-6-v2"

class MetadataConfig(BaseModel):
    tracked_fields: List[str] = Field(default_factory=lambda: ["source", "page", "file_type", "total_pages"])
    include_in_context: bool = True
    citation_metadata_format: str = "[Source: <source>, Page: <page>]"

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
    corpus_directory: Optional[str] = None
    indexed_documents: List[str] = Field(default_factory=list)
    chunk_size: int = 500
    chunk_overlap: int = 100
    embedding_model: str = "all-MiniLM-L6-v2"
    retrieval_method: str = "dense_vector_faiss"
    top_k: int = 4
    similarity_threshold: float = 0.35
    reranking_config: Optional[Union[RerankingConfig, Dict[str, Any]]] = None
    metadata_config: MetadataConfig = Field(default_factory=MetadataConfig)
    tool_selection: List[str] = Field(default_factory=list)
    tool_justifications: Dict[str, str] = Field(default_factory=dict)
    output_contract: OutputContract = Field(default_factory=OutputContract)
    citation_requirements: CitationRequirements = Field(default_factory=CitationRequirements)
    refusal_policy: str
    llm_config: ModelConfig = Field(default_factory=ModelConfig, alias="model_config")
