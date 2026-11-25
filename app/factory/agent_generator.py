import os
import json
from typing import Optional, Dict, Any, List
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.requirements import Requirements
from app.schemas.groundability import GroundabilityReport
from app.schemas.agent_definition import AgentDefinition, OutputContract, CitationRequirements, ModelConfig
from app.tools.registry import registry

class AgentGenerator:
    """Module 3: Agent Generator - Generates declarative, executable agent definitions."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def generate_agent(
        self,
        requirements: Requirements,
        groundability: GroundabilityReport,
        doc_folder: str
    ) -> AgentDefinition:
        """Create complete AgentDefinition incorporating groundability constraints."""
        available_tools = registry.list_tools()

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "agent_generator.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            requirements_json=requirements.model_dump_json(indent=2),
            groundability_json=groundability.model_dump_json(indent=2),
            available_tools=", ".join(available_tools)
        )

        response_text = self.llm.generate(
            prompt=prompt,
            json_mode=True,
            temperature=0.1
        )

        try:
            clean_json = response_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            data = json.loads(clean_json.strip())
        except Exception:
            # Deterministic fallback definition
            doc_refs = [d.filename for d in requirements.document_inventory]
            data = {
                "agent_name": requirements.agent_name,
                "description": requirements.purpose,
                "system_prompt": (
                    f"You are {requirements.agent_name}. Answer user questions strictly based on the provided context.\n"
                    "Always cite the source document name and page.\n"
                    "If the answer cannot be found or concerns unsupported topics, you MUST refuse to answer."
                ),
                "target_audience": requirements.target_audience,
                "supported_topics": [t.topic for t in groundability.supported_topics],
                "unsupported_topics": [t.topic for t in groundability.unsupported_topics],
                "must_refuse_topics": requirements.must_refuse_topics,
                "document_references": doc_refs,
                "chunk_size": 500,
                "chunk_overlap": 100,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 4,
                "similarity_threshold": 0.35,
                "reranking_config": None,
                "tool_selection": requirements.required_tools,
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>]",
                    "refusal_phrase": "I cannot answer this question as it is outside my verified documentation scope."
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>]"
                },
                "refusal_policy": "Strict refusal on ungrounded claims, confidential records, or unsupported capabilities.",
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }

        # Strict tool validation
        if "tool_selection" in data:
            data["tool_selection"] = registry.validate_selection(data["tool_selection"])

        # Validate with Pydantic
        agent_def = AgentDefinition(**data)
        return agent_def

    def save_definition(self, definition: AgentDefinition, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(definition.model_dump_json(indent=2, by_alias=True))
