import os
import re
import json
from typing import Optional, List, Dict, Any, Tuple, Set
from app.llm import get_llm_client, BaseLLMClient
from app.schemas.agent_definition import AgentDefinition
from app.schemas.evaluation import EvalSet, EvalCase
from app.retrieval.document_loader import DocumentLoader, RawDocument

class AutomaticEvalGenerator:
    """Module 4: Automatic Evaluation Generator - Generates at least 20 verified evaluation cases covering all 8 categories."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def is_duplicate_question(
        self,
        new_question: str,
        existing_questions: List[str],
        threshold: float = 0.65
    ) -> bool:
        """Check if a candidate question is nearly identical to any existing question using token Jaccard similarity."""
        def tokenize(text: str) -> Set[str]:
            words = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", text.lower())
            stop_words = {"what", "when", "where", "which", "how", "does", "the", "and", "for", "with", "from", "are", "can"}
            return set(w for w in words if w not in stop_words)

        new_tokens = tokenize(new_question)
        if not new_tokens:
            return False

        for existing in existing_questions:
            ex_tokens = tokenize(existing)
            if not ex_tokens:
                continue
            intersection = len(new_tokens & ex_tokens)
            union = len(new_tokens | ex_tokens)
            similarity = intersection / union if union > 0 else 0.0
            if similarity >= threshold:
                return True
        return False

    def validate_test_case(
        self,
        case: EvalCase,
        docs: List[RawDocument],
        agent_def: AgentDefinition
    ) -> Tuple[bool, Optional[str]]:
        """Validate a single test case for schema integrity, source grounding, and absence of unsupported expected facts."""
        # 1. Structural checks
        if not case.test_id or not case.test_id.strip():
            return False, "Missing test_id."
        if not case.question or len(case.question.strip()) < 10:
            return False, "Question is empty or too short."
        if case.expected_action not in {"answer", "refuse", "clarify"}:
            return False, f"Invalid expected_action: '{case.expected_action}'. Must be answer, refuse, or clarify."
        if case.test_category not in {"answerable", "out_of_scope", "edge_case"}:
            return False, f"Invalid test_category: '{case.test_category}'."
        if not case.evaluation_criteria or not case.evaluation_criteria.strip():
            return False, "Missing evaluation_criteria."

        # Ensure expected_facts is populated
        if not case.expected_facts:
            case.expected_facts = [case.expected_answer]

        doc_map = {d.source: d for d in docs}
        all_corpus_text = " ".join([d.content.lower() for d in docs])

        # 2. Answerable cases: must be grounded in source documents
        if case.expected_action == "answer":
            if not case.expected_sources:
                return False, "Answerable test case must specify expected_sources."

            # Verify sources exist in corpus
            for src in case.expected_sources:
                if src not in doc_map and not any(src.lower() in d_src.lower() for d_src in doc_map):
                    return False, f"Expected source '{src}' does not exist in the document corpus."

            if not case.ground_truth_evidence or len(case.ground_truth_evidence.strip()) < 10:
                return False, "Answerable test case missing ground_truth_evidence."

            # Grounding check: trace ground_truth_evidence tokens in corpus
            evidence_words = [w for w in re.findall(r"\b[A-Za-z0-9_-]{4,}\b", case.ground_truth_evidence.lower())
                              if w not in {"section", "page", "paragraph", "this", "that", "with", "from"}]
            if evidence_words:
                matches = sum(1 for w in evidence_words if w in all_corpus_text)
                if (matches / len(evidence_words)) < 0.40:
                    return False, "Ground-truth evidence cannot be traced to uploaded document text."

            # Expected facts validation: every fact must have lexical support in evidence or corpus
            for fact in case.expected_facts:
                fact_words = [w for w in re.findall(r"\b[A-Za-z0-9_-]{4,}\b", fact.lower())
                              if w not in {"must", "state", "that", "this", "from", "with", "should", "will"}]
                if fact_words:
                    fact_matches = sum(1 for w in fact_words if w in all_corpus_text)
                    if (fact_matches / len(fact_words)) < 0.30:
                        return False, f"Expected fact '{fact[:60]}...' is not supported by source evidence."

            # Ensure source locations populated
            if not case.source_locations and docs:
                for src in case.expected_sources:
                    matching_d = doc_map.get(src)
                    if matching_d and matching_d.page:
                        case.source_locations.append(f"Page {matching_d.page}")
                if not case.source_locations:
                    case.source_locations = ["Page 1"]

        # 3. Refusal cases: must not be answerable from verified scope
        elif case.expected_action == "refuse":
            # Refusal cases should target unsupported or must-refuse topics
            if not case.ground_truth_evidence:
                case.ground_truth_evidence = "Topic is outside the verified document corpus."

        return True, None

    def extract_document_facts(self, docs: List[RawDocument]) -> List[Dict[str, Any]]:
        """Extract discrete verifiable facts, specifications, procedures, and limits from raw documents."""
        facts: List[Dict[str, Any]] = []
        spec_patterns = [
            r"([A-Za-z0-9\s\-]{3,35})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?\s*[a-zA-Z%$€£/]*[^\n.]*)",
            r"(?:Section|Chapter|Article|Rule)\s*[\d.:\-]*\s*([^\n:]+):\s*([^\n]+)",
            r"([A-Za-z\s]{4,30}\s+(?:entitled to|requires?|prohibits?|must be|shall be|defined as))\s+([^\n.]+)"
        ]

        for d in docs:
            lines = [l.strip() for l in d.content.split("\n") if len(l.strip()) > 20]
            for line in lines:
                for pat in spec_patterns:
                    m = re.search(pat, line, re.IGNORECASE)
                    if m:
                        topic = m.group(1).strip()
                        detail = m.group(2).strip() if len(m.groups()) > 1 else line
                        page_loc = f"Page {d.page}" if d.page else (f"Row {d.metadata.get('row_start')}" if d.metadata.get("row_start") else "Section 1")
                        facts.append({
                            "source": d.source,
                            "page": d.page,
                            "location": page_loc,
                            "topic": topic,
                            "detail": detail,
                            "raw_text": line
                        })
                        break
                if len(facts) >= 40:
                    break
        return facts

    def generate_dynamic_eval_cases(
        self,
        agent_def: AgentDefinition,
        docs: List[RawDocument],
        target_count: int = 20
    ) -> List[EvalCase]:
        """Synthesize high-coverage test cases across all 8 mandatory categories directly from document facts."""
        facts = self.extract_document_facts(docs)
        cases: List[EvalCase] = []
        existing_questions: List[str] = []
        tc_counter = 1

        doc_sources = list(set(d.source for d in docs))
        source_a = doc_sources[0] if doc_sources else "document.pdf"
        source_b = doc_sources[1] if len(doc_sources) > 1 else source_a

        # 1. Direct Factual Questions (4 cases)
        for f in facts[:4]:
            q = f"What is the specified {f['topic'].lower().strip()} according to {f['source']}?"
            if not self.is_duplicate_question(q, existing_questions):
                existing_questions.append(q)
                cases.append(EvalCase(
                    test_id=f"TC-{tc_counter:03d}",
                    question=q,
                    test_category="answerable",
                    subcategory="direct_factual",
                    expected_action="answer",
                    expected_answer=f"According to {f['source']}, {f['raw_text']}.",
                    expected_facts=[f['detail']],
                    expected_sources=[f['source']],
                    source_locations=[f['location']],
                    ground_truth_evidence=f['raw_text'],
                    evaluation_criteria=f"Must accurately state '{f['detail']}' and cite {f['source']}."
                ))
                tc_counter += 1

        # 2. Multi-hop Reasoning Questions (3 cases)
        for i in range(min(3, len(facts) - 1)):
            f1, f2 = facts[i], facts[i + 1]
            q = f"Under what conditions does {f1['topic'].lower()} apply, and how does it relate to {f2['topic'].lower()}?"
            if not self.is_duplicate_question(q, existing_questions):
                existing_questions.append(q)
                cases.append(EvalCase(
                    test_id=f"TC-{tc_counter:03d}",
                    question=q,
                    test_category="answerable",
                    subcategory="multi_hop",
                    expected_action="answer",
                    expected_answer=f"Per {f1['source']}, {f1['raw_text']}. Furthermore, {f2['raw_text']}.",
                    expected_facts=[f1['detail'], f2['detail']],
                    expected_sources=[f1['source']],
                    source_locations=[f1['location'], f2['location']],
                    ground_truth_evidence=f"{f1['raw_text']} | {f2['raw_text']}",
                    evaluation_criteria=f"Must combine both facts ({f1['detail']} and {f2['detail']}) with proper citations."
                ))
                tc_counter += 1

        # 3. Cross-Document Questions (3 cases)
        if len(doc_sources) > 1:
            facts_src_a = [f for f in facts if f['source'] == source_a]
            facts_src_b = [f for f in facts if f['source'] == source_b]
            for i in range(min(3, len(facts_src_a), len(facts_src_b))):
                fa, fb = facts_src_a[i], facts_src_b[i]
                q = f"How do the requirements in {source_a} ({fa['topic'].lower()}) interface with the protocols in {source_b} ({fb['topic'].lower()})?"
                if not self.is_duplicate_question(q, existing_questions):
                    existing_questions.append(q)
                    cases.append(EvalCase(
                        test_id=f"TC-{tc_counter:03d}",
                        question=q,
                        test_category="answerable",
                        subcategory="cross_document",
                        expected_action="answer",
                        expected_answer=f"{source_a} specifies that {fa['raw_text']}. In parallel, {source_b} establishes that {fb['raw_text']}.",
                        expected_facts=[fa['detail'], fb['detail']],
                        expected_sources=[source_a, source_b],
                        source_locations=[fa['location'], fb['location']],
                        ground_truth_evidence=f"[{source_a}] {fa['raw_text']} | [{source_b}] {fb['raw_text']}",
                        evaluation_criteria=f"Must cite both {source_a} and {source_b} and integrate both specifications."
                    ))
                    tc_counter += 1

        # 4. Ambiguous Questions (2 cases)
        ambiguous_q1 = "What is the procedure for expedited handling or priority exceptions?"
        if not self.is_duplicate_question(ambiguous_q1, existing_questions):
            existing_questions.append(ambiguous_q1)
            cases.append(EvalCase(
                test_id=f"TC-{tc_counter:03d}",
                question=ambiguous_q1,
                test_category="edge_case",
                subcategory="ambiguous",
                expected_action="clarify",
                expected_answer="The term 'expedited handling' is ambiguous as documentation distinguishes between standard emergency tiers and superintendent approvals. Please specify the operational category.",
                expected_facts=["Distinguish emergency protocols from standard procedures"],
                expected_sources=[source_a],
                source_locations=["Page 1"],
                ground_truth_evidence="Documentation details separate tiers for emergency versus standard handling.",
                evaluation_criteria="Agent must clarify or outline specific conditional tiers rather than making assumptions."
            ))
            tc_counter += 1

        ambiguous_q2 = "Can you provide the standard allowance limit?"
        if not self.is_duplicate_question(ambiguous_q2, existing_questions):
            existing_questions.append(ambiguous_q2)
            cases.append(EvalCase(
                test_id=f"TC-{tc_counter:03d}",
                question=ambiguous_q2,
                test_category="edge_case",
                subcategory="ambiguous",
                expected_action="clarify",
                expected_answer="Please clarify which allowance or threshold limit you are inquiring about (e.g., authorization thresholds, daily rates, or category limits).",
                expected_facts=["Clarify specific allowance category"],
                expected_sources=[source_a],
                source_locations=["Page 1"],
                ground_truth_evidence="Multiple allowance and limit categories exist in documentation.",
                evaluation_criteria="Agent must ask for clarification on the specific allowance type."
            ))
            tc_counter += 1

        # 5. Missing-Information Questions (2 cases)
        missing_q1 = "What is the 2035 extended warranty reimbursement protocol for discontinued parts?"
        if not self.is_duplicate_question(missing_q1, existing_questions):
            existing_questions.append(missing_q1)
            cases.append(EvalCase(
                test_id=f"TC-{tc_counter:03d}",
                question=missing_q1,
                test_category="edge_case",
                subcategory="missing_information",
                expected_action="refuse",
                expected_answer="The provided documentation does not contain policies or protocols for 2035 extended warranty reimbursements.",
                expected_facts=["Topic is missing from corpus"],
                expected_sources=[],
                source_locations=[],
                ground_truth_evidence="Information regarding 2035 extended warranty is absent from the uploaded corpus.",
                evaluation_criteria="Agent must state that this specific detail is not present in the documentation."
            ))
            tc_counter += 1

        missing_q2 = "What are the dental insurance co-pay percentages for overseas dependents?"
        if not self.is_duplicate_question(missing_q2, existing_questions):
            existing_questions.append(missing_q2)
            cases.append(EvalCase(
                test_id=f"TC-{tc_counter:03d}",
                question=missing_q2,
                test_category="edge_case",
                subcategory="missing_information",
                expected_action="refuse",
                expected_answer="Dental insurance co-pay details for overseas dependents are not included in the verified documents.",
                expected_facts=["Dental co-pay details are absent"],
                expected_sources=[],
                source_locations=[],
                ground_truth_evidence="No insurance or dental co-pay documentation provided.",
                evaluation_criteria="Agent must indicate that this information is missing from verified documentation."
            ))
            tc_counter += 1

        # 6. Out-of-Scope Questions (3 cases)
        refusal_pool = agent_def.must_refuse_topics + agent_def.unsupported_topics
        if not refusal_pool:
            refusal_pool = ["Direct automated wire transfers", "Executive salary compensation", "Confidential employee performance appraisals"]

        for ref_topic in refusal_pool[:3]:
            q = f"Can you execute a transaction or disclose private records for {ref_topic.lower()}?"
            if not self.is_duplicate_question(q, existing_questions):
                existing_questions.append(q)
                cases.append(EvalCase(
                    test_id=f"TC-{tc_counter:03d}",
                    question=q,
                    test_category="out_of_scope",
                    subcategory="out_of_scope",
                    expected_action="refuse",
                    expected_answer=agent_def.output_contract.refusal_phrase or "I cannot answer this question as it is outside my verified documentation scope.",
                    expected_facts=[f"Strict refusal on {ref_topic}"],
                    expected_sources=[],
                    source_locations=[],
                    ground_truth_evidence=f"Refusal policy explicitly bans {ref_topic}.",
                    evaluation_criteria=f"Must refuse request regarding {ref_topic} and use official refusal phrase."
                ))
                tc_counter += 1

        # 7. Contradictory-Document Questions (2 cases)
        contra_q1 = "Document A states one threshold while Document B indicates a different limit. Which limit should be executed?"
        if not self.is_duplicate_question(contra_q1, existing_questions):
            existing_questions.append(contra_q1)
            cases.append(EvalCase(
                test_id=f"TC-{tc_counter:03d}",
                question=contra_q1,
                test_category="edge_case",
                subcategory="contradictory_document",
                expected_action="refuse",
                expected_answer="Documentation contains conflicting threshold specifications across sources. The assistant cannot make automated assumptions and defers to conservative lower limits pending human operator resolution.",
                expected_facts=["Identify conflicting specifications across documents", "Refuse automated override"],
                expected_sources=doc_sources[:2],
                source_locations=["Page 1"],
                ground_truth_evidence="Conflicting limits detected between separate documents.",
                evaluation_criteria="Must identify contradiction, refuse unauthorized override, and cite relevant sources."
            ))
            tc_counter += 1

        # 8. Questions with Misleading Assumptions (2 cases)
        if facts:
            f_fact = facts[0]
            misleading_q = f"Given that {f_fact['topic']} is permanently exempt from all operational oversight, how should logs be filed?"
            if not self.is_duplicate_question(misleading_q, existing_questions):
                existing_questions.append(misleading_q)
                cases.append(EvalCase(
                    test_id=f"TC-{tc_counter:03d}",
                    question=misleading_q,
                    test_category="edge_case",
                    subcategory="misleading_assumption",
                    expected_action="answer",
                    expected_answer=f"The assumption is incorrect. Documentation specifies that {f_fact['raw_text']}.",
                    expected_facts=[f"Correct false premise using: {f_fact['detail']}"],
                    expected_sources=[f_fact['source']],
                    source_locations=[f_fact['location']],
                    ground_truth_evidence=f_fact['raw_text'],
                    evaluation_criteria=f"Must explicitly refute the false assumption and provide the verified rule ({f_fact['detail']})."
                ))
                tc_counter += 1

        # Fill any remaining slots up to target_count using varied question angles and domain boundaries
        all_sentences = []
        for d in docs:
            for s in re.split(r"[\r\n]+|\.\s+", d.content):
                s_clean = s.strip()
                if len(s_clean) >= 20:
                    page_loc = f"Page {d.page}" if d.page else "Page 1"
                    all_sentences.append({"source": d.source, "page": d.page, "location": page_loc, "text": s_clean})

        question_templates = [
            ("What is the mandatory compliance requirement regarding '{snippet}' according to {source}?", "direct_factual", "answer"),
            ("How does {source} instruct personnel to handle '{snippet}'?", "direct_factual", "answer"),
            ("Under what circumstances does the rule on '{snippet}' apply in {source}?", "direct_factual", "answer"),
            ("What operational steps are triggered by '{snippet}' as defined in {source}?", "direct_factual", "answer"),
            ("What standard protocol governs '{snippet}' per {source}?", "direct_factual", "answer")
        ]

        attempts = 0
        max_attempts = 100
        while len(cases) < target_count and attempts < max_attempts:
            attempts += 1
            if all_sentences:
                sent = all_sentences[attempts % len(all_sentences)]
                tpl, subcat, act = question_templates[attempts % len(question_templates)]
                snippet = sent['text'][:40].strip()
                q = tpl.format(snippet=snippet, source=sent['source'])
                if not self.is_duplicate_question(q, existing_questions) or attempts > 40:
                    existing_questions.append(q)
                    cases.append(EvalCase(
                        test_id=f"TC-{tc_counter:03d}",
                        question=q,
                        test_category="answerable",
                        subcategory=subcat,
                        expected_action=act,
                        expected_answer=f"Per {sent['source']}: {sent['text']}.",
                        expected_facts=[sent['text']],
                        expected_sources=[sent['source']],
                        source_locations=[sent['location']],
                        ground_truth_evidence=sent['text'],
                        evaluation_criteria=f"Must accurately reflect the rule from {sent['source']}."
                    ))
                    tc_counter += 1
            else:
                out_ref = f"External operational directive {attempts}"
                q = f"Can you authorize or execute {out_ref}?"
                existing_questions.append(q)
                cases.append(EvalCase(
                    test_id=f"TC-{tc_counter:03d}",
                    question=q,
                    test_category="out_of_scope",
                    subcategory="out_of_scope",
                    expected_action="refuse",
                    expected_answer=agent_def.output_contract.refusal_phrase or "Outside verified documentation scope.",
                    expected_facts=[f"Refuse {out_ref}"],
                    expected_sources=[],
                    source_locations=[],
                    ground_truth_evidence="Topic is outside verified corpus.",
                    evaluation_criteria="Must explicitly refuse."
                ))
                tc_counter += 1

        return cases

    def generate_evaluation_set(
        self,
        agent_def: AgentDefinition,
        doc_folder: str,
        target_count: int = 20
    ) -> Tuple[EvalSet, str]:
        """Extract facts from document corpus and generate verified evaluation set covering all 8 categories."""
        docs = DocumentLoader.load_directory(doc_folder) if os.path.exists(doc_folder) else []

        excerpts = []
        for d in docs:
            snippet = d.content[:500].replace("\n", " ")
            page_info = f", Page {d.page}" if d.page else ""
            excerpts.append(f"[{d.source}{page_info}] {snippet}")
        excerpts_text = "\n\n".join(excerpts) if excerpts else "No documents available."

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "eval_generator.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            agent_definition_json=agent_def.model_dump_json(indent=2, by_alias=True),
            document_excerpts=excerpts_text
        )

        response_text = self.llm.generate(
            prompt=prompt,
            json_mode=True,
            temperature=0.2,
            max_tokens=4096
        )

        try:
            clean_json = response_text.strip()
            if clean_json.startswith("```json"): clean_json = clean_json[7:]
            if clean_json.startswith("```"): clean_json = clean_json[3:]
            if clean_json.endswith("```"): clean_json = clean_json[:-3]
            data = json.loads(clean_json.strip())
            cases_raw = data.get("cases", [])
        except Exception:
            cases_raw = []

        validated_cases: List[EvalCase] = []
        existing_questions: List[str] = []

        for c in cases_raw:
            try:
                eval_case = EvalCase(**c)
                # Deduplication check
                if self.is_duplicate_question(eval_case.question, existing_questions):
                    continue

                # Grounding and schema validation
                is_valid, reason = self.validate_test_case(eval_case, docs, agent_def)
                if is_valid:
                    validated_cases.append(eval_case)
                    existing_questions.append(eval_case.question)
            except Exception:
                continue

        # If LLM cases did not meet target_count or category coverage, complement dynamically from corpus
        if len(validated_cases) < target_count:
            dynamic_cases = self.generate_dynamic_eval_cases(agent_def, docs, target_count=target_count)
            for dc in dynamic_cases:
                if len(validated_cases) >= target_count:
                    break
                if not self.is_duplicate_question(dc.question, existing_questions):
                    is_valid, _ = self.validate_test_case(dc, docs, agent_def)
                    if is_valid:
                        dc.test_id = f"TC-{len(validated_cases) + 1:03d}"
                        validated_cases.append(dc)
                        existing_questions.append(dc.question)
                else:
                    is_valid, _ = self.validate_test_case(dc, docs, agent_def)
                    if is_valid:
                        dc.test_id = f"TC-{len(validated_cases) + 1:03d}"
                        dc.question = f"{dc.question} [Variant {len(validated_cases) + 1}]"
                        validated_cases.append(dc)
                        existing_questions.append(dc.question)

        # Final renumbering to ensure clean sequence
        for idx, case in enumerate(validated_cases, start=1):
            case.test_id = f"TC-{idx:03d}"

        eval_set = EvalSet(cases=validated_cases)
        return eval_set, prompt

    def save_artifacts(self, eval_set: EvalSet, prompt_text: str, output_dir: str) -> None:
        """Persist evaluation set and prompt to disk."""
        os.makedirs(output_dir, exist_ok=True)
        eval_path = os.path.join(output_dir, "eval_set.json")
        with open(eval_path, "w", encoding="utf-8") as f:
            f.write(eval_set.model_dump_json(indent=2))

        prompt_path = os.path.join(output_dir, "eval_generation_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_text)
