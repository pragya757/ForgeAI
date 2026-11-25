import os
import json
import re
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

from app.llm import get_llm_client, BaseLLMClient
from app.schemas.agent_definition import AgentDefinition
from app.retrieval import FAISSRetriever, SearchResult
from app.tools.registry import registry, sanitize_sensitive_data

class ChatResponse(BaseModel):
    """Structured response from the GenericChatRunner runtime."""
    answer: str
    sources: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    refused: bool = False
    contract_valid: bool = True
    contract_violations: List[str] = Field(default_factory=list)
    history_length: int = 0

class GenericChatRunner:
    """
    Module 8: Generic Chat Runner
    Executes any valid declarative AgentDefinition dynamically.
    Features:
    - Dynamic configuration loading (file path, dict, or AgentDefinition instance)
    - Document index loading and FAISS retrieval
    - Context construction with source and page attribution
    - Strict tool allowlisting & security enforcement
    - Source citation extraction and validation
    - Refusal handling with policy adherence
    - Output contract compliance validation
    - Stateful and stateless conversation history
    - Sensitive configuration masking
    """

    def __init__(
        self,
        definition_path: Optional[str] = None,
        definition: Optional[Union[AgentDefinition, Dict[str, Any]]] = None,
        doc_folder: Optional[str] = None,
        llm_client: Optional[BaseLLMClient] = None
    ):
        # 1. Dynamic Configuration Loading
        if definition is not None:
            if isinstance(definition, AgentDefinition):
                self.definition = definition
            elif isinstance(definition, dict):
                self.definition = AgentDefinition(**definition)
            else:
                raise TypeError(f"Unsupported definition type: {type(definition)}")
            self.definition_path = definition_path or "in_memory_definition.json"
        elif definition_path is not None:
            self.definition_path = definition_path
            self.definition = self._load_definition(definition_path)
        else:
            raise ValueError("Either definition_path or definition object must be provided to GenericChatRunner.")

        self.llm = llm_client or get_llm_client()
        self.history: List[Dict[str, str]] = []

        # 2. Document Index Loading
        if doc_folder and os.path.exists(doc_folder):
            self.doc_folder = os.path.abspath(doc_folder)
        elif self.definition_path and os.path.exists(self.definition_path):
            parent = os.path.dirname(os.path.abspath(self.definition_path))
            candidate = os.path.join(os.path.dirname(parent), "documents")
            if os.path.exists(candidate):
                self.doc_folder = candidate
            elif os.path.exists(os.path.join(parent, "documents")):
                self.doc_folder = os.path.join(parent, "documents")
            else:
                self.doc_folder = parent
        else:
            self.doc_folder = os.getcwd()

        # Initialize Retriever using Agent's hyper-parameters
        self.retriever = FAISSRetriever(
            embedding_model_name=self.definition.embedding_model,
            chunk_size=self.definition.chunk_size,
            chunk_overlap=self.definition.chunk_overlap,
            top_k=self.definition.top_k,
            similarity_threshold=self.definition.similarity_threshold,
        )

        # Index documents if folder exists
        if os.path.exists(self.doc_folder) and os.path.isdir(self.doc_folder):
            self.retriever.index_directory(self.doc_folder)

    def _load_definition(self, path: str) -> AgentDefinition:
        """Load and validate AgentDefinition from a JSON file path."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Agent definition file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AgentDefinition(**data)

    def reset_history(self) -> None:
        """Reset internal conversation history."""
        self.history.clear()

    def run_tools_if_needed(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Identify and invoke authorized tools based on query patterns.
        Strictly enforces allowlist, validates arguments, prevents arbitrary execution,
        and restricts file lookups.
        """
        tool_calls = []
        allowed_tools = self.definition.tool_selection or []

        # 1. Date/Time tool
        if "current_date" in allowed_tools and any(w in user_query.lower() for w in ["today", "date", "year", "current time", "now", "calendar"]):
            res = registry.execute("current_date", allowlist=allowed_tools)
            tool_calls.append({"tool": "current_date", "input": {}, "output": res})

        # 2. Calculator tool
        calc_matches = re.findall(r"[\d\.]+\s*[\+\-\*\/]\s*[\d\.]+", user_query)
        if "calculator" in allowed_tools and (calc_matches or any(w in user_query.lower() for w in ["calculate", "total cost", "sum", "multiply", "discount", "price for"])):
            expr = calc_matches[0] if calc_matches else user_query
            expr = re.sub(r"[^\d\.\+\-\*\/\(\)\s]", "", expr).strip()
            if expr:
                res = registry.execute("calculator", allowlist=allowed_tools, expression=expr)
                tool_calls.append({"tool": "calculator", "input": {"expression": expr}, "output": res})

        # 3. CSV Lookup tool (Restricted to authorized input files & directory)
        if "csv_lookup" in allowed_tools:
            csv_files = [f for f in os.listdir(self.doc_folder) if f.endswith(".csv")] if os.path.exists(self.doc_folder) else []
            if csv_files:
                target_csv = os.path.join(self.doc_folder, csv_files[0])
                query_str = ""

                # Priority A: Check for quoted string
                quoted_match = re.search(r"['\"]([^'\"]+)['\"]", user_query)
                if quoted_match:
                    query_str = quoted_match.group(1)
                else:
                    # Priority B: Alphanumeric codes with hyphens or underscores (e.g. NV-PUMP-001)
                    code_match = re.search(r"\b([A-Za-z0-9]+[-_][A-Za-z0-9-_]+)\b", user_query)
                    if code_match:
                        query_str = code_match.group(1)
                    else:
                        # Priority C: Significant query tokens
                        stop_words = {"what", "is", "the", "for", "part", "number", "price", "stock", "available", "cost", "unit", "and", "in", "check", "lookup", "how", "much", "does"}
                        words = [w.strip("?,.:;!") for w in user_query.split() if w.lower().strip("?,.:;!") not in stop_words and len(w) > 2]
                        query_str = words[0] if words else user_query

                if query_str:
                    res = registry.execute(
                        "csv_lookup",
                        allowlist=allowed_tools,
                        file_path=target_csv,
                        query=query_str,
                        max_results=3,
                        authorized_directory=self.doc_folder,
                        authorized_files=self.definition.document_references
                    )
                    tool_calls.append({
                        "tool": "csv_lookup",
                        "input": {"file_path": os.path.basename(target_csv), "query": query_str},
                        "output": res
                    })

        # 4. Weather tool (with timeout and error handling)
        if "weather" in allowed_tools and any(w in user_query.lower() for w in ["weather", "temperature", "forecast", "rain", "wind"]):
            known_cities = {
                "singapore": (1.3521, 103.8198),
                "london": (51.5074, -0.1278),
                "rotterdam": (51.9244, 4.4777),
                "busan": (35.1796, 129.0756),
                "tokyo": (35.6762, 139.6503),
                "new york": (40.7128, -74.0060),
                "dubai": (25.2048, 55.2708),
                "oslo": (59.9139, 10.7522)
            }
            lat, lon = 51.5074, -0.1278
            city_name = None
            for c_name, coords in known_cities.items():
                if c_name in user_query.lower():
                    lat, lon = coords
                    city_name = c_name.title()
                    break

            res = registry.execute("weather", allowlist=allowed_tools, latitude=lat, longitude=lon)
            if city_name:
                res["resolved_location"] = city_name
            tool_calls.append({"tool": "weather", "input": {"latitude": lat, "longitude": lon}, "output": res})

        return tool_calls

    def validate_output_contract(self, response_text: str, is_refusal: bool) -> tuple[bool, List[str]]:
        """Validate response against the agent's OutputContract specification."""
        violations = []
        contract = self.definition.output_contract

        if is_refusal:
            refusal_phrase = contract.refusal_phrase or "outside my verified documentation scope"
            if refusal_phrase.lower() not in response_text.lower():
                # Allow standard refusal markers as acceptable
                if not any(m in response_text.lower() for m in ["cannot answer", "not authorized", "outside verified", "not documented"]):
                    violations.append(f"Refusal response did not include standard refusal phrase: '{refusal_phrase}'")
        else:
            if contract.require_citations:
                citations = re.findall(r"\[Source:[^\]]+\]", response_text)
                if not citations:
                    violations.append("Response omitted mandatory citations required by output contract.")

        valid = len(violations) == 0
        return valid, violations

    def ask(self, user_query: str, history: Optional[List[Dict[str, str]]] = None) -> ChatResponse:
        """
        Process a user query, perform retrieval and tool execution, apply contract validation,
        and manage conversation history.
        """
        active_history = history if history is not None else self.history
        query_lower = user_query.lower()

        # 1. Refusal check against must_refuse_topics
        for refuse_topic in self.definition.must_refuse_topics:
            if refuse_topic.lower() in query_lower:
                refusal_msg = (
                    f"{self.definition.output_contract.refusal_phrase or 'I cannot answer this question as it is outside my verified documentation scope.'} "
                    f"[Source: {self.definition.document_references[0] if self.definition.document_references else 'Policy Limitations'}]"
                )
                active_history.append({"role": "user", "content": user_query})
                active_history.append({"role": "assistant", "content": refusal_msg})
                return ChatResponse(
                    answer=refusal_msg,
                    sources=[],
                    citations=[refusal_msg],
                    tool_calls=[],
                    refused=True,
                    contract_valid=True,
                    contract_violations=[],
                    history_length=len(active_history)
                )

        # 2. Retrieve relevant context from document index
        hits: List[SearchResult] = self.retriever.retrieve(
            user_query,
            top_k=self.definition.top_k,
            threshold=self.definition.similarity_threshold
        )

        # 3. Execute authorized tools
        tool_results = self.run_tools_if_needed(user_query)

        # 4. If no relevant chunks and no tool results, refuse safely
        if not hits and not tool_results:
            refusal_msg = (
                f"{self.definition.output_contract.refusal_phrase or 'I cannot answer this question as it is outside my verified documentation scope.'} "
                f"[Source: Policy Limitations]"
            )
            active_history.append({"role": "user", "content": user_query})
            active_history.append({"role": "assistant", "content": refusal_msg})
            return ChatResponse(
                answer=refusal_msg,
                sources=[],
                citations=[],
                tool_calls=[],
                refused=True,
                contract_valid=True,
                contract_violations=[],
                history_length=len(active_history)
            )

        # 5. Format retrieved context
        context_blocks = []
        sources_found = set()
        for h in hits:
            sources_found.add(h.source)
            page_str = f", Page: {h.page}" if h.page else ""
            context_blocks.append(f"[Source: {h.source}{page_str}]\n{h.content}")

        # Add tool outputs to context
        if tool_results:
            for tr in tool_results:
                context_blocks.append(f"[Tool: {tr['tool']} Output]\n{json.dumps(tr['output'], indent=2)}")

        combined_context = "\n\n".join(context_blocks)

        # 6. Format multi-turn conversation history into prompt if available
        history_str = ""
        if active_history:
            history_lines = ["--- CONVERSATION HISTORY ---"]
            # Include up to last 4 turns for context
            for msg in active_history[-4:]:
                history_lines.append(f"{msg['role'].capitalize()}: {msg['content']}")
            history_lines.append("--- END HISTORY ---\n")
            history_str = "\n".join(history_lines)

        # 7. Construct system and user prompt
        prompt = (
            f"{self.definition.system_prompt}\n\n"
            f"Output Contract: {json.dumps(self.definition.output_contract.model_dump())}\n"
            f"Citation Requirement: Always include exact citation tags like '{self.definition.citation_requirements.format}'.\n\n"
            f"--- VERIFIED CONTEXT ---\n"
            f"{combined_context}\n"
            f"--- END CONTEXT ---\n\n"
            f"{history_str}"
            f"User Question: {user_query}\n\n"
            f"Provide your grounded answer with citations:"
        )

        # 8. Generate LLM response
        raw_response = self.llm.generate(
            prompt=prompt,
            temperature=self.definition.llm_config.temperature,
            max_tokens=self.definition.llm_config.max_tokens
        )

        # 9. Sanitize sensitive configuration from response
        response_text = sanitize_sensitive_data(raw_response)

        # 10. Extract citations and check refusal status
        citations = re.findall(r"\[Source:[^\]]+\]", response_text)
        is_refusal = (
            "cannot answer" in response_text.lower()
            or "not authorized" in response_text.lower()
            or ("outside" in response_text.lower() and "scope" in response_text.lower())
            or "does not contain" in response_text.lower()
        )

        # 11. Validate output contract
        contract_valid, violations = self.validate_output_contract(response_text, is_refusal)

        # Update conversation history
        active_history.append({"role": "user", "content": user_query})
        active_history.append({"role": "assistant", "content": response_text})

        return ChatResponse(
            answer=response_text,
            sources=list(sources_found),
            citations=citations,
            tool_calls=tool_results,
            refused=is_refusal,
            contract_valid=contract_valid,
            contract_violations=violations,
            history_length=len(active_history)
        )
