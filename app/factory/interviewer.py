import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.requirements import (
    Requirements,
    DocumentItem,
    Clarification,
    InformationGapAnalysis,
    InformationContradiction
)
from app.tools.registry import registry
from app.retrieval.document_loader import DocumentLoader, RawDocument

# Comprehensive set of generic instructions, prompt metadata, and stopwords to ignore during gap detection
GENERIC_STOPWORDS: Set[str] = {
    # Pronouns, prepositions, conjunctions, aux verbs
    "this", "that", "these", "those", "with", "have", "from", "user", "agent",
    "system", "please", "should", "could", "would", "must", "build", "will",
    "shall", "can", "may", "might", "into", "onto", "upon", "about", "above",
    "across", "after", "before", "behind", "below", "beside", "between", "both",
    "each", "either", "neither", "other", "some", "such", "than", "then", "there",
    "when", "where", "which", "while", "who", "whom", "whose", "why", "what",
    # Prompting & meta-instruction words
    "create", "make", "generate", "develop", "construct", "assistant", "bot",
    "chatbot", "helper", "answer", "answers", "answering", "question", "questions",
    "help", "helps", "helping", "provide", "provides", "providing", "using", "uses",
    "used", "based", "according", "company", "organization", "enterprise", "business",
    "document", "documents", "documentation", "file", "files", "corpus", "manual",
    "handbook", "policy", "policies", "guideline", "guidelines", "rules", "rule",
    "standard", "standards", "information", "info", "data", "detail", "details",
    "knowledge", "employee", "employees", "staff", "personnel", "internal", "external",
    "queries", "query", "request", "requests", "support", "service", "services",
    "verify", "verified", "verifying", "check", "checking", "search", "searching",
    "developer", "developers", "operator", "operators", "engineer", "engineers",
    "client", "clients", "member", "members", "admin", "admins", "audience"
}

