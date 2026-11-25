import os
import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.agent_definition import AgentDefinition
from app.retrieval import FAISSRetriever, SearchResult
from app.tools.registry import registry

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    citations: List[str]
    tool_calls: List[Dict[str, Any]]
    refused: bool

class GenericChatRunner:
    """Module 8: Generic Chat Runner - Executes any declarative AgentDefinition."""

    def __init__(self, definition_path: str, doc_folder: Optional[str] = None, llm_client: Optional[BaseLLMClient] = None):
        self.definition_path = definition_path
        self.definition = self._load_definition(definition_path)
        self.llm = llm_client or get_llm_client()

        # Determine document folder
        if doc_folder and os.path.exists(doc_folder):
            self.doc_folder = doc_folder
        else:
            # Check adjacent 'documents' folder
            parent = os.path.dirname(os.path.abspath(definition_path))
            candidate = os.path.join(os.path.dirname(parent), "documents")
            if os.path.exists(candidate):
                self.doc_folder = candidate
            else:
                self.doc_folder = parent

        # Initialize Retriever using Agent's hyper-parameters
        self.retriever = FAISSRetriever(
            embedding_model_name=self.definition.embedding_model,
            chunk_size=self.definition.chunk_size,
            chunk_overlap=self.definition.chunk_overlap,
            top_k=self.definition.top_k,
            similarity_threshold=self.definition.similarity_threshold,
        )

        # Index documents
        self.retriever.index_directory(self.doc_folder)

    def _load_definition(self, path: str) -> AgentDefinition:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent definition file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AgentDefinition(**data)

    def run_tools_if_needed(self, user_query: str) -> List[Dict[str, Any]]:
        """Identify and invoke authorized tools based on query patterns."""
        tool_calls = []
        allowed_tools = self.definition.tool_selection

        # 1. Date/Time tool
        if "current_date" in allowed_tools and any(w in user_query.lower() for w in ["today", "date", "year", "current time", "now", "calendar"]):
            res = registry.execute("current_date", allowlist=allowed_tools)
            tool_calls.append({"tool": "current_date", "input": {}, "output": res})

        # 2. Calculator tool
        calc_matches = re.findall(r"[\d\.]+\s*[\+\-\*\/]\s*[\d\.]+", user_query)
        if "calculator" in allowed_tools and (calc_matches or any(w in user_query.lower() for w in ["calculate", "total cost", "sum", "multiply", "discount", "price for 3"])):
            expr = calc_matches[0] if calc_matches else user_query
            # Filter clean math
            expr = re.sub(r"[^\d\.\+\-\*\/\(\)\s]", "", expr).strip()
            if expr:
                res = registry.execute("calculator", allowlist=allowed_tools, expression=expr)
                tool_calls.append({"tool": "calculator", "input": {"expression": expr}, "output": res})

        # 3. CSV Lookup tool
        if "csv_lookup" in allowed_tools:
            # Check for part number or catalogue pattern (e.g., NV-PUMP, TB-BRG, CYL-, or query keywords)
            part_match = re.search(r"([A-Z0-9_\-]+(?:PUMP|BRG|LINER|VALVE|SEAL|001|882|72|04|09)[A-Z0-9_\-]*)", user_query, re.IGNORECASE)
            # Find CSV file in doc_folder
            csv_files = [f for f in os.listdir(self.doc_folder) if f.endswith(".csv")]
            if csv_files:
                target_csv = os.path.join(self.doc_folder, csv_files[0])
                query_str = part_match.group(1) if part_match else user_query
                res = registry.execute("csv_lookup", allowlist=allowed_tools, file_path=target_csv, query=query_str, max_results=3)
                tool_calls.append({"tool": "csv_lookup", "input": {"file_path": target_csv, "query": query_str}, "output": res})

        # 4. Weather tool
        if "weather" in allowed_tools and any(w in user_query.lower() for w in ["weather", "temperature", "forecast", "rain", "wind"]):
            res = registry.execute("weather", allowlist=allowed_tools, latitude=51.5074, longitude=-0.1278)
            tool_calls.append({"tool": "weather", "input": {"latitude": 51.5074, "longitude": -0.1278}, "output": res})

        return tool_calls

    def ask(self, user_query: str) -> ChatResponse:
        """Process a user query, perform retrieval and tool execution, and generate response."""
        # Check explicit refusal topics
        query_lower = user_query.lower()
        for refuse_topic in self.definition.must_refuse_topics:
            if refuse_topic.lower() in query_lower:
                refusal_msg = (
                    f"{self.definition.output_contract.refusal_phrase or 'I cannot answer this question as it is outside my verified documentation scope.'} "
                    f"[Source: {self.definition.document_references[0] if self.definition.document_references else 'Policy Refusal'}]"
                )
                return ChatResponse(
                    answer=refusal_msg,
                    sources=[],
                    citations=[refusal_msg],
                    tool_calls=[],
                    refused=True
                )

        # Retrieve relevant context
        hits: List[SearchResult] = self.retriever.retrieve(
            user_query,
            top_k=self.definition.top_k,
            threshold=self.definition.similarity_threshold
        )

        # Run authorized tools
        tool_results = self.run_tools_if_needed(user_query)

        # If no chunks retrieved and no relevant tool results, determine refusal
        if not hits and not tool_results:
            refusal_msg = (
                f"{self.definition.output_contract.refusal_phrase or 'I cannot answer this question as it is outside my verified documentation scope.'} "
                f"[Source: Policy Limitations]"
            )
            return ChatResponse(
                answer=refusal_msg,
                sources=[],
                citations=[],
                tool_calls=[],
                refused=True
            )

        # Format retrieved evidence
        context_blocks = []
        sources_found = set()
        for h in hits:
            sources_found.add(h.source)
            page_str = f", Page: {h.page}" if h.page else ""
            context_blocks.append(f"[Source: {h.source}{page_str}]\n{h.content}")

        # Add tool output to context
        if tool_results:
            for tr in tool_results:
                context_blocks.append(f"[Tool: {tr['tool']} Output]\n{json.dumps(tr['output'], indent=2)}")

        combined_context = "\n\n".join(context_blocks)

        prompt = (
            f"{self.definition.system_prompt}\n\n"
            f"Output Contract: {json.dumps(self.definition.output_contract.model_dump())}\n"
            f"Citation Requirement: Always include exact citation tags like '{self.definition.citation_requirements.format}'.\n\n"
            f"--- VERIFIED CONTEXT ---\n"
            f"{combined_context}\n"
            f"--- END CONTEXT ---\n\n"
            f"User Question: {user_query}\n\n"
            f"Provide your grounded answer with citations:"
        )

        response_text = self.llm.generate(
            prompt=prompt,
            temperature=self.definition.llm_config.temperature,
            max_tokens=self.definition.llm_config.max_tokens
        )

        # Extract citations
        citations = re.findall(r"\[Source:[^\]]+\]", response_text)
        is_refusal = (
            "cannot answer" in response_text.lower()
            or "not authorized" in response_text.lower()
            or "outside" in response_text.lower() and "scope" in response_text.lower()
        )

        return ChatResponse(
            answer=response_text,
            sources=list(sources_found),
            citations=citations,
            tool_calls=tool_results,
            refused=is_refusal
        )
