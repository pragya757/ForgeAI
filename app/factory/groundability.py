import os
import re
import json
from typing import Optional, List, Dict, Any
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.requirements import Requirements
from app.schemas.groundability import (
    GroundabilityReport,
    SupportedTopic,
    PartiallySupportedTopic,
    UnsupportedTopic,
    EvidenceReference
)
from app.retrieval.document_loader import DocumentLoader, RawDocument

class GroundabilityGuard:
    """Module 2: Groundability Guard - Validates topic coverage against source evidence."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def _find_evidence_for_topic(
        self,
        topic: str,
        docs: List[RawDocument]
    ) -> List[EvidenceReference]:
        """Search raw documents for textual evidence supporting the topic."""
        topic_keywords = [
            w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", topic)
            if w.lower() not in {"and", "the", "for", "with", "from", "rules", "policy", "guidelines"}
        ]
        if not topic_keywords:
            topic_keywords = [topic.lower()]

        evidence_refs: List[EvidenceReference] = []

        for d in docs:
            lines = d.content.split("\n")
            for idx, line in enumerate(lines):
                line_clean = line.strip()
                if len(line_clean) < 15:
                    continue
                line_lower = line_clean.lower()
                matches = sum(1 for kw in topic_keywords if kw in line_lower)
                if matches > 0:
                    # Score relevance by proportion of matched keywords
                    relevance = round(min(1.0, 0.4 + (matches / len(topic_keywords)) * 0.6), 2)
                    # Create excerpt with some surrounding context
                    excerpt = line_clean
                    if len(excerpt) > 200:
                        excerpt = excerpt[:197] + "..."
                    page_info = f"Page {d.page}" if d.page else (f"Row {d.metadata.get('row_start')}" if d.metadata.get("row_start") else "Section 1")
                    evidence_refs.append(EvidenceReference(
                        source_document=d.source,
                        page_or_record=page_info,
                        excerpt=excerpt,
                        relevance_score=relevance
                    ))
                    if len(evidence_refs) >= 3:
                        break
            if len(evidence_refs) >= 5:
                break

        # Sort by relevance
        evidence_refs.sort(key=lambda x: x.relevance_score, reverse=True)
        return evidence_refs[:3]

    def _classify_absence_nature(self, topic: str, reason: str) -> str:
        """Distinguish missing information from nonexistent or unsupported capabilities."""
        topic_lower = topic.lower()
        reason_lower = reason.lower()

        # Capability / transaction check
        action_keywords = ["wire", "transfer", "payment", "credit card", "write", "execute", "modify", "database write", "booking", "live transaction"]
        if any(ak in topic_lower or ak in reason_lower for ak in action_keywords):
            return "unsupported_capability"

        # Inherently non-existent / impossible / fictional check
        impossible_keywords = ["telepathy", "mars ocean", "perpetual motion", "magic", "faster-than-light", "fictional", "nonexistent", "impossible"]
        if any(ik in topic_lower or ik in reason_lower for ik in impossible_keywords):
            return "inherently_nonexistent"

        # Default to missing from current corpus
        return "missing_from_corpus"

    def inspect_groundability(
        self,
        requirements: Requirements,
        doc_folder: str
    ) -> GroundabilityReport:
        """Examine document text against must_answer_topics and unsupported_requirements."""
        docs = DocumentLoader.load_directory(doc_folder) if os.path.exists(doc_folder) else []

        # Build concise excerpts for the LLM
        excerpts = []
        for d in docs[:15]:
            snippet = d.content[:400].replace("\n", " ")
            page_info = f", Page {d.page}" if d.page else ""
            excerpts.append(f"[{d.source}{page_info}] {snippet}...")
        excerpts_text = "\n".join(excerpts) if excerpts else "No document content found."

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "groundability.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            requirements_json=requirements.model_dump_json(indent=2),
            document_excerpts=excerpts_text
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
            # Deterministic evidence-backed fallback
            doc_names = list(set(d.source for d in docs))
            supported = []
            partially_supported = []
            unsupported = []
            doc_coverage_map: Dict[str, List[str]] = {name: [] for name in doc_names}

            for t in requirements.must_answer_topics:
                ev_refs = self._find_evidence_for_topic(t, docs)
                if ev_refs:
                    src_docs = list(set(e.source_document for e in ev_refs))
                    for sd in src_docs:
                        if sd in doc_coverage_map:
                            doc_coverage_map[sd].append(t)
                    supported.append({
                        "topic": t,
                        "evidence_sources": src_docs,
                        "coverage_summary": f"Verified in {', '.join(src_docs)}.",
                        "confidence_score": max([e.relevance_score for e in ev_refs]),
                        "evidence_references": [e.model_dump() for e in ev_refs]
                    })
                else:
                    # If requested in must_answer but no evidence found, classify as unsupported or partially supported
                    unsupported.append({
                        "topic": t,
                        "reason": "No textual evidence found in uploaded corpus.",
                        "absence_nature": self._classify_absence_nature(t, "missing from corpus"),
                        "confidence_score": 0.90
                    })

            for u in requirements.unsupported_requirements + requirements.must_refuse_topics:
                unsupported.append({
                    "topic": u,
                    "reason": "Explicitly outside verified document scope or involves unsupported capability.",
                    "absence_nature": self._classify_absence_nature(u, "explicitly refused or unsupported capability"),
                    "confidence_score": 0.95
                })

            data = {
                "supported_topics": supported,
                "partially_supported_topics": partially_supported,
                "unsupported_topics": unsupported,
                "document_coverage_map": doc_coverage_map,
                "refusal_recommendations": [f"Refuse queries regarding {u['topic']} ({u.get('absence_nature', 'unsupported')})" for u in unsupported],
                "sanitized_answerable_topics": [s["topic"] for s in supported],
                "overall_groundability_score": len(supported) / max(1, len(supported) + len(unsupported))
            }

        # Enhance data with evidence references and absence classification if missing
        if "supported_topics" in data:
            for s in data["supported_topics"]:
                if "evidence_references" not in s or not s["evidence_references"]:
                    ev = self._find_evidence_for_topic(s.get("topic", ""), docs)
                    s["evidence_references"] = [e.model_dump() for e in ev]
                if "confidence_score" not in s:
                    s["confidence_score"] = 0.95

        if "partially_supported_topics" in data:
            for p in data["partially_supported_topics"]:
                if "evidence_references" not in p or not p["evidence_references"]:
                    ev = self._find_evidence_for_topic(p.get("topic", ""), docs)
                    p["evidence_references"] = [e.model_dump() for e in ev]
                if "confidence_score" not in p:
                    p["confidence_score"] = 0.60

        if "unsupported_topics" in data:
            for u in data["unsupported_topics"]:
                if "absence_nature" not in u:
                    u["absence_nature"] = self._classify_absence_nature(u.get("topic", ""), u.get("reason", ""))
                if "confidence_score" not in u:
                    u["confidence_score"] = 0.95

        # Strictly sanitize answerable topics: unsupported topics MUST NOT enter answerable scope
        unsupported_topic_names = set(u.get("topic") for u in data.get("unsupported_topics", []))
        candidate_answerable = [s.get("topic") for s in data.get("supported_topics", [])]
        for p in data.get("partially_supported_topics", []):
            candidate_answerable.append(p.get("topic"))

        data["sanitized_answerable_topics"] = [
            t for t in candidate_answerable if t and t not in unsupported_topic_names
        ]

        if not data.get("refusal_recommendations"):
            data["refusal_recommendations"] = [
                f"Strictly refuse requests regarding '{u.get('topic')}' as it is {u.get('absence_nature', 'unsupported')}."
                for u in data.get("unsupported_topics", [])
            ]

        # Validate with Pydantic
        report = GroundabilityReport(**data)
        return report

    def save_report(self, report: GroundabilityReport, output_path: str) -> None:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