class IntakeInterviewer:
    """Module 1: Intake Interviewer - Conducts requirements intake and document inspection."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def inspect_documents(self, doc_folder: str) -> List[DocumentItem]:
        """Scan directory and produce structured document inventory with topics and metadata."""
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
                    "sample": d.content[:300],
                    "total_rows": d.metadata.get("total_rows"),
                    "text_blocks": []
                }
            if d.page:
                summary_map[fname]["pages"].add(d.page)
            summary_map[fname]["total_chars"] += len(d.content)
            summary_map[fname]["text_blocks"].append(d.content)

        items: List[DocumentItem] = []
        for fname, info in summary_map.items():
            page_count = len(info["pages"]) if info["pages"] else 1
            record_count = info.get("total_rows")

            # Extract detected topics from headers/key terms
            all_text = " ".join(info["text_blocks"])
            detected_topics = self._extract_key_topics(all_text)

            sample_snippet = info["sample"].replace("\n", " ").strip()
            if len(sample_snippet) > 120:
                sample_snippet = sample_snippet[:120] + "..."

            desc = f"Format {info['format']}. Approx {info['total_chars']} chars. Preview: {sample_snippet}"

            items.append(DocumentItem(
                filename=fname,
                format=info["format"],
                description=desc,
                page_count=page_count if info["format"] != "CSV" else None,
                record_count=record_count,
                content_summary=f"Covers topics: {', '.join(detected_topics[:4]) if detected_topics else 'General data'}",
                detected_topics=detected_topics[:8]
            ))

        return items

    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract meaningful topics/headers from document text generically."""
        topics = []
        # Look for markdown or uppercase headers: e.g. # Topic, SECTION X: Topic, or lines with Title Case
        header_patterns = [
            r"^#+\s+(.+)$",
            r"(?:Section|Chapter|Policy|Directive|Protocol|Specification|Standard)\s*[\d.:\-]*\s*([A-Za-z0-9\s\-]+)",
            r"^[A-Z][A-Za-z0-9\s]{3,30}:"
        ]
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            for pat in header_patterns:
                m = re.search(pat, line, re.MULTILINE)
                if m:
                    extracted = m.group(1).strip() if m.groups() else line.replace(":", "").strip()
                    if len(extracted) > 3 and len(extracted) < 50 and extracted not in topics:
                        topics.append(extracted)
                        break

        # If too few headers, extract frequent capitalized phrases
        if len(topics) < 2:
            phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text)
            for p in phrases:
                if p not in topics and len(p) < 40:
                    topics.append(p)
                if len(topics) >= 5:
                    break

        return topics[:8]

    def detect_information_gaps(
        self,
        inventory: List[DocumentItem],
        doc_folder: str,
        brief: str
    ) -> InformationGapAnalysis:
        """Inspect document texts to identify missing, contradictory, duplicated, and incomplete information."""
        if not os.path.exists(doc_folder):
            return InformationGapAnalysis(
                missing_information=["All requested documentation is missing from disk."]
            )

        raw_docs = DocumentLoader.load_directory(doc_folder)
        gaps = InformationGapAnalysis()

        # 1. Detect Duplicated Information across documents
        # Check for matching passages (lines, paragraphs, or sentences >= 50 chars) between distinct files
        seen_snippets: Dict[str, str] = {}  # normalized text -> filename
        duplicates: Set[str] = set()

        for d in raw_docs:
            snippets = [s.strip() for s in re.split(r"[\r\n]+|\.\s+", d.content) if len(s.strip()) >= 40]
            for s in snippets:
                # Strip punctuation and whitespace to compare semantic passage content
                norm_s = re.sub(r"[^\w\s]", "", s).strip().lower()
                norm_s = re.sub(r"\s+", " ", norm_s)[:150]
                if len(norm_s) < 35:
                    continue
                if norm_s in seen_snippets and seen_snippets[norm_s] != d.source:
                    duplicates.add(
                        f"Identical or near-duplicate passage found in '{seen_snippets[norm_s]}' and '{d.source}': \"{s[:80]}...\""
                    )
                else:
                    seen_snippets[norm_s] = d.source
        gaps.duplicated_information = list(duplicates)[:5]

        # 2. Detect Incomplete Information
        incomplete_markers = ["[tbd]", "[todo]", "[pending]", "to be determined", "to be announced", "[missing]", "under review", "placeholder"]
        incomplete_found: Set[str] = set()
        for d in raw_docs:
            lower_content = d.content.lower()
            for marker in incomplete_markers:
                if marker in lower_content:
                    incomplete_found.add(
                        f"Incomplete marker '{marker}' found in '{d.source}' indicating unfinished documentation."
                    )
            # Check for abrupt truncation or empty sections
            if re.search(r":\s*(\[|\.\.\.|\?)\s*$", d.content, re.MULTILINE):
                incomplete_found.add(f"Unresolved specification field found in '{d.source}'.")
        gaps.incomplete_information = list(incomplete_found)[:5]

        # 3. Detect Contradictions between documents
        contradictions: List[InformationContradiction] = []
        # Generic heuristic: Find key numerical specifications or limits stated differently across files
        # E.g. "max depth 3000m" vs "max depth 4500m", "ceiling: 400ft" vs "ceiling: 500ft"
        spec_regex = re.compile(
            r"\b(maximum|max|minimum|min|limit|ceiling|threshold|depth|temperature|speed|capacity|leave|approval|tier)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?\s*[a-zA-Z%$€£]*)",
            re.IGNORECASE
        )
        spec_map: Dict[str, List[Tuple[str, str, str]]] = {} # norm_key -> [(source, raw_statement, value)]
        for d in raw_docs:
            for line in d.content.split("\n"):
                match = spec_regex.search(line)
                if match:
                    key = match.group(1).lower()
                    val = match.group(2).strip()
                    if key not in spec_map:
                        spec_map[key] = []
                    spec_map[key].append((d.source, line.strip(), val))

        for key, matches in spec_map.items():
            sources = set(m[0] for m in matches)
            values = set(m[2] for m in matches)
            if len(sources) > 1 and len(values) > 1:
                # Contradiction detected
                statements = [f"[{src}] \"{stmt}\"" for src, stmt, _ in matches[:3]]
                contradictions.append(InformationContradiction(
                    topic=f"Conflicting {key.title()} Specification",
                    conflicting_statements=statements,
                    conflicting_sources=list(sources),
                    resolution_strategy=f"Decline automated execution and defer to conservative lower bound until verified by human operator."
                ))
        gaps.contradictory_information = contradictions[:5]

        # 4. Detect Missing Information (topics mentioned in user brief that have no document coverage)
        # Extract candidate nouns / topic words from brief, filtering out generic instruction words
        brief_words = [
            w for w in re.findall(r"\b[A-Za-z]{4,}\b", brief)
            if w.lower() not in GENERIC_STOPWORDS and not w.isdigit()
        ]
        all_corpus_text = " ".join([d.content for d in raw_docs]).lower()
        missing_topics: List[str] = []
        for word in sorted(set(brief_words)):
            w = word.lower()
            if (
                w not in all_corpus_text
                and (not w.endswith("s") or w[:-1] not in all_corpus_text)
                and (not w.endswith("es") or w[:-2] not in all_corpus_text)
                and (not w.endswith("ed") or w[:-2] not in all_corpus_text)
                and (not w.endswith("ing") or w[:-3] not in all_corpus_text)
            ):
                missing_topics.append(word)

        if missing_topics:
            gaps.missing_information.append(
                f"Brief keywords not found anywhere in uploaded documents: {', '.join(sorted(missing_topics)[:6])}"
            )

        return gaps

    def generate_clarifying_questions(self, brief: str, doc_folder: str) -> List[str]:
        """Formulate no more than five high-value clarifying questions regarding gaps, ambiguities, and operational scope."""
        # If user explicitly specified that the brief is self-contained with no clarification needed, return empty
        b_lower = brief.lower()
        if ("self-contained" in b_lower or "unambiguous" in b_lower or "no clarification needed" in b_lower) and "contradiction" not in b_lower:
            return []

        inventory = self.inspect_documents(doc_folder)
        doc_names = [item.filename for item in inventory]
        gaps = self.detect_information_gaps(inventory, doc_folder, brief)

        gap_summary = []
        if gaps.contradictory_information:
            for c in gaps.contradictory_information:
                gap_summary.append(f"Contradiction: {c.topic} between {', '.join(c.conflicting_sources)}")
        if gaps.incomplete_information:
            gap_summary.extend(gaps.incomplete_information[:2])
        if gaps.missing_information:
            gap_summary.extend(gaps.missing_information[:2])

        prompt = (
            f"Review this user brief, document inventory, and detected information gaps:\n"
            f"User Brief: {brief}\n"
            f"Available Documents: {doc_names}\n"
            f"Detected Information Gaps:\n" + ("\n".join(gap_summary) if gap_summary else "No severe data contradictions found.") + "\n\n"
            "Formulate up to 5 critical, high-value clarifying questions regarding audience, operational scope, contradictions, or refusal limits.\n"
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

        # If LLM didn't return questions, formulate high-value questions deterministically from detected gaps
        if not questions:
            deterministic_qs = []
            for c in gaps.contradictory_information[:2]:
                deterministic_qs.append(
                    f"Regarding '{c.topic}': conflicting values were found in {', '.join(c.conflicting_sources)}. Which document takes precedence?"
                )
            for m in gaps.missing_information[:2]:
                deterministic_qs.append(
                    f"The brief references terms not covered in the documents ({m}). Should the agent strictly refuse these out-of-scope requests?"
                )
            for inc in gaps.incomplete_information[:1]:
                deterministic_qs.append(
                    f"The documentation contains incomplete specifications ({inc}). Should the agent defer or answer with conservative defaults?"
                )
            if not deterministic_qs:
                if any(w in brief.lower() for w in ["hr", "leave", "attendance", "handbook", "employee"]):
                    deterministic_qs = [
                        "Should the assistant handle contract workers or temporary staff differently from standard full-time employees?",
                        "Are inquiries regarding personal compensation, salary records, or health insurance claims strictly out of scope?"
                    ]
                elif any(w in brief.lower() for w in ["procurement", "spare", "supplier", "catalog"]):
                    deterministic_qs = [
                        "Are emergency orders subject to standard PO approval threshold limits, or can superintendents approve up to $10,000?",
                        "Should price comparisons factor in express freight courier surcharges or list catalog unit prices only?"
                    ]
                else:
                    deterministic_qs = [
                        "Who is the primary target audience (e.g., technical operators, internal staff, external clients)?",
                        "Are there specific sensitive topics or requests that the assistant must strictly refuse to answer?"
                    ]
            questions = deterministic_qs

        # Enforce maximum 5 questions ceiling
        return questions[:5]

    def conduct_interview(
        self,
        brief: str,
        doc_folder: str,
        clarification_answers: Optional[Dict[str, str]] = None,
        unattended: bool = True,
    ) -> Requirements:
        """Process brief, inspect folder, identify gaps, ask clarifications, and produce structured Requirements schema."""
        inventory = self.inspect_documents(doc_folder)
        gaps = self.detect_information_gaps(inventory, doc_folder, brief)

        doc_summary_text = "\n".join([
            f"- {item.filename} ({item.format}, pages: {item.page_count or 'N/A'}, records: {item.record_count or 'N/A'}): {item.description} Topics: {', '.join(item.detected_topics)}"
            for item in inventory
        ]) if inventory else "No documents found."

        available_tools = registry.list_tools()

        clarifications_text = "None provided (unattended mode)."
        if clarification_answers:
            clarifications_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in clarification_answers.items()])

        # Build documented conservative assumptions if in unattended mode
        conservative_assumptions = [
            "Provided documents are treated as the sole ground truth; undocumented claims will be strictly refused.",
            "Unanswered clarification questions are resolved using conservative, read-only operational defaults."
        ]
        if gaps.contradictory_information:
            for c in gaps.contradictory_information:
                conservative_assumptions.append(
                    f"Contradiction in '{c.topic}': Deferring to conservative lower bound and refusing automated override without human verification."
                )

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "interviewer.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        gap_summary_json = gaps.model_dump_json(indent=2)
        prompt = template.format(
            user_brief=brief,
            document_summary=doc_summary_text,
            information_gaps_summary=gap_summary_json,
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
            clean_json = response_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            data = json.loads(clean_json.strip())
        except Exception:
            # Generic fallback based on brief and inventory
            doc_topics = []
            for item in inventory:
                doc_topics.extend(item.detected_topics)

            data = {
                "agent_name": "Autonomous Domain Assistant",
                "purpose": brief,
                "user_intent": "Informational query answering from verified corpus",
                "target_audience": "Domain operators and authorized personnel",
                "domain": "Generic Enterprise",
                "scope": f"Verifiable documentation queries covering {', '.join(doc_topics[:3]) if doc_topics else 'provided corpus'}",
                "tone": "Professional, authoritative, and concise",
                "constraints": ["Strict grounding required", "No external transactions"],
                "must_answer_topics": doc_topics[:4] if doc_topics else ["Documented specifications", "Verified procedures"],
                "must_refuse_topics": ["Undocumented speculations", "External transactions", "Personal private records"],
                "required_tools": ["current_date"],
                "document_inventory": [d.model_dump() for d in inventory],
                "information_gaps": gaps.model_dump(),
                "assumptions": conservative_assumptions,
                "ambiguities": ["Precedence rules between conflicting documents require explicit confirmation."],
                "unsupported_requirements": ["Direct financial transactions", "External API interactions"],
                "clarifications": []
            }

        # Merge actual disk inventory and detected information gaps
        if inventory:
            data["document_inventory"] = [item.model_dump() for item in inventory]

        if "information_gaps" not in data or not data["information_gaps"]:
            data["information_gaps"] = gaps.model_dump()

        # In unattended mode, append conservative assumptions
        if unattended and "assumptions" in data:
            for ca in conservative_assumptions:
                if ca not in data["assumptions"]:
                    data["assumptions"].append(ca)

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
