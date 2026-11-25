import os
import re
import json
from typing import Optional, Dict, Any, List, Tuple
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.requirements import Requirements, DocumentItem
from app.schemas.groundability import GroundabilityReport
from app.schemas.agent_definition import (
    AgentDefinition,
    OutputContract,
    CitationRequirements,
    ModelConfig,
    RerankingConfig,
    MetadataConfig
)
from app.tools.registry import registry
from app.retrieval.document_loader import DocumentLoader

class AgentGenerator:
    """Module 3: Agent Generator - Dynamically generates declarative, executable agent definitions."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def analyze_document_characteristics(
        self,
        doc_folder: str,
        inventory: List[DocumentItem]
    ) -> Dict[str, Any]:
        """Inspect document collection characteristics to adapt chunking, retrieval, and reranking parameters."""
        formats = set(item.format.upper() for item in inventory)
        total_files = len(inventory)
        has_csv = "CSV" in formats
        has_pdf = "PDF" in formats
        has_txt = any(f in formats for f in ("TXT", "MD"))

        # Calculate character counts and volume
        total_chars = 0
        if os.path.exists(doc_folder):
            try:
                raw_docs = DocumentLoader.load_directory(doc_folder)
                total_chars = sum(len(d.content) for d in raw_docs)
            except Exception:
                total_chars = total_files * 1500

        is_heterogeneous = len(formats) > 1

        # 1. Adaptive Chunk Size & Overlap Selection
        if has_csv and not (has_pdf or has_txt):
            # Pure tabular data: smaller chunks preserve row-level precision
            adaptive_chunk_size = 300
            adaptive_chunk_overlap = 60
        elif has_csv and (has_pdf or has_txt):
            # Mixed tabular and narrative
            adaptive_chunk_size = 400
            adaptive_chunk_overlap = 80
        elif has_pdf:
            # Standard PDF documents with granular sections
            adaptive_chunk_size = 500
            adaptive_chunk_overlap = 100
        else:
            # Narrative / text files
            if total_chars > 8000:
                adaptive_chunk_size = 600
                adaptive_chunk_overlap = 120
            else:
                adaptive_chunk_size = 450
                adaptive_chunk_overlap = 90

        # 2. Adaptive Retrieval Top-K and Similarity Threshold
        if total_files <= 2:
            adaptive_top_k = 3
            adaptive_similarity_threshold = 0.32
        elif total_files >= 5 or is_heterogeneous:
            adaptive_top_k = 5
            adaptive_similarity_threshold = 0.38
        else:
            adaptive_top_k = 4
            adaptive_similarity_threshold = 0.35

        # 3. Optional Reranking based on collection characteristics
        # Enable reranking if collection has >= 3 files, is heterogeneous, or total chars > 10,000
        rerank_enabled = (total_files >= 3 or is_heterogeneous or total_chars > 10000)
        rerank_config = RerankingConfig(
            enabled=rerank_enabled,
            method="cross_encoder",
            top_n=min(3, adaptive_top_k),
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

        # 4. Configurable Embedding Model
        embedding_model = os.getenv("FORGEAI_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        return {
            "formats": list(formats),
            "total_files": total_files,
            "total_chars": total_chars,
            "has_csv": has_csv,
            "has_pdf": has_pdf,
            "is_heterogeneous": is_heterogeneous,
            "adaptive_chunk_size": adaptive_chunk_size,
            "adaptive_chunk_overlap": adaptive_chunk_overlap,
            "adaptive_top_k": adaptive_top_k,
            "adaptive_similarity_threshold": adaptive_similarity_threshold,
            "embedding_model": embedding_model,
            "reranking_config": rerank_config
        }

    def determine_tool_selection_and_justifications(
        self,
        requirements: Requirements,
        doc_folder: str,
        inventory: List[DocumentItem]
    ) -> Tuple[List[str], Dict[str, str]]:
        """Dynamically select authorized tools from registry with explicit necessity justifications."""
        available_tools = set(registry.list_tools())
        selected_tools: List[str] = []
        justifications: Dict[str, str] = {}

        # Scan text cues in requirements and constraints
        req_corpus = " ".join([
            requirements.purpose,
            requirements.scope,
            " ".join(requirements.constraints),
            " ".join(requirements.must_answer_topics),
            requirements.user_intent
        ]).lower()

        # Check for CSV files in folder or inventory
        csv_files_exist = False
        if os.path.exists(doc_folder):
            csv_files_exist = any(f.endswith(".csv") for f in os.listdir(doc_folder))
        csv_in_inventory = any(item.format.upper() == "CSV" for item in inventory)

        # 1. csv_lookup tool
        if (csv_files_exist or csv_in_inventory) and "csv_lookup" in available_tools:
            selected_tools.append("csv_lookup")
            justifications["csv_lookup"] = (
                "Structured CSV tabular files detected in document inventory; "
                "csv_lookup provides exact row, column, and record-level querying."
            )

        # 2. calculator tool
        math_cues = ["calculate", "math", "price", "pricing", "cost", "sum", "total", "budget",
                     "threshold", "tier", "limit", "rate", "$", "usd", "eur", "%", "discount", "formula"]
        if any(cue in req_corpus for cue in math_cues) and "calculator" in available_tools:
            selected_tools.append("calculator")
            justifications["calculator"] = (
                "Domain requirements involve numerical thresholds, price comparisons, "
                "or mathematical calculations."
            )

        # 3. current_date tool
        date_cues = ["today", "date", "year", "current", "time", "now", "calendar", "fiscal",
                     "expiration", "schedule", "period", "validity", "attendance"]
        if (any(cue in req_corpus for cue in date_cues) or "current_date" in requirements.required_tools) and "current_date" in available_tools:
            if "current_date" not in selected_tools:
                selected_tools.append("current_date")
            justifications["current_date"] = (
                "Required for temporal verification of ongoing policy validity, current date, "
                "or fiscal year alignment."
            )

        # 4. weather tool
        weather_cues = ["weather", "temperature", "forecast", "meteo", "rain", "wind", "maritime weather", "flight weather"]
        if any(cue in req_corpus for cue in weather_cues) and "weather" in available_tools:
            selected_tools.append("weather")
            justifications["weather"] = (
                "Domain operations involve meteorological condition checks or weather observations."
            )

        # Also validate and honor any explicitly requested tools from requirements that are valid
        for tool_name in requirements.required_tools:
            if tool_name in available_tools and tool_name not in selected_tools:
                # Reject csv_lookup if no CSV exists
                if tool_name == "csv_lookup" and not (csv_files_exist or csv_in_inventory):
                    continue
                selected_tools.append(tool_name)
                justifications[tool_name] = f"Explicitly requested by requirements for {requirements.domain} operations."

        return selected_tools, justifications

    def generate_system_prompt(
        self,
        requirements: Requirements,
        groundability: GroundabilityReport,
        tool_selection: List[str],
        tool_justifications: Dict[str, str],
        output_contract: OutputContract,
        citation_reqs: CitationRequirements
    ) -> str:
        """Dynamically generate authoritative system prompt incorporating groundability boundaries and refusal policy."""
        supported_list = "\n".join([f"- {t}" for t in groundability.sanitized_answerable_topics[:10]])
        unsupported_list = "\n".join([f"- {u.topic} ({u.absence_nature})" for u in groundability.unsupported_topics[:8]])
        must_refuse_list = "\n".join([f"- {r}" for r in requirements.must_refuse_topics[:8]])
        constraints_list = "\n".join([f"- {c}" for c in requirements.constraints[:5]]) if requirements.constraints else "- Answer strictly from verified context."

        tool_protocols = []
        for t in tool_selection:
            reason = tool_justifications.get(t, "Authorized tool.")
            tool_protocols.append(f"- `{t}`: {reason}")
        tools_block = "\n".join(tool_protocols) if tool_protocols else "- No external tools authorized. Answer using text retrieval only."

        prompt = (
            f"You are {requirements.agent_name}, an autonomous AI domain specialist dedicated to {requirements.purpose}.\n\n"
            f"### MISSION & IDENTITY\n"
            f"- Domain: {requirements.domain}\n"
            f"- Target Audience: {requirements.target_audience}\n"
            f"- Operational Tone: {requirements.tone}\n"
            f"- Scope: {requirements.scope}\n\n"
            f"### OPERATIONAL CONSTRAINTS\n"
            f"{constraints_list}\n\n"
            f"### VERIFIED GROUNDED TOPICS (Strictly Answerable)\n"
            f"{supported_list}\n\n"
            f"### STRICT REFUSAL POLICY & INSTRUCTIONS\n"
            f"1. You MUST explicitly refuse to answer queries concerning unsupported or out-of-scope topics:\n"
            f"{unsupported_list}\n"
            f"2. You MUST strictly refuse must-refuse topics:\n"
            f"{must_refuse_list}\n"
            f"3. When refusing, state clearly: \"{output_contract.refusal_phrase}\"\n"
            f"4. Never extrapolate, speculate, or fabricate ungrounded claims outside the retrieved documentation.\n\n"
            f"### AUTHORIZED TOOLS & PROTOCOLS\n"
            f"{tools_block}\n\n"
            f"### CITATION & OUTPUT CONTRACT\n"
            f"- All responses must follow {output_contract.format} format.\n"
            f"- Every factual claim must include a source citation formatted as: {citation_reqs.format}.\n"
            f"- Do not provide unanchored factual assertions without source references."
        )
        return prompt.strip()

    def validate_agent_definition(
        self,
        definition: AgentDefinition,
        requirements: Requirements,
        doc_folder: str
    ) -> None:
        """Validation stage: Rejects irrelevant tools, enforces groundability boundaries, and validates configurations."""
        available_tools = set(registry.list_tools())

        # 1. Reject tools not in registry
        for t in definition.tool_selection:
            if t not in available_tools:
                raise ValueError(f"Invalid tool configuration: Tool '{t}' is not registered in the tool registry.")

        # 2. Reject irrelevant tools (e.g. csv_lookup without CSV)
        csv_files_exist = False
        if os.path.exists(doc_folder):
            csv_files_exist = any(f.endswith(".csv") for f in os.listdir(doc_folder))
        csv_in_inventory = any(item.format.upper() == "CSV" for item in requirements.document_inventory)

        if "csv_lookup" in definition.tool_selection and not (csv_files_exist or csv_in_inventory):
            definition.tool_selection.remove("csv_lookup")
            if "csv_lookup" in definition.tool_justifications:
                del definition.tool_justifications["csv_lookup"]

        # 3. Ensure tool justifications exist for every tool
        for t in definition.tool_selection:
            if t not in definition.tool_justifications or not definition.tool_justifications[t].strip():
                definition.tool_justifications[t] = f"Authorized tool required for {requirements.domain} operations."

        # 4. Validate chunk size and overlap
        if definition.chunk_size <= 50:
            raise ValueError(f"Invalid chunk_size {definition.chunk_size}: must be > 50.")
        if definition.chunk_overlap < 0 or definition.chunk_overlap >= definition.chunk_size:
            raise ValueError(f"Invalid chunk_overlap {definition.chunk_overlap}: must be >= 0 and < chunk_size ({definition.chunk_size}).")

        # 5. Validate retrieval parameters
        if definition.top_k < 1:
            raise ValueError(f"Invalid top_k {definition.top_k}: must be >= 1.")
        if not (0.0 <= definition.similarity_threshold <= 1.0):
            raise ValueError(f"Invalid similarity_threshold {definition.similarity_threshold}: must be between 0.0 and 1.0.")

        # 6. Validate groundability boundaries
        unsupported_set = set(definition.unsupported_topics)
        unsupported_set.update(requirements.unsupported_requirements)
        definition.unsupported_topics = sorted(list(unsupported_set))
        definition.supported_topics = [t for t in definition.supported_topics if t not in unsupported_set]
        if not definition.supported_topics:
            definition.supported_topics = ["Verified documentation inquiries"]

        # Ensure must_refuse_topics includes all unsupported topics
        all_refusals = set(definition.must_refuse_topics)
        all_refusals.update(unsupported_set)
        definition.must_refuse_topics = sorted(list(all_refusals))

        # 7. Validate output contract refusal phrase
        if not definition.output_contract.refusal_phrase or not definition.output_contract.refusal_phrase.strip():
            definition.output_contract.refusal_phrase = "I cannot answer this question as it is outside my verified documentation scope."

    def generate_agent(
        self,
        requirements: Requirements,
        groundability: GroundabilityReport,
        doc_folder: str
    ) -> AgentDefinition:
        """Create complete, declarative AgentDefinition dynamically generated from requirements and document characteristics."""
        doc_chars = self.analyze_document_characteristics(doc_folder, requirements.document_inventory)
        tool_selection, tool_justifications = self.determine_tool_selection_and_justifications(
            requirements, doc_folder, requirements.document_inventory
        )

        doc_refs = [d.filename for d in requirements.document_inventory]
        unsupported_topics = [t.topic for t in groundability.unsupported_topics]
        sanitized_supported = groundability.sanitized_answerable_topics or [t.topic for t in groundability.supported_topics]

        output_contract = OutputContract(
            format="markdown",
            require_citations=True,
            citation_format="[Source: <document_name>, Page: <page>]",
            refusal_phrase="I cannot answer this question as it is outside my verified documentation scope.",
            section_headers=["Direct Answer", "Evidence & Citations"]
        )

        citation_requirements = CitationRequirements(
            must_cite=True,
            format="[Source: <filename>, Page: <page>]",
            granularity="sentence_level",
            prohibit_unanchored_claims=True
        )

        metadata_config = MetadataConfig(
            tracked_fields=["source", "page", "file_type", "total_pages"],
            include_in_context=True,
            citation_metadata_format="[Source: <source>, Page: <page>]"
        )

        # Dynamic system prompt
        system_prompt = self.generate_system_prompt(
            requirements=requirements,
            groundability=groundability,
            tool_selection=tool_selection,
            tool_justifications=tool_justifications,
            output_contract=output_contract,
            citation_reqs=citation_requirements
        )

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "agent_generator.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            requirements_json=requirements.model_dump_json(indent=2),
            groundability_json=groundability.model_dump_json(indent=2),
            document_characteristics_json=json.dumps(doc_chars, indent=2, default=str),
            available_tools=", ".join(registry.list_tools())
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
            # Deterministic fallback definition using analyzed characteristics
            data = {
                "agent_name": requirements.agent_name,
                "description": requirements.purpose,
                "system_prompt": system_prompt,
                "target_audience": requirements.target_audience,
                "supported_topics": sanitized_supported,
                "unsupported_topics": unsupported_topics,
                "must_refuse_topics": list(set(requirements.must_refuse_topics + unsupported_topics)),
                "document_references": doc_refs,
                "chunk_size": doc_chars["adaptive_chunk_size"],
                "chunk_overlap": doc_chars["adaptive_chunk_overlap"],
                "embedding_model": doc_chars["embedding_model"],
                "retrieval_method": "dense_vector_faiss",
                "top_k": doc_chars["adaptive_top_k"],
                "similarity_threshold": doc_chars["adaptive_similarity_threshold"],
                "reranking_config": doc_chars["reranking_config"].model_dump() if doc_chars["reranking_config"] else None,
                "metadata_config": metadata_config.model_dump(),
                "tool_selection": tool_selection,
                "tool_justifications": tool_justifications,
                "output_contract": output_contract.model_dump(),
                "citation_requirements": citation_requirements.model_dump(),
                "refusal_policy": (
                    f"Strict refusal on ungrounded claims, undocumented speculations, or unsupported topics: "
                    f"{', '.join(unsupported_topics[:4]) if unsupported_topics else 'out of scope requests'}."
                ),
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }

        # Merge calculated tool justifications and metadata if missing
        if "tool_justifications" not in data or not data["tool_justifications"]:
            data["tool_justifications"] = tool_justifications
        if "metadata_config" not in data:
            data["metadata_config"] = metadata_config.model_dump()
        if "reranking_config" not in data or data["reranking_config"] is None:
            data["reranking_config"] = doc_chars["reranking_config"].model_dump() if doc_chars["reranking_config"] else None

        # Ensure system prompt incorporates domain identity and refusal policy
        if "system_prompt" not in data or len(data.get("system_prompt", "")) < 100 or "STRICT REFUSAL" not in data.get("system_prompt", ""):
            data["system_prompt"] = system_prompt

        # Build AgentDefinition
        agent_def = AgentDefinition(**data)

        # Run strict validation stage
        self.validate_agent_definition(agent_def, requirements, doc_folder)

        return agent_def

    def save_definition(self, definition: AgentDefinition, output_path: str) -> None:
        """Persist declarative agent definition to disk."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(definition.model_dump_json(indent=2, by_alias=True))
