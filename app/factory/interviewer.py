import os
import json
from typing import Dict, Any, List, Optional
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.requirements import Requirements, DocumentItem, Clarification
from app.tools.registry import registry
from app.retrieval.document_loader import DocumentLoader

class IntakeInterviewer:
    """Module 1: Intake Interviewer - Conducts requirements intake and document inspection."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def inspect_documents(self, doc_folder: str) -> List[DocumentItem]:
        """Scan directory and produce structured document inventory."""
        if not os.path.exists(doc_folder):
            return []

        docs = DocumentLoader.load_directory(doc_folder)
        summary_map: Dict[str, Dict[str, Any]] = {}

        for d in docs:
            fname = d.source
            if fname not in summary_map:
                summary_map[fname] = {
                    "filename": fname,
                    "format": d.file_type.upper(),
                    "pages": set(),
                    "total_chars": 0,
                    "sample": d.content[:200]
                }
            if d.page:
                summary_map[fname]["pages"].add(d.page)
            summary_map[fname]["total_chars"] += len(d.content)

        items: List[DocumentItem] = []
        for fname, info in summary_map.items():
            page_count = len(info["pages"]) if info["pages"] else 1
            desc = f"Contains approx {info['total_chars']} characters. Sample: {info['sample'].replace(chr(10), ' ')[:100]}..."
            items.append(DocumentItem(
                filename=fname,
                format=info["format"],
                description=desc,
                page_count=page_count
            ))

        return items

    def generate_clarifying_questions(self, brief: str, doc_folder: str) -> List[str]:
        """Formulate no more than five relevant clarifying questions regarding requirements and scope."""
        inventory = self.inspect_documents(doc_folder)
        doc_names = [item.filename for item in inventory]

        prompt = (
            f"Review this user brief and document inventory:\n"
            f"User Brief: {brief}\n"
            f"Available Documents: {doc_names}\n\n"
            "Formulate up to 5 concise, critical clarifying questions to resolve ambiguities in scope, audience, tools, or policies.\n"
            "Return a JSON list of questions: [\"Question 1\", \"Question 2\", ...]. Never output more than 5 questions."
        )

        try:
            response = self.llm.generate(prompt=prompt, json_mode=True, temperature=0.1)
            clean = response.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            data = json.loads(clean.strip())
            if isinstance(data, list):
                questions = [str(q) for q in data[:5]]
            elif isinstance(data, dict):
                first_val = list(data.values())[0]
                questions = [str(q) for q in first_val[:5]] if isinstance(first_val, list) else []
            else:
                questions = []
        except Exception:
            questions = []

        if not questions:
            questions = [
                "Who is the primary target audience (e.g., internal staff, department managers, external clients)?",
                "Are there specific topics or requests that the assistant must strictly refuse to answer?",
                "What tone should the assistant maintain (e.g., formal and authoritative, supportive and friendly)?",
                "Are there specific external tools or data sources required beyond the provided files?",
                "Should responses follow a specific output structure (e.g., bulleted highlights, strict tabular format)?"
            ]

        # Enforce maximum 5 questions ceiling
        return questions[:5]

    def conduct_interview(
        self,
        brief: str,
        doc_folder: str,
        clarification_answers: Optional[Dict[str, str]] = None,
        unattended: bool = True,
    ) -> Requirements:
        """Process brief, inspect folder, ask clarifications, and produce Requirements schema."""
        inventory = self.inspect_documents(doc_folder)

        doc_summary_text = "\n".join([
            f"- {item.filename} ({item.format}, pages: {item.page_count}): {item.description}"
            for item in inventory
        ]) if inventory else "No documents found."

        available_tools = registry.list_tools()

        clarifications_text = "None provided (unattended mode)."
        if clarification_answers:
            clarifications_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in clarification_answers.items()])

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "interviewer.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            user_brief=brief,
            document_summary=doc_summary_text,
            clarification_context=clarifications_text,
            available_tools=", ".join(available_tools)
        )

        response_text = self.llm.generate(
            prompt=prompt,
            json_mode=True,
            temperature=0.1
        )

        # Parse JSON
        try:
            # Handle potential markdown code fencing
            clean_json = response_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            data = json.loads(clean_json.strip())
        except Exception:
            # Fallback if raw text returned
            data = {
                "agent_name": "Autonomous Domain Assistant",
                "purpose": brief,
                "target_audience": "Domain users",
                "scope": "Verifiable documentation queries",
                "tone": "Professional and helpful",
                "must_answer_topics": ["General policy", "Documented specifications"],
                "must_refuse_topics": ["Undocumented claims", "Confidential records"],
                "required_tools": ["current_date"],
                "document_inventory": [d.model_dump() for d in inventory],
                "assumptions": ["Documents provided are accurate and current."],
                "ambiguities": ["Edge case handling requires confirmation."],
                "unsupported_requirements": ["External transactions"],
                "clarifications": []
            }

        # Ensure document inventory from actual disk inspection is merged
        if inventory:
            data["document_inventory"] = [item.model_dump() for item in inventory]

        # Enforce tool allowlist validation
        requested_tools = data.get("required_tools", [])
        data["required_tools"] = registry.validate_selection(requested_tools)

        # Validate with Pydantic
        requirements = Requirements(**data)
        return requirements

    def save_requirements(self, requirements: Requirements, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(requirements.model_dump_json(indent=2))
