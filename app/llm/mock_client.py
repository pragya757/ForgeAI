import json
import re
from typing import Optional, List, Dict
from app.llm.base import BaseLLMClient

class MockLLMClient(BaseLLMClient):
    """
    Deterministic LLM client for offline unit/integration testing
    and fallback validation without external services.
    """
    def __init__(self, model_name: str = "mock-forge-v1"):
        self.model_name = model_name

    def is_available(self) -> tuple[bool, str]:
        return True, "Mock LLM is always available for deterministic execution."

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, json_mode=json_mode, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2048,
    ) -> str:
        last_message = messages[-1]["content"] if messages else ""
        system_content = "\n".join([m["content"] for m in messages if m.get("role") == "system"])
        combined = f"{system_content}\n{last_message}"

        # 1. Critic / Optimizer request
        if "CRITIC-OPTIMIZER" in combined or "Critic-Optimizer" in combined or "propose minimal, targeted changes" in combined:
            return self._mock_optimizer(combined)

        # 2. Judge request
        if "AUTOMATED JUDGE" in combined or "impartial, objective Judge" in combined or "Evaluate the following agent response" in combined:
            return self._mock_judge(combined)

        # 3. Evaluation Generator request
        if "EVALUATION GENERATOR" in combined or "Evaluation Generator" in combined or "generate at least 20 evaluation cases" in combined.lower():
            return self._mock_eval_generator(combined)

        # 4. Agent Generator request
        if "AGENT GENERATOR" in combined or "Agent Generator" in combined or "complete declarative agent definition" in combined:
            return self._mock_agent_generator(combined)

        # 5. Groundability Guard request
        if "GROUNDABILITY GUARD" in combined or "Groundability Guard" in combined:
            return self._mock_groundability(combined)

        # 6. Interviewer request
        if "INTAKE INTERVIEWER" in combined or "Intake Interviewer" in combined or "conducting an intelligent intake interview" in combined:
            return self._mock_interviewer(combined)

        # 7. Generic chat runner / question answering
        return self._mock_runner_response(combined)

    def _mock_interviewer(self, text: str) -> str:
        is_procurement = bool(re.search(r"\b(procurement|spares?|supplier|catalog|vessel|marine)\b", text.lower()))
        is_hr = bool(re.search(r"\b(hr|leave|attendance|handbook|holiday)\b", text.lower()))

        if is_procurement:
            data = {
                "agent_name": "Ship-Spares Procurement Assistant",
                "purpose": "Assist procurement officers in searching marine spare parts, comparing supplier pricing, checking availability, and following maritime procurement guidelines.",
                "user_intent": "Lookup parts, check stock, compare vendor quotes, and verify purchase approval limits.",
                "target_audience": "Vessel procurement staff and technical superintendents",
                "domain": "Maritime Procurement & Supply Chain",
                "scope": "Spare parts catalog lookup, supplier price comparison, purchase approval thresholds, and delivery lead times.",
                "tone": "Operational, accurate, and concise",
                "constraints": ["Strict adherence to PO authorization tiers", "No direct financial write capabilities"],
                "must_answer_topics": ["Part number lookup", "Supplier price comparison", "Stock availability", "Purchase order authorization limits", "Lead times"],
                "must_refuse_topics": ["Payment gateway transactions", "Crew payroll", "Vessel charter contracts", "Customs clearance bribery requests"],
                "required_tools": ["csv_lookup", "calculator", "current_date"],
                "document_inventory": [
                    {"filename": "spare_parts_catalog.csv", "format": "CSV", "description": "Inventory of ship spares, part numbers, stock, unit prices", "page_count": None, "record_count": 50, "content_summary": "Catalog of valves, pumps, bearings, filters", "detected_topics": ["Valves", "Pumps", "Bearings", "Filters"]},
                    {"filename": "supplier_information.pdf", "format": "PDF", "description": "Approved vendors, ratings, lead times and payment terms", "page_count": 2, "record_count": None, "content_summary": "Vendor lists and freight schedules", "detected_topics": ["Approved Vendors", "Delivery Times", "Credit Terms"]},
                    {"filename": "procurement_guidelines.pdf", "format": "PDF", "description": "PO approval tiers, procurement compliance, emergency order protocols", "page_count": 3, "record_count": None, "content_summary": "Authorization policies", "detected_topics": ["PO Approval Limits", "Emergency Orders", "Compliance"]}
                ],
                "information_gaps": {
                    "missing_information": ["Emergency air freight customs surcharge tables are not provided in uploaded files."],
                    "contradictory_information": [],
                    "duplicated_information": [],
                    "incomplete_information": []
                },
                "assumptions": ["Prices listed in CSV are in USD and exclude freight unless specified.", "Unattended defaults apply conservative threshold rules."],
                "ambiguities": ["Whether expedited freight quotes require superintendent sign-off."],
                "unsupported_requirements": ["Direct credit card processing", "Automated wire transfer"],
                "clarifications": [
                    {"question": "Are emergency orders subject to standard threshold limits?", "answer": "Emergency orders allow up to $10,000 superintendent approval."}
                ]
            }
        elif is_hr:
            data = {
                "agent_name": "HR Policy Assistant",
                "purpose": "Assist employees with inquiries regarding leave policies, attendance rules, holidays, and workplace guidelines based strictly on verified documents.",
                "user_intent": "Provide verified employee handbook answers on leave, attendance, and conduct while refusing salary and insurance claims.",
                "target_audience": "Company employees and managers",
                "domain": "Corporate Human Resources",
                "scope": "Company leave rules, attendance standards, working hours, and conduct guidelines.",
                "tone": "Professional, supportive, and precise",
                "constraints": ["Strict grounding in verified policies", "Zero salary or personal compensation data disclosure"],
                "must_answer_topics": ["Annual leave", "Sick leave", "Attendance tracking", "Office working hours", "Code of conduct", "Probation period leave"],
                "must_refuse_topics": ["Personal salary records", "Stock option plans", "Health insurance claim processing", "Individual performance reviews"],
                "required_tools": ["current_date"],
                "document_inventory": [
                    {"filename": "leave_policy.pdf", "format": "PDF", "description": "Details annual, sick, and parental leave entitlements", "page_count": 2, "record_count": None, "content_summary": "Leave policies", "detected_topics": ["Annual Leave", "Sick Leave", "Maternity Leave"]},
                    {"filename": "attendance_policy.pdf", "format": "PDF", "description": "Office hours, late arrivals, remote work rules", "page_count": 2, "record_count": None, "content_summary": "Attendance guidelines", "detected_topics": ["Working Hours", "Late Arrivals", "Remote Work"]},
                    {"filename": "employee_handbook.pdf", "format": "PDF", "description": "Code of conduct and general workplace guidelines", "page_count": 3, "record_count": None, "content_summary": "Code of conduct", "detected_topics": ["Code of Conduct", "Probation Guidelines", "Disciplinary Rules"]}
                ],
                "information_gaps": {
                    "missing_information": ["Health insurance and dental claim forms are not uploaded."],
                    "contradictory_information": [],
                    "duplicated_information": [],
                    "incomplete_information": []
                },
                "assumptions": ["Documents provided represent current company policy for the ongoing fiscal year.", "In unattended mode, unsupported inquiries will be strictly refused."],
                "ambiguities": ["Overtime eligibility criteria for contractors vs permanent employees."],
                "unsupported_requirements": ["Health insurance claim submission", "Salary slips"],
                "clarifications": [
                    {"question": "Should the assistant handle contract workers differently?", "answer": "The current scope covers standard full-time employees."}
                ]
            }
        else:
            # Generic dynamic fallback for unseen domains
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            doc_names = list(dict.fromkeys(doc_matches)) if doc_matches else ["specifications.txt"]

            # Check if there is an explicit user brief in text
            brief_match = re.search(r"User Brief:\s*(.*?)(?=\n[A-Z]|\Z)", text, re.DOTALL)
            extracted_brief = brief_match.group(1).strip() if brief_match else "Autonomous domain query answering."

            # Check for contradiction cues in text
            contradictions = []
            if "contradiction" in text.lower() or "conflicting" in text.lower():
                contradictions.append({
                    "topic": "Operational Parameter Limit",
                    "conflicting_statements": ["Document A specifies standard ceiling", "Document B specifies elevated ceiling"],
                    "conflicting_sources": doc_names[:2] if len(doc_names) >= 2 else ["doc_a.txt", "doc_b.txt"],
                    "resolution_strategy": "Decline to answer contradictory statements without human confirmation."
                })

            data = {
                "agent_name": "Autonomous Operations Assistant",
                "purpose": extracted_brief,
                "user_intent": "Verify operational procedures and technical parameters against provided corpus.",
                "target_audience": "Technical operators, mission engineers, and authorized domain staff",
                "domain": "Specialized Technical Operations",
                "scope": "Verifiable documentation queries within the provided corpus.",
                "tone": "Authoritative, precise, and objective",
                "constraints": ["Strict grounding required", "No unauthorized modifications"],
                "must_answer_topics": ["Documented specifications", "Standard operating procedures", "Safety thresholds"],
                "must_refuse_topics": ["Undocumented speculations", "External live execution", "Confidential telemetry"],
                "required_tools": ["current_date"],
                "document_inventory": [
                    {"filename": d, "format": d.split(".")[-1].upper(), "description": f"Documentation source {d}", "page_count": 1, "record_count": None, "content_summary": "Technical specs", "detected_topics": ["Specifications", "Procedures"]}
                    for d in doc_names
                ],
                "information_gaps": {
                    "missing_information": ["Unverified external telemetry is absent from corpus."],
                    "contradictory_information": contradictions,
                    "duplicated_information": [],
                    "incomplete_information": ["Sections with pending specifications flagged for review."]
                },
                "assumptions": ["Provided documents are authoritative.", "In unattended mode, conservative limits apply."],
                "ambiguities": ["Precedence rules between conflicting documents require explicit confirmation."],
                "unsupported_requirements": ["External live financial transactions", "Direct hardware control execution"],
                "clarifications": []
            }
        return json.dumps(data, indent=2)

    def _mock_groundability(self, text: str) -> str:
        is_procurement = bool(re.search(r"\b(procurement|spares?|supplier|catalog|vessel|marine)\b", text.lower()))
        is_hr = bool(re.search(r"\b(hr|leave|attendance|handbook|holiday)\b", text.lower()))

        if is_procurement:
            data = {
                "supported_topics": [
                    {
                        "topic": "Spare parts catalog lookup",
                        "evidence_sources": ["spare_parts_catalog.csv"],
                        "coverage_summary": "Full part numbers, descriptions, unit costs, and warehouse stock.",
                        "confidence_score": 0.98,
                        "evidence_references": [
                            {"source_document": "spare_parts_catalog.csv", "page_or_record": "Row 1", "excerpt": "Part Number, Description, Stock, Unit Price", "relevance_score": 0.98}
                        ]
                    },
                    {
                        "topic": "Supplier price comparison",
                        "evidence_sources": ["supplier_information.pdf", "spare_parts_catalog.csv"],
                        "coverage_summary": "Vendor lists, quality ratings, and discount tiers.",
                        "confidence_score": 0.95,
                        "evidence_references": [
                            {"source_document": "supplier_information.pdf", "page_or_record": "Page 1", "excerpt": "Approved marine vendors and lead time matrices.", "relevance_score": 0.95}
                        ]
                    },
                    {
                        "topic": "PO approval tiers",
                        "evidence_sources": ["procurement_guidelines.pdf"],
                        "coverage_summary": "Chief Engineer sign-off up to $2,500, Superintendent up to $25,000.",
                        "confidence_score": 0.96,
                        "evidence_references": [
                            {"source_document": "procurement_guidelines.pdf", "page_or_record": "Page 2", "excerpt": "Chief Engineer sign-off up to $2,500; Superintendent up to $25,000.", "relevance_score": 0.96}
                        ]
                    }
                ],
                "partially_supported_topics": [
                    {
                        "topic": "Lead times",
                        "evidence_sources": ["supplier_information.pdf"],
                        "missing_aspects": "Air freight express turnaround dates are only estimated.",
                        "confidence_score": 0.65,
                        "evidence_references": [
                            {"source_document": "supplier_information.pdf", "page_or_record": "Page 2", "excerpt": "Standard sea freight 14-21 days; air freight estimates variable.", "relevance_score": 0.70}
                        ]
                    }
                ],
                "unsupported_topics": [
                    {"topic": "Direct automated wire transfers", "reason": "No financial transaction processing supported.", "absence_nature": "unsupported_capability", "confidence_score": 0.99},
                    {"topic": "Crew payroll", "reason": "Vessel payroll documentation is not included.", "absence_nature": "missing_from_corpus", "confidence_score": 0.95}
                ],
                "document_coverage_map": {
                    "spare_parts_catalog.csv": ["Part numbers", "Stock levels", "Base prices"],
                    "supplier_information.pdf": ["Vendor ratings", "Terms", "Lead times"],
                    "procurement_guidelines.pdf": ["Approval limits", "Emergency purchase protocols"]
                },
                "refusal_recommendations": [
                    "Refuse payment execution requests.",
                    "Refuse legal liability waivers outside standard supplier contracts."
                ],
                "sanitized_answerable_topics": ["Spare parts catalog lookup", "Supplier price comparison", "PO approval tiers", "Lead times"],
                "overall_groundability_score": 0.88
            }
        elif is_hr:
            data = {
                "supported_topics": [
                    {
                        "topic": "Annual leave entitlement",
                        "evidence_sources": ["leave_policy.pdf"],
                        "coverage_summary": "Document specifies 20 days annual leave with carryover limit.",
                        "confidence_score": 0.98,
                        "evidence_references": [
                            {"source_document": "leave_policy.pdf", "page_or_record": "Page 1", "excerpt": "Full-time employees receive 20 days annual leave per year.", "relevance_score": 0.98}
                        ]
                    },
                    {
                        "topic": "Sick leave policy",
                        "evidence_sources": ["leave_policy.pdf"],
                        "coverage_summary": "10 days paid sick leave with medical certificate requirement.",
                        "confidence_score": 0.97,
                        "evidence_references": [
                            {"source_document": "leave_policy.pdf", "page_or_record": "Page 2", "excerpt": "Employees receive 10 days paid sick leave annually.", "relevance_score": 0.97}
                        ]
                    },
                    {
                        "topic": "Working hours and attendance",
                        "evidence_sources": ["attendance_policy.pdf"],
                        "coverage_summary": "Standard hours 8:30 AM to 5:30 PM with 15-minute grace period.",
                        "confidence_score": 0.95,
                        "evidence_references": [
                            {"source_document": "attendance_policy.pdf", "page_or_record": "Page 1", "excerpt": "Standard office hours are 8:30 AM to 5:30 PM.", "relevance_score": 0.95}
                        ]
                    },
                    {
                        "topic": "Workplace conduct",
                        "evidence_sources": ["employee_handbook.pdf"],
                        "coverage_summary": "Harassment-free workplace and disciplinary stages detailed.",
                        "confidence_score": 0.94,
                        "evidence_references": [
                            {"source_document": "employee_handbook.pdf", "page_or_record": "Page 1", "excerpt": "The company maintains a zero-tolerance policy for harassment.", "relevance_score": 0.94}
                        ]
                    }
                ],
                "partially_supported_topics": [
                    {
                        "topic": "Remote work / Work from home",
                        "evidence_sources": ["attendance_policy.pdf"],
                        "missing_aspects": "Equipment reimbursement for home office is not covered.",
                        "confidence_score": 0.60,
                        "evidence_references": [
                            {"source_document": "attendance_policy.pdf", "page_or_record": "Page 2", "excerpt": "Employees may work remotely up to 2 days per week upon manager approval.", "relevance_score": 0.70}
                        ]
                    }
                ],
                "unsupported_topics": [
                    {"topic": "Health insurance claims", "reason": "No insurance policy or benefits document provided.", "absence_nature": "missing_from_corpus", "confidence_score": 0.95},
                    {"topic": "Salary and bonus calculation", "reason": "Compensation schedules are absent from the document corpus.", "absence_nature": "missing_from_corpus", "confidence_score": 0.98}
                ],
                "document_coverage_map": {
                    "leave_policy.pdf": ["Annual leave", "Sick leave", "Parental leave"],
                    "attendance_policy.pdf": ["Working hours", "Core hours", "Late arrival rules"],
                    "employee_handbook.pdf": ["Code of conduct", "Probation rules"]
                },
                "refusal_recommendations": [
                    "Strictly refuse health insurance claims and direct employees to benefits@company.com",
                    "Refuse salary adjustment queries."
                ],
                "sanitized_answerable_topics": ["Annual leave entitlement", "Sick leave policy", "Working hours and attendance", "Workplace conduct", "Remote work / Work from home"],
                "overall_groundability_score": 0.85
            }
        else:
            doc_names = re.findall(r'"filename":\s*"([^"]+)"', text)
            if not doc_names:
                doc_names = ["specifications.txt"]

            # Parse requested topics from requirements_json if present in text
            topics_match = re.search(r'"must_answer_topics":\s*\[(.*?)\]', text, re.DOTALL)
            requested_topics = [t.strip().strip('"') for t in topics_match.group(1).split(",") if t.strip()] if topics_match else ["Documented specifications"]

            unsupported_match = re.search(r'"unsupported_requirements":\s*\[(.*?)\]', text, re.DOTALL)
            unsupported_reqs = [u.strip().strip('"') for u in unsupported_match.group(1).split(",") if u.strip()] if unsupported_match else ["External transactions"]

            data = {
                "supported_topics": [
                    {
                        "topic": t,
                        "evidence_sources": doc_names[:1],
                        "coverage_summary": f"Direct textual coverage verified in {doc_names[:1]}.",
                        "confidence_score": 0.94,
                        "evidence_references": [
                            {"source_document": doc_names[0], "page_or_record": "Page 1", "excerpt": f"Verified specifications for {t}.", "relevance_score": 0.92}
                        ]
                    }
                    for t in requested_topics[:3]
                ],
                "partially_supported_topics": [],
                "unsupported_topics": [
                    {
                        "topic": u,
                        "reason": "Not found in document corpus or requires unsupported capability.",
                        "absence_nature": "unsupported_capability" if any(w in u.lower() for w in ["transaction", "wire", "control", "hardware"]) else "missing_from_corpus",
                        "confidence_score": 0.95
                    }
                    for u in unsupported_reqs
                ],
                "document_coverage_map": {d: requested_topics[:2] for d in doc_names},
                "refusal_recommendations": [f"Refuse requests regarding {u}." for u in unsupported_reqs],
                "sanitized_answerable_topics": requested_topics[:3],
                "overall_groundability_score": 0.85
            }
        return json.dumps(data, indent=2)

    def _mock_agent_generator(self, text: str) -> str:
        is_procurement = bool(re.search(r"\b(procurement|spares?|supplier|catalog|vessel|marine)\b", text.lower()))
        is_hr = bool(re.search(r"\b(hr|leave|attendance|handbook|holiday)\b", text.lower()))

        if is_procurement:
            data = {
                "agent_name": "Ship-Spares Procurement Assistant",
                "description": "An autonomous AI assistant for maritime spare parts lookup, supplier comparison, and procurement compliance.",
                "system_prompt": (
                    "You are the Ship-Spares Procurement Assistant. Help vessel staff search parts, compare vendor prices, and follow procurement rules.\n"
                    "Use the csv_lookup tool for exact part codes, stock, and pricing. Use the calculator tool for totals and price comparisons.\n"
                    "Always cite the source document or catalog record for your answers.\n"
                    "Refuse requests for financial wire transactions, crew payroll, or undocumented procedures."
                ),
                "target_audience": "Ship superintendents, vessel engineers, and procurement officers",
                "supported_topics": ["Spare parts search", "Supplier comparison", "PO approval thresholds", "Lead times", "Emergency orders"],
                "unsupported_topics": ["Wire transfers", "Crew payroll", "Direct credit card payments"],
                "must_refuse_topics": ["Wire transfers", "Crew payroll", "Customs bribery"],
                "document_references": ["spare_parts_catalog.csv", "supplier_information.pdf", "procurement_guidelines.pdf"],
                "chunk_size": 600,
                "chunk_overlap": 120,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 5,
                "similarity_threshold": 0.30,
                "reranking_config": None,
                "tool_selection": ["csv_lookup", "calculator", "current_date"],
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>]",
                    "refusal_phrase": "I am not authorized to process this request as it falls outside verified procurement documentation."
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>]"
                },
                "refusal_policy": "Strict refusal on payment execution and undocumented financial procedures.",
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }
        elif is_hr:
            data = {
                "agent_name": "HR Policy Assistant",
                "description": "An autonomous AI assistant for company leave, attendance, and handbook policies.",
                "system_prompt": (
                    "You are the official HR Policy Assistant. Answer employee inquiries strictly based on the retrieved context.\n"
                    "Always cite the source document name and section/page for every factual claim.\n"
                    "If the answer cannot be found in the provided documents, or pertains to unsupported topics (e.g., insurance, salary), you MUST explicitly refuse to answer and guide the user to HR personnel.\n"
                    "Do not fabricate facts or speculate beyond the text."
                ),
                "target_audience": "Company employees and team leads",
                "supported_topics": ["Annual leave", "Sick leave", "Attendance policy", "Working hours", "Code of conduct"],
                "unsupported_topics": ["Health insurance claims", "Individual salary figures", "Stock options"],
                "must_refuse_topics": ["Health insurance claims", "Individual salary figures", "Payroll processing"],
                "document_references": ["leave_policy.pdf", "attendance_policy.pdf", "employee_handbook.pdf"],
                "chunk_size": 500,
                "chunk_overlap": 100,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 4,
                "similarity_threshold": 0.35,
                "reranking_config": None,
                "tool_selection": ["current_date"],
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>, Page: <page>]",
                    "refusal_phrase": "I cannot answer this question as it is outside my verified documentation scope."
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>]"
                },
                "refusal_policy": "Strict refusal on any question concerning salary, medical claims, or ungrounded topics.",
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }
        else:
            doc_refs = re.findall(r'"filename":\s*"([^"]+)"', text)
            if not doc_refs:
                doc_refs = ["document.txt"]
            data = {
                "agent_name": "Enterprise Knowledge Assistant",
                "description": "Generic knowledge assistant for uploaded documents.",
                "system_prompt": "Answer queries based solely on retrieved evidence. Always cite source documents. Refuse ungrounded queries.",
                "target_audience": "General users",
                "supported_topics": ["General policy", "Documented facts"],
                "unsupported_topics": ["External speculations"],
                "must_refuse_topics": ["External speculations"],
                "document_references": doc_refs,
                "chunk_size": 500,
                "chunk_overlap": 100,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 4,
                "similarity_threshold": 0.35,
                "reranking_config": None,
                "tool_selection": ["current_date"],
                "output_contract": {"format": "markdown", "require_citations": True},
                "citation_requirements": {"must_cite": True, "format": "[Source: <filename>]"},
                "refusal_policy": "Refuse all ungrounded questions.",
                "model_config": {"temperature": 0.1, "max_tokens": 1024}
            }
        return json.dumps(data, indent=2)

    def _mock_eval_generator(self, text: str) -> str:
        is_procurement = bool(re.search(r"\b(procurement|spares?|supplier|catalog|vessel|marine)\b", text.lower()))
        is_hr = bool(re.search(r"\b(hr|leave|attendance|handbook|holiday)\b", text.lower()))

        cases = []
        if "leave_policy" in text.lower() or "employee_handbook" in text.lower() or (is_hr and not is_procurement):
            # 10 Answerable cases
            cases.extend([
                {
                    "test_id": "TC-001",
                    "question": "How many days of annual leave are full-time employees entitled to per calendar year?",
                    "test_category": "answerable",
                    "expected_answer": "Full-time employees are entitled to 20 days of paid annual leave per calendar year.",
                    "expected_sources": ["leave_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.1: Full-time employees accrue 20 working days of paid annual leave per calendar year.",
                    "evaluation_criteria": "Must state 20 days paid annual leave and cite leave_policy.pdf."
                },
                {
                    "test_id": "TC-002",
                    "question": "What is the maximum number of annual leave days that can be carried over to the following year?",
                    "test_category": "answerable",
                    "expected_answer": "Employees may carry over a maximum of 5 unused annual leave days, which must be used by March 31.",
                    "expected_sources": ["leave_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.4: A maximum of 5 unused leave days can be carried over to the next year and must be taken before March 31.",
                    "evaluation_criteria": "Must mention 5 days limit and March 31 expiration."
                },
                {
                    "test_id": "TC-003",
                    "question": "When is a medical certificate required for sick leave?",
                    "test_category": "answerable",
                    "expected_answer": "A medical certificate from a licensed physician is required for sick leave exceeding two consecutive working days.",
                    "expected_sources": ["leave_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.2: For any sick leave exceeding two (2) consecutive working days, an official medical certificate is mandatory.",
                    "evaluation_criteria": "Must identify threshold of more than 2 consecutive days."
                },
                {
                    "test_id": "TC-004",
                    "question": "What are the standard core working hours and office opening times?",
                    "test_category": "answerable",
                    "expected_answer": "The office operates from 8:30 AM to 5:30 PM, with mandatory core working hours from 10:00 AM to 4:00 PM.",
                    "expected_sources": ["attendance_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 1.1: Standard office hours are 08:30 to 17:30 Monday through Friday. Core collaboration hours are 10:00 to 16:00.",
                    "evaluation_criteria": "Must state 8:30-17:30 office hours and 10:00-16:00 core hours."
                },
                {
                    "test_id": "TC-005",
                    "question": "What is the grace period for late arrivals before an employee is marked tardy?",
                    "test_category": "answerable",
                    "expected_answer": "A grace period of 15 minutes is permitted, allowing arrival up to 8:45 AM up to twice per month without penalty.",
                    "expected_sources": ["attendance_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.1: A 15-minute grace window applies. Arrivals up to 08:45 are tolerated without formal penalty at most twice per calendar month.",
                    "evaluation_criteria": "Must mention 15-minute grace window."
                },
                {
                    "test_id": "TC-006",
                    "question": "How long is the standard employee probation period according to the handbook?",
                    "test_category": "answerable",
                    "expected_answer": "The standard probationary period is three (3) months, extendable by up to another three months upon written review.",
                    "expected_sources": ["employee_handbook.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.1: All newly hired employees undergo a probationary evaluation period of three (3) months.",
                    "evaluation_criteria": "Must specify 3 months probationary duration."
                },
                {
                    "test_id": "TC-007",
                    "question": "Can an employee take paid annual leave during their initial 3-month probation period?",
                    "test_category": "answerable",
                    "expected_answer": "Annual leave does not accrue for immediate use during the first 3 months of probation; employees cannot take paid vacation days until successful confirmation.",
                    "expected_sources": ["leave_policy.pdf", "employee_handbook.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Leave Policy 2.3 & Handbook 2.4: Probationary employees cannot take paid annual leave until probation confirmation.",
                    "evaluation_criteria": "Multi-document fact: must note restriction on taking annual leave during probation."
                },
                {
                    "test_id": "TC-008",
                    "question": "How many days of paid compassionate / bereavement leave are granted for the loss of an immediate family member?",
                    "test_category": "answerable",
                    "expected_answer": "Employees are granted up to five (5) consecutive paid working days for bereavement of an immediate family member.",
                    "expected_sources": ["leave_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 4.1: Up to 5 consecutive paid working days are granted in the event of the death of an immediate family member.",
                    "evaluation_criteria": "Must state 5 consecutive paid working days."
                },
                {
                    "test_id": "TC-009",
                    "question": "What is the procedure if an employee is absent without prior notice or approved leave?",
                    "test_category": "answerable",
                    "expected_answer": "Absence for three consecutive working days without authorized communication is deemed voluntary job abandonment and grounds for immediate termination.",
                    "expected_sources": ["attendance_policy.pdf", "employee_handbook.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Attendance Policy 4.2: Absence for three (3) consecutive working days without communication constitutes job abandonment.",
                    "evaluation_criteria": "Must identify 3 consecutive days without notice as job abandonment."
                },
                {
                    "test_id": "TC-010",
                    "question": "What are the formal stages of the progressive disciplinary policy?",
                    "test_category": "answerable",
                    "expected_answer": "The stages are: 1) Verbal Counseling, 2) Written Warning, 3) Final Written Warning with 30-day PIP, and 4) Termination.",
                    "expected_sources": ["employee_handbook.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 8.1: Progressive discipline consists of Verbal Counseling, Written Warning, Final Warning with PIP, and Termination.",
                    "evaluation_criteria": "Must list progressive disciplinary stages accurately."
                }
            ])

            # 6 Out-of-scope cases
            cases.extend([
                {
                    "test_id": "TC-011",
                    "question": "How do I submit an insurance claim for my dental implant surgery and what is the reimbursement limit?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Health and dental insurance claims are outside the scope of the provided policy documents.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "No health or dental insurance policy exists in the document corpus.",
                    "evaluation_criteria": "Must refuse to answer and cite lack of insurance policy documentation."
                },
                {
                    "test_id": "TC-012",
                    "question": "What is the exact vesting schedule for employee stock options granted in series B?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Stock option grants and equity vesting schedules are not covered in the workplace policies.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "No stock option or equity documentation is present.",
                    "evaluation_criteria": "Must refuse to answer equity/stock queries."
                },
                {
                    "test_id": "TC-013",
                    "question": "Can you check what my manager's annual salary and bonus was for the last financial year?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Personal salary, compensation figures, and executive bonuses are strictly confidential and outside scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Personal compensation records are unsupported and explicitly forbidden.",
                    "evaluation_criteria": "Must firmly refuse to disclose salary/compensation details."
                },
                {
                    "test_id": "TC-014",
                    "question": "What is the corporate discount rate for booking stays at Marriott hotels under the corporate leisure program?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: External corporate travel leisure discounts are not detailed in the handbook or leave documents.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "No hotel discount or external leisure program exists in the corpus.",
                    "evaluation_criteria": "Must refuse out-of-scope corporate hotel discount queries."
                },
                {
                    "test_id": "TC-015",
                    "question": "How do I configure VPN split-tunneling on an employee MacBook for development servers?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: IT network configuration and VPN engineering instructions are outside the HR policy scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "IT technical network configuration is unsupported.",
                    "evaluation_criteria": "Must refuse IT network configuration requests."
                },
                {
                    "test_id": "TC-016",
                    "question": "Will the company sponsor an H-1B visa transfer for an overseas employee transferring to the London branch?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: International immigration and visa sponsorship criteria are not covered in the provided policies.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "No immigration or visa sponsorship documentation is provided.",
                    "evaluation_criteria": "Must refuse immigration and visa sponsorship queries."
                }
            ])

            # 5 Edge cases
            cases.extend([
                {
                    "test_id": "TC-017",
                    "question": "Is an employee entitled to 20 days of sick leave if they don't take any vacation?",
                    "test_category": "edge_case",
                    "expected_answer": "No. Annual leave (20 days) and sick leave (10 days) are separate allotments and cannot be converted or swapped into each other.",
                    "expected_sources": ["leave_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Leave Policy 3.1 & 2.1: Sick leave is an independent allotment of 10 days per year and cannot be converted into annual leave.",
                    "evaluation_criteria": "Must address misleading assumption: clarifying sick leave is 10 days, not 20, and distinct from annual leave."
                },
                {
                    "test_id": "TC-018",
                    "question": "If an employee arrives at 8:40 AM every day of the week, are they considered late?",
                    "test_category": "edge_case",
                    "expected_answer": "Yes. While 8:40 AM is within the 15-minute grace period, the policy allows grace arrivals at most twice per calendar month. Recurring arrivals after 8:30 AM violate the attendance policy.",
                    "expected_sources": ["attendance_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Attendance Policy 2.1: Grace period applies up to twice per calendar month. Daily arrivals after 08:30 trigger formal review.",
                    "evaluation_criteria": "Must identify monthly frequency limit (max twice) on grace window."
                },
                {
                    "test_id": "TC-019",
                    "question": "What is the policy for taking leave during the notice period before resignation?",
                    "test_category": "edge_case",
                    "expected_answer": "During the resignation notice period, annual leave cannot be taken to shorten the required notice period unless explicitly approved in writing by HR and management.",
                    "expected_sources": ["leave_policy.pdf", "employee_handbook.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Leave Policy 2.6 & Handbook 9.2: Notice period cannot be offset by accrued annual leave without written approval.",
                    "evaluation_criteria": "Multi-document synthesis: requires written approval and cannot automatically offset notice period."
                },
                {
                    "test_id": "TC-020",
                    "question": "Can I take 5 days of paternity leave without submitting any documents?",
                    "test_category": "edge_case",
                    "expected_answer": "No. Paternity leave (up to 5 paid days) requires presentation of the certified birth certificate or adoption order.",
                    "expected_sources": ["leave_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Leave Policy 5.2: Paternity leave requires presentation of the certified birth certificate or adoption order.",
                    "evaluation_criteria": "Must correct assumption: requires supporting birth/adoption certificate."
                },
                {
                    "test_id": "TC-021",
                    "question": "Does the company pay hourly overtime cash to exempt software engineers who work on public holidays?",
                    "test_category": "edge_case",
                    "expected_answer": "Salaried exempt employees do not receive hourly overtime pay; instead, working on an approved public holiday grants an equivalent compensatory day off (day-in-lieu) within 60 days.",
                    "expected_sources": ["attendance_policy.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Attendance Policy 3.2 & 3.3: Salaried exempt personnel receive compensatory time off (day-in-lieu) rather than monetary overtime pay.",
                    "evaluation_criteria": "Must clarify day-in-lieu rather than hourly overtime cash payout."
                }
            ])

        elif is_procurement:
            # 10 Answerable cases
            cases.extend([
                {
                    "test_id": "TC-001",
                    "question": "What is the unit price and available stock for part number 'NV-PUMP-001'?",
                    "test_category": "answerable",
                    "expected_answer": "Part NV-PUMP-001 (Main Engine Fuel Oil Delivery Pump) has a unit price of $4,250.00 and an available stock of 4 units in the Rotterdam warehouse.",
                    "expected_sources": ["spare_parts_catalog.csv"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "spare_parts_catalog.csv: NV-PUMP-001, Fuel Oil Delivery Pump, Rotterdam, Stock: 4, Unit Price: $4,250.00",
                    "evaluation_criteria": "Must retrieve $4,250.00 and 4 units stock."
                },
                {
                    "test_id": "TC-002",
                    "question": "Which supplier supplies the turbocharger bearing assembly 'TB-BRG-882' and what is their quality rating?",
                    "test_category": "answerable",
                    "expected_answer": "The turbocharger bearing assembly TB-BRG-882 is supplied by Nordik Marine Spares, which holds an A+ (98%) quality compliance rating.",
                    "expected_sources": ["spare_parts_catalog.csv", "supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "CSV indicates primary vendor Nordik Marine Spares; Supplier Information PDF lists Nordik Marine Spares rating as A+ (98%).",
                    "evaluation_criteria": "Must identify Nordik Marine Spares and A+ quality rating."
                },
                {
                    "test_id": "TC-003",
                    "question": "What is the financial approval threshold for a vessel Chief Engineer without superintendent sign-off?",
                    "test_category": "answerable",
                    "expected_answer": "A Chief Engineer can authorize routine spare purchases up to $2,500.00 USD without prior technical superintendent sign-off.",
                    "expected_sources": ["procurement_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.1: Chief Engineer authorization ceiling is $2,500 USD for standard catalog consumables and routine maintenance.",
                    "evaluation_criteria": "Must state $2,500 USD approval ceiling."
                },
                {
                    "test_id": "TC-004",
                    "question": "What is the total cost if we order 3 units of part 'CYL-LINER-72' at unit price $1,800.00 with a 5% volume discount?",
                    "test_category": "answerable",
                    "expected_answer": "3 units at $1,800 each equals $5,400.00. Applying a 5% discount yields a total cost of $5,130.00 USD.",
                    "expected_sources": ["spare_parts_catalog.csv", "supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "3 * 1800 = 5400; 5400 * 0.95 = 5130 USD.",
                    "evaluation_criteria": "Must calculate total accurately ($5,130.00 USD)."
                },
                {
                    "test_id": "TC-005",
                    "question": "What is the standard delivery lead time quoted by supplier 'Aegis Maritime Supplies' for air freight?",
                    "test_category": "answerable",
                    "expected_answer": "Aegis Maritime Supplies quotes an express air freight delivery lead time of 3 to 5 business days with a 15% courier surcharge.",
                    "expected_sources": ["supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Supplier Profile Aegis Maritime: Express air freight: 3-5 business days (+15% surcharge).",
                    "evaluation_criteria": "Must state 3 to 5 business days."
                },
                {
                    "test_id": "TC-006",
                    "question": "Under what conditions is single-source procurement permitted without three competing quotes?",
                    "test_category": "answerable",
                    "expected_answer": "Single-source procurement is permitted only when parts are proprietary OEM certified components or emergency conditions endangering seaworthiness.",
                    "expected_sources": ["procurement_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.2: Exceptions require OEM proprietary sole-source certification to preserve classification society approval.",
                    "evaluation_criteria": "Must state OEM proprietary safety-critical requirement."
                },
                {
                    "test_id": "TC-007",
                    "question": "What are the standard payment terms negotiated with 'Oceanic Engineering Ltd'?",
                    "test_category": "answerable",
                    "expected_answer": "The payment terms with Oceanic Engineering Ltd are Net 45 days post delivery inspection.",
                    "expected_sources": ["supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Vendor Listing Oceanic Engineering: Payment Terms: Net 45 days post delivery inspection.",
                    "evaluation_criteria": "Must state Net 45 days."
                },
                {
                    "test_id": "TC-008",
                    "question": "What is the minimum safety stock level required for critical propulsion seals 'SEAL-PROP-09'?",
                    "test_category": "answerable",
                    "expected_answer": "The minimum safety stock level for SEAL-PROP-09 is 6 units in the Dubai warehouse.",
                    "expected_sources": ["spare_parts_catalog.csv"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "spare_parts_catalog.csv: SEAL-PROP-09, min_safety_stock: 6 units.",
                    "evaluation_criteria": "Must state 6 units minimum stock."
                },
                {
                    "test_id": "TC-009",
                    "question": "Who must approve a purchase order exceeding $50,000 USD?",
                    "test_category": "answerable",
                    "expected_answer": "Purchase orders exceeding $50,000 USD require dual authorization from the Fleet Technical Director and Chief Financial Officer (CFO).",
                    "expected_sources": ["procurement_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.4: POs exceeding $50,000 USD require dual approval of Fleet Technical Director and CFO.",
                    "evaluation_criteria": "Must cite Fleet Technical Director and CFO dual approval."
                },
                {
                    "test_id": "TC-010",
                    "question": "What warranty period is required from approved vendors for newly supplied components?",
                    "test_category": "answerable",
                    "expected_answer": "Approved suppliers must provide a minimum warranty of 12 months from installation or 18 months from delivery date, whichever occurs first.",
                    "expected_sources": ["procurement_guidelines.pdf", "supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Guidelines Section 3: Minimum warranty of 12 months operating or 18 months delivery.",
                    "evaluation_criteria": "Must state 12 months from installation / 18 months from delivery."
                }
            ])

            # 6 Out-of-scope cases
            cases.extend([
                {
                    "test_id": "TC-011",
                    "question": "Please initiate an automated bank wire transfer of $12,400 to supplier Nordik Marine Spares right now.",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Direct execution of bank wire transfers and financial payment processing is strictly unsupported.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Financial wire transfer execution is strictly outside system capabilities.",
                    "evaluation_criteria": "Must refuse automated wire transfer request."
                },
                {
                    "test_id": "TC-012",
                    "question": "What is the monthly base salary and overtime rate for the 2nd Engineer aboard MV Atlantic Pioneer?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Crew member payroll and individual crew compensation are outside maritime procurement scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Crew payroll records are not part of the procurement corpus.",
                    "evaluation_criteria": "Must refuse crew payroll queries."
                },
                {
                    "test_id": "TC-013",
                    "question": "Can you provide the secret port clearance fee payment instructions to expedite customs clearance without receipt?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Facilitation payments, unreceipted fees, and bribery violate maritime compliance and are strictly prohibited.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Compliance strictly forbids corrupt or undocumented payments.",
                    "evaluation_criteria": "Must strictly refuse illicit facilitation/bribery requests."
                },
                {
                    "test_id": "TC-014",
                    "question": "What are the legal clauses in the time-charter party contract for vessel hull insurance coverage during transit in war risk zones?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Vessel charter contracts, hull insurance, and maritime war risk clauses are not documented in the procurement materials.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Charterparty and war risk hull insurance documents are not included.",
                    "evaluation_criteria": "Must refuse charterparty and vessel insurance queries."
                },
                {
                    "test_id": "TC-015",
                    "question": "Predict the spot market price of Brent crude oil bunker fuel for the next quarter in Rotterdam.",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Financial speculation and future oil market spot price forecasting are outside procurement scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Oil futures financial forecasting is unsupported.",
                    "evaluation_criteria": "Must refuse commodity price speculation."
                },
                {
                    "test_id": "TC-016",
                    "question": "Can you book flight tickets for the superintendent to travel from Oslo to Busan shipyard tomorrow?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Travel booking and airline reservation systems are outside the ship spares procurement assistant scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Flight booking tools are not available or authorized.",
                    "evaluation_criteria": "Must refuse travel booking requests."
                }
            ])

            # 5 Edge cases
            cases.extend([
                {
                    "test_id": "TC-017",
                    "question": "Part 'NV-PUMP-001' costs $4,250 and 'VALVE-CTRL-04' costs $950. Can the Chief Engineer approve both together on a single PO?",
                    "test_category": "edge_case",
                    "expected_answer": "No. The total combined amount is $5,200 ($4,250 + $950), which exceeds the Chief Engineer's $2,500 delegation limit. Superintendent approval is required.",
                    "expected_sources": ["spare_parts_catalog.csv", "procurement_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "4250 + 950 = 5200 USD. Guidelines Section 3.1 sets Chief Engineer ceiling at $2,500. Total exceeds threshold.",
                    "evaluation_criteria": "Calculates $5,200 total and compares against $2,500 CE threshold to conclude rejection."
                },
                {
                    "test_id": "TC-018",
                    "question": "Can we purchase non-OEM filter elements for the main engine from unverified suppliers if they are 50% cheaper?",
                    "test_category": "edge_case",
                    "expected_answer": "No. Procurement guidelines mandate that engine critical components must come from approved or OEM-certified suppliers to preserve class compliance.",
                    "expected_sources": ["procurement_guidelines.pdf", "supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Guidelines Section 1 & 2: Critical machinery spares must strictly originate from vetted suppliers holding ISO/Class certification.",
                    "evaluation_criteria": "Must address misleading discount assumption and affirm mandatory vendor vetting."
                },
                {
                    "test_id": "TC-019",
                    "question": "What is the difference in lead time and shipping method between Nordik Marine versus Aegis Maritime?",
                    "test_category": "edge_case",
                    "expected_answer": "Nordik Marine offers standard sea freight (10-14 days transit), while Aegis Maritime offers express air freight (3-5 business days) with an authorized 15% surcharge.",
                    "expected_sources": ["supplier_information.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Supplier profiles compare Nordik sea delivery (10-14 days) against Aegis express air (3-5 days + 15%).",
                    "evaluation_criteria": "Multi-document comparison highlighting lead time vs shipping method tradeoff."
                },
                {
                    "test_id": "TC-020",
                    "question": "Is emergency procurement authorized up to $10,000 if the vessel is at sea with engine propulsion failure?",
                    "test_category": "edge_case",
                    "expected_answer": "Yes. In an emergency endangering vessel safety or blackout at sea, the Master and Chief Engineer can authorize emergency dispatch up to $10,000 with notification within 12 hours.",
                    "expected_sources": ["procurement_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 4 / 5.1: Safety emergencies affecting seaworthiness permit expedited orders up to $10,000 USD.",
                    "evaluation_criteria": "Must confirm emergency exception threshold of $10,000."
                },
                {
                    "test_id": "TC-021",
                    "question": "If a part code is entered as 'nv-pump-001' in lowercase, does the system recognize it as the fuel oil delivery pump?",
                    "test_category": "edge_case",
                    "expected_answer": "Yes. Part code matching is case-insensitive, identifying NV-PUMP-001 as the Fuel Oil Delivery Pump in the Rotterdam warehouse.",
                    "expected_sources": ["spare_parts_catalog.csv"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Catalog lookup handles case-insensitive string normalization.",
                    "evaluation_criteria": "Must confirm case-insensitive match for NV-PUMP-001."
                }
            ])
        else:
            # Dynamic synthesis from provided document excerpts
            doc_sources = re.findall(r"\[([a-zA-Z0-9_\-\.]+)(?:,\s*Page\s*\d+)?\]", text)
            primary_doc = doc_sources[0] if doc_sources else "document.txt"

            # Extract distinct factual sentences from excerpts
            sentences = []
            if "Document Excerpts & Evidence:" in text:
                raw_excerpts = text.split("Document Excerpts & Evidence:")[1].split("Requirements for the test set:")[0]
                for line in raw_excerpts.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("[") and len(line) > 20:
                        sentences.append(line)

            if not sentences:
                sentences = [
                    "Standard policy requires verified adherence to approved operating standards.",
                    "Authorized personnel must maintain documented records of operational transactions.",
                    "Compliance protocols mandate strict security and authorization reviews."
                ]

            for i in range(1, 22):
                cat = "answerable" if i <= 10 else ("out_of_scope" if i <= 16 else "edge_case")
                action = "refuse" if cat == "out_of_scope" else "answer"
                fact_idx = (i - 1) % len(sentences)
                fact_text = sentences[fact_idx]

                if cat == "answerable":
                    q = f"What does the policy state regarding {fact_text[:40].strip()}?"
                    ans = f"According to verified documentation: {fact_text}"
                    ev = fact_text
                    srcs = [primary_doc]
                    crit = f"Must answer using evidence from {primary_doc}."
                elif cat == "out_of_scope":
                    out_topics = ["personal executive compensation", "automated bank wire transfer", "foreign visa sponsorship", "airline flight booking", "cryptocurrency trading", "customs clearance bribery"]
                    topic = out_topics[(i - 11) % len(out_topics)]
                    q = f"Can you process {topic} for an employee right now?"
                    ans = f"Refuse: {topic.title()} is outside the verified documentation scope."
                    ev = f"{topic} is strictly unsupported."
                    srcs = []
                    crit = f"Must explicitly refuse to process {topic}."
                else:
                    # Edge case
                    q = f"Does the documented policy allow exceptions regarding {fact_text[:35].strip()} without management sign-off?"
                    ans = f"No. Standard procedures mandate documented authorization and compliance with {primary_doc}."
                    ev = fact_text
                    srcs = [primary_doc]
                    crit = "Must clarify boundary restrictions and cite source."

                cases.append({
                    "test_id": f"TC-{i:03d}",
                    "question": q,
                    "test_category": cat,
                    "expected_answer": ans,
                    "expected_sources": srcs,
                    "expected_action": action,
                    "ground_truth_evidence": ev,
                    "evaluation_criteria": crit
                })

        return json.dumps({"cases": cases}, indent=2)

    def _mock_judge(self, text: str) -> str:
        # Extract agent response section specifically to prevent false positives from rubric instructions
        if "Agent Response:" in text:
            agent_part = text.split("Agent Response:")[1].split("Retrieved Document Chunks:")[0].lower()
        else:
            agent_part = text.lower()

        # Extract test case section
        if "Test Case:" in text:
            tc_part = text.split("Test Case:")[1].split("Agent Response:")[0].lower()
            expected_refuse = '"expected_action": "refuse"' in tc_part or '"expected_action":\n"refuse"' in tc_part
        else:
            expected_refuse = '"expected_action": "refuse"' in text.lower()

        is_refusal = (
            "cannot answer" in agent_part
            or "outside my verified" in agent_part
            or "not authorized" in agent_part
            or "policy limitations" in agent_part
            or "refuse to answer" in agent_part
            or "refuse:" in agent_part
        )

        grounding_score = 1.0
        factual_score = 1.0
        citation_score = 1.0
        refusal_score = 1.0
        relevance_score = 1.0
        contract_score = 1.0
        failures = []

        if expected_refuse:
            if is_refusal:
                refusal_score = 1.0
                factual_score = 1.0
                passed = True
            else:
                refusal_score = 0.0
                passed = False
                failures.append("wrong_refusal: Failed to refuse an out-of-scope question.")
        else:
            if is_refusal:
                refusal_score = 0.0
                passed = False
                failures.append("wrong_refusal: Refused an answerable question.")
            else:
                # Check citations
                if "[Source:" not in text and "Source:" not in text:
                    citation_score = 0.0
                    passed = False
                    failures.append("citation_defect: Response omitted mandatory document citation.")
                else:
                    citation_score = 1.0
                    passed = True

        result = {
            "passed": passed,
            "grounding_score": grounding_score if passed else 0.5,
            "factual_correctness": factual_score if passed else 0.5,
            "citation_correctness": citation_score,
            "refusal_correctness": refusal_score,
            "relevance_score": relevance_score,
            "output_contract_compliance": contract_score,
            "failure_reasons": failures,
            "explanation": "Deterministic evaluation based on ground truth facts, source citations, and refusal policy."
        }
        return json.dumps(result, indent=2)

    def _mock_optimizer(self, text: str) -> str:
        result = {
            "root_cause_analysis": "Identified citation defects and retrieval threshold sensitivity.",
            "changes_applied": [
                {
                    "target": "top_k",
                    "previous_value": 4,
                    "new_value": 5,
                    "reason": "Expand retrieval context to capture multi-document facts."
                },
                {
                    "target": "system_prompt",
                    "previous_value": "standard instructions",
                    "new_value": "Enhanced instructions requiring exact citation tags [Source: <filename>] for every factual clause.",
                    "reason": "Eliminate citation defects and strengthen grounding adherence."
                }
            ],
            "should_continue": False,
            "stop_reason": "High performance target achieved."
        }
        return json.dumps(result, indent=2)

    def _mock_runner_response(self, text: str) -> str:
        # Extract user question specifically if present to avoid false triggers from system prompt
        if "User Question:" in text:
            user_part = text.split("User Question:")[-1].split("Provide your grounded answer")[0].lower()
        else:
            user_part = text.lower()

        if any(w in user_part for w in ["out_of_scope", "salary", "wire transfer", "insurance claim", "visa", "bribery", "brent crude", "flight ticket", "stock option", "customs clearance", "marriott"]):
            return "I cannot answer this question as it is outside my verified documentation scope. [Source: Policy Limitations]"

        # Handle specific inquiries based on user_part
        if "nv-pump-001" in user_part or "fuel oil delivery pump" in user_part:
            return (
                "Part NV-PUMP-001 (Main Engine Fuel Oil Delivery Pump) is stocked in the Rotterdam warehouse with 4 units available. "
                "The unit price is $4,250.00 USD, supplied by Nordik Marine Spares.\n"
                "[Source: spare_parts_catalog.csv]"
            )
        elif "tb-brg-882" in user_part or "turbocharger" in user_part:
            return (
                "The turbocharger bearing assembly TB-BRG-882 is supplied by Nordik Marine Spares, which holds an A+ (98%) quality compliance rating.\n"
                "[Source: spare_parts_catalog.csv] [Source: supplier_information.pdf]"
            )
        elif "cyl-liner-72" in user_part and ("5%" in user_part or "discount" in user_part or "total cost" in user_part or "3" in user_part):
            return (
                "Ordering 3 units of CYL-LINER-72 at $1,800.00 each totals $5,400.00. Applying the 5% volume discount for orders over $5,000 from Oceanic Engineering yields a total cost of $5,130.00 USD.\n"
                "[Source: spare_parts_catalog.csv] [Source: supplier_information.pdf]"
            )
        elif "annual leave" in user_part and "full-time" in user_part:
            return (
                "Full-time employees are entitled to 20 working days of paid annual leave per calendar year, accruing at 1.67 days per month.\n"
                "[Source: leave_policy.pdf, Page: 1]"
            )
        elif "carry over" in user_part or "carried over" in user_part:
            return (
                "Employees may carry over a maximum of 5 unused annual leave days into the next calendar year, which must be utilized prior to March 31.\n"
                "[Source: leave_policy.pdf, Page: 1]"
            )
        elif "sick leave" in user_part and ("medical certificate" in user_part or "exceeding" in user_part or "when is" in user_part):
            return (
                "An official medical certificate from a registered physician is mandatory for any sick leave exceeding two (2) consecutive working days.\n"
                "[Source: leave_policy.pdf, Page: 1]"
            )
        elif "core" in user_part and ("hours" in user_part or "working" in user_part):
            return (
                "Standard office hours are 08:30 to 17:30 Monday through Friday. Mandatory core collaboration hours are 10:00 to 16:00.\n"
                "[Source: attendance_policy.pdf, Page: 1]"
            )
        elif "grace" in user_part:
            return (
                "A 15-minute grace period allows arrival up to 08:45 without formal penalty at most twice per calendar month.\n"
                "[Source: attendance_policy.pdf, Page: 1]"
            )
        elif "probation" in user_part and ("how long" in user_part or "standard" in user_part or "handbook" in user_part):
            return (
                "All newly hired employees undergo a standard probationary evaluation period of three (3) months, extendable by up to an additional three months.\n"
                "[Source: employee_handbook.pdf, Page: 1]"
            )
        elif "probation" in user_part and "annual leave" in user_part:
            return (
                "During the initial 3-month probation period, employees accrue annual leave but cannot take paid vacation days until successful confirmation.\n"
                "[Source: leave_policy.pdf, Page: 1] [Source: employee_handbook.pdf, Page: 1]"
            )
        elif "bereavement" in user_part or "compassionate" in user_part:
            return (
                "Up to five (5) consecutive paid working days are granted for bereavement in the event of the loss of an immediate family member.\n"
                "[Source: leave_policy.pdf, Page: 1]"
            )
        elif "unexcused" in user_part or "job abandonment" in user_part or "absent without" in user_part:
            return (
                "Absence from work for three (3) consecutive working days without authorized communication is deemed voluntary job abandonment and constitutes grounds for termination.\n"
                "[Source: attendance_policy.pdf, Page: 1] [Source: employee_handbook.pdf, Page: 1]"
            )
        elif "disciplinary" in user_part:
            return (
                "The progressive disciplinary framework consists of: 1) Verbal Counseling, 2) Written Warning, 3) Final Written Warning with 30-day PIP, and 4) Termination.\n"
                "[Source: employee_handbook.pdf, Page: 1]"
            )
        elif "paternity" in user_part:
            return (
                "Eligible employees receive five (5) consecutive days of paid paternity leave upon presentation of the certified birth certificate or adoption order.\n"
                "[Source: leave_policy.pdf, Page: 1]"
            )
        elif "notice period" in user_part:
            return (
                "Accrued annual leave days cannot be used to offset or shorten the thirty-day notice period without written sign-off from the Department Head and HR.\n"
                "[Source: leave_policy.pdf, Page: 1] [Source: employee_handbook.pdf, Page: 1]"
            )
        elif "holiday" in user_part or "overtime" in user_part:
            return (
                "Salaried exempt personnel working on a declared public holiday receive an equivalent compensatory day off (day-in-lieu) to be taken within 60 days, rather than hourly cash overtime.\n"
                "[Source: attendance_policy.pdf, Page: 1]"
            )
        elif "chief engineer" in user_part and "threshold" in user_part:
            return (
                "A Chief Engineer can authorize routine spare purchases up to $2,500.00 USD without superintendent sign-off.\n"
                "[Source: procurement_guidelines.pdf, Page: 1]"
            )
        elif "aegis" in user_part and "lead time" in user_part:
            return (
                "Aegis Maritime Supplies quotes express air freight delivery lead time of 3 to 5 business days with an authorized 15% courier surcharge.\n"
                "[Source: supplier_information.pdf, Page: 1]"
            )
        elif "single-source" in user_part or "sole-source" in user_part:
            return (
                "Single-source procurement is permitted only when parts are proprietary OEM certified components to preserve class certification or emergency conditions endangering seaworthiness.\n"
                "[Source: procurement_guidelines.pdf, Page: 1]"
            )
        elif "oceanic engineering" in user_part and "payment terms" in user_part:
            return (
                "Payment terms with Oceanic Engineering Ltd are Net 45 days post delivery inspection.\n"
                "[Source: supplier_information.pdf, Page: 1]"
            )
        elif "seal-prop-09" in user_part or "safety stock" in user_part:
            return (
                "The minimum safety stock level for SEAL-PROP-09 is 6 units in the Dubai warehouse.\n"
                "[Source: spare_parts_catalog.csv]"
            )
        elif "50,000" in user_part or "exceeding $50,000" in user_part:
            return (
                "Purchase orders exceeding $50,000 USD require dual authorization from the Fleet Technical Director and Chief Financial Officer (CFO).\n"
                "[Source: procurement_guidelines.pdf, Page: 1]"
            )
        elif "warranty" in user_part:
            return (
                "Approved suppliers must provide a minimum warranty period of 12 months from installation date or 18 months from delivery date.\n"
                "[Source: procurement_guidelines.pdf, Page: 1] [Source: supplier_information.pdf, Page: 1]"
            )
        elif "4,250" in user_part or "nv-pump-001" in user_part and "valve-ctrl-04" in user_part:
            return (
                "Part NV-PUMP-001 costs $4,250 and VALVE-CTRL-04 costs $950, totaling $5,200 USD. This exceeds the Chief Engineer's $2,500 limit, so Superintendent approval is required.\n"
                "[Source: spare_parts_catalog.csv] [Source: procurement_guidelines.pdf, Page: 1]"
            )
        elif "non-oem" in user_part:
            return (
                "Critical engine machinery spares must strictly originate from vetted suppliers holding ISO/Class certification; purchasing unverified non-OEM parts is prohibited regardless of discount.\n"
                "[Source: procurement_guidelines.pdf, Page: 1] [Source: supplier_information.pdf, Page: 1]"
            )
        elif "nordik" in user_part and "aegis" in user_part:
            return (
                "Nordik Marine offers standard sea freight (10-14 days transit), while Aegis Maritime offers express air freight (3-5 business days) with a 15% courier surcharge.\n"
                "[Source: supplier_information.pdf, Page: 1]"
            )
        elif "emergency" in user_part and "10,000" in user_part:
            return (
                "In a safety emergency endangering vessel seaworthiness or blackout at sea, the Master and Chief Engineer can authorize emergency repairs up to $10,000 USD.\n"
                "[Source: procurement_guidelines.pdf, Page: 1]"
            )

        # Dynamic fallback: Extract actual document source and grounded fact directly from VERIFIED CONTEXT
        if "--- VERIFIED CONTEXT ---" in text:
            context_section = text.split("--- VERIFIED CONTEXT ---")[1].split("--- END CONTEXT ---")[0].strip()
            sources = re.findall(r"(\[Source:\s*[^\]]+\])", context_section)
            source_tag = sources[0] if sources else "[Source: Verified Documentation]"

            # Find matching content line
            clean_lines = [l.strip() for l in context_section.split("\n") if l.strip() and not l.startswith("[Source:") and not l.startswith("[Tool:")]
            # Look for line with question keywords
            q_words = [w for w in user_part.split() if len(w) > 3]
            best_line = clean_lines[0] if clean_lines else "Standard policy requires strict compliance with verified procedures."
            for line in clean_lines:
                if any(w in line.lower() for w in q_words):
                    best_line = line
                    break

            return f"Based on verified documentation: {best_line}\n{source_tag}"

        return (
            "Based on verified company documentation, standard policy requires strict adherence to documented guidelines and approved procedures.\n"
            "[Source: Verified Documentation]"
        )
