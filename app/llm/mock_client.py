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
        if any(w in combined for w in ["AUTOMATED JUDGE", "Evaluator and Judge", "impartial", "Scoring Rubric:", "Defenses Against Evaluator Biases:"]):
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

        # 6b. Clarifying questions request
        if "clarifying questions" in combined.lower() or "formulate up to 5" in combined.lower():
            return self._mock_clarifying_questions(combined)

        # 7. Generic chat runner / question answering
        return self._mock_runner_response(combined)

    def _mock_clarifying_questions(self, text: str) -> str:
        qs = []
        if "depth" in text.lower() or "3000m" in text.lower() or "4500m" in text.lower():
            qs.append("Regarding conflicting depth specifications (3000m vs 4500m): which operational ceiling takes precedence?")
        if "incomplete" in text.lower() or "[tbd]" in text.lower():
            qs.append("The payload documentation contains incomplete [TBD] markers: should the assistant answer with conservative defaults?")
        if "ionosphere" in text.lower() or "telemetry" in text.lower():
            qs.append("The brief references atmospheric ionosphere telemetry not covered in the documents: should these requests be refused?")
        if "emergency" in text.lower() and "threshold" in text.lower():
            qs.append("Are emergency orders subject to standard threshold limits?")
        return json.dumps(qs[:5])

    def _detect_domain(self, text: str) -> str:
        t = text.lower()
        # 1. Procurement signals
        if any(d in t for d in ["spare_parts_catalog", "supplier_information", "procurement_guidelines"]) or \
           (any(w in t for w in ["procurement", "spare parts", "vessel procurement", "marine spares", "purchase order authorization", "po approval", "catalogue"]) and not any(w in t for w in ["annual leave", "sick leave", "attendance rules", "employee handbook"])):
            return "procurement"
        # 2. HR signals
        if any(d in t for d in ["leave_policy", "attendance_policy", "employee_handbook", "hr_policy"]) or \
           any(w in t for w in ["hr assistant", "human resources", "leave policies", "attendance rules", "workplace guidelines", "employee questions", "sick leave", "annual leave", "working hours"]):
            return "hr"
        # 3. Academic signals
        if any(d in t for d in ["academic_regulations", "examination_guidelines", "student_handbook"]) or \
           any(w in t for w in ["academic regulations", "university academic", "student grading", "academic probation", "graduation requirements", "examination guidelines"]):
            return "academic"
        # 4. Medical signals
        if any(d in t for d in ["clinic_handbook", "patient_privacy", "triage_guidelines"]) or \
           any(w in t for w in ["medical clinic", "triage appointment", "telehealth consultation", "patient health information", "medical record release"]):
            return "medical"
        return "generic"

    def _mock_interviewer(self, text: str) -> str:
        domain = self._detect_domain(text)

        if domain == "procurement":
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
        elif domain == "hr":
            data = {
                "agent_name": "HR Policy Assistant",
                "purpose": "Assist employees with inquiries regarding leave policies, attendance rules, holidays, and workplace guidelines based strictly on verified documents.",
                "user_intent": "Provide verified employee handbook answers on leave, attendance, and conduct while refusing salary and insurance claims.",
                "target_audience": "Company employees, managers, and HR administrators",
                "domain": "Corporate Human Resources",
                "scope": "Company leave rules, attendance standards, working hours, and conduct guidelines.",
                "tone": "Professional, supportive, and precise",
                "constraints": ["Strict grounding in verified policies", "Zero salary or personal compensation data disclosure"],
                "must_answer_topics": ["Annual leave", "Sick leave", "Attendance tracking", "Office working hours", "Code of conduct", "Probation period leave"],
                "must_refuse_topics": ["Personal salary records", "Stock option plans", "Health insurance claim processing", "Individual performance reviews", "Direct payroll execution"],
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
        elif domain == "academic":
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            doc_names = list(dict.fromkeys(doc_matches)) if doc_matches else ["academic_regulations.pdf", "student_handbook.pdf"]
            data = {
                "agent_name": "University Academic Regulations Assistant",
                "purpose": "Assist students, faculty, and academic advisors with questions regarding graduation requirements, grading scales, academic probation, examination guidelines, and student conduct based strictly on verified university documents.",
                "user_intent": "Provide verified guidance on university degree requirements, grade appeal deadlines, and probation policies while refusing unauthorized tuition or grade alterations.",
                "target_audience": "University students, academic advisors, and faculty members",
                "domain": "Higher Education Academic Affairs",
                "scope": "Degree graduation requirements, GPA calculation, academic probation rules, examination conduct, and grievance procedures.",
                "tone": "Authoritative, academic, and clear",
                "constraints": ["Strict grounding in verified academic policy manuals", "Zero grade alteration or fee waiver processing"],
                "must_answer_topics": ["Graduation requirements", "Grading scale and GPA calculation", "Academic probation rules", "Examination guidelines", "Student code of conduct"],
                "must_refuse_topics": ["Tuition fee waiver processing", "Grade tampering requests", "Financial aid disbursement", "Disciplinary hearing bypass"],
                "required_tools": ["current_date"],
                "document_inventory": [
                    {"filename": d, "format": d.split(".")[-1].upper(), "description": f"Academic regulations document {d}", "page_count": 1, "record_count": None, "content_summary": "University academic standards", "detected_topics": ["Graduation", "Grading", "Probation"]}
                    for d in doc_names
                ],
                "information_gaps": {
                    "missing_information": [],
                    "contradictory_information": [],
                    "duplicated_information": [],
                    "incomplete_information": []
                },
                "assumptions": ["Academic regulations reflect current catalog year.", "Unattended defaults apply conservative policy interpretation."],
                "ambiguities": ["Undergraduate vs graduate credit transfer reciprocity."],
                "unsupported_requirements": ["Direct transcript alteration", "Tuition fee refunds"],
                "clarifications": []
            }
        else:
            # Generic dynamic fallback for unseen domains
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            doc_names = list(dict.fromkeys(doc_matches)) if doc_matches else ["specifications.txt"]

            # Check if there is an explicit user brief in text
            brief_match = re.search(r"User Brief:\s*(.*?)(?=\n[A-Z]|\Z)", text, re.DOTALL)
            extracted_brief = brief_match.group(1).strip() if brief_match else "Autonomous domain query answering."

            # Infer agent name from user brief
            agent_name = "Autonomous Domain Assistant"
            name_m = re.search(r"(?:create|build|generate|develop)\s+(?:an?|the)?\s*([A-Za-z0-9_\-\s]{3,40}?)(?:\s+(?:assistant|agent|advisor|specialist|bot|system))", extracted_brief, re.IGNORECASE)
            if name_m:
                agent_name = " ".join(w.capitalize() for w in name_m.group(1).strip().split()) + " Assistant"
            elif bool(re.search(r"\b(hr|human resources|employee handbook)\b", extracted_brief.lower())):
                agent_name = "HR Policy Assistant"

            # Infer domain from brief and document cues
            base_agent = agent_name.replace(' Assistant', '')
            domain_title = base_agent if (base_agent.endswith("Operations") or base_agent.endswith("Management")) else f"{base_agent} Operations"
            if agent_name == "Autonomous Domain Assistant":
                domain_title = "Enterprise Operations"
            t_low = text.lower()
            if bool(re.search(r"\b(academic|student|grading|university|faculty)\b", t_low)):
                domain_title = "Higher Education Academic Affairs"
            elif bool(re.search(r"\b(clinic|medical|patient|triage|telehealth)\b", t_low)):
                domain_title = "Clinical Healthcare Administration"
            elif bool(re.search(r"\b(procurement|spares|supplier|vessel)\b", t_low)):
                domain_title = "Maritime Procurement & Supply Chain"
            elif bool(re.search(r"\b(hr|human resources|annual leave|sick leave|attendance policy)\b", t_low)):
                domain_title = "Corporate Human Resources"

            # Extract detected topics from document summary
            detected_topics = []
            for tm in re.finditer(r"Topics:\s*([^\n]+)", text):
                for part in tm.group(1).split(","):
                    p = part.strip()
                    if p and len(p) > 2 and p not in detected_topics:
                        detected_topics.append(p)
            if not detected_topics:
                detected_topics = ["Documented policies", "Standard operating procedures", "Compliance requirements"]

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
                "agent_name": agent_name,
                "purpose": extracted_brief,
                "user_intent": f"Verify and query operational guidelines and verified policies for {agent_name}.",
                "target_audience": "Authorized personnel and operational staff",
                "domain": domain_title,
                "scope": f"Verifiable documentation queries covering {', '.join(detected_topics[:4])}.",
                "tone": "Authoritative, precise, and objective",
                "constraints": ["Strict grounding required", "No unauthorized external modifications"],
                "must_answer_topics": detected_topics[:6],
                "must_refuse_topics": ["Personal confidential records", "External live execution", "Direct financial wire transactions"],
                "required_tools": ["current_date"],
                "document_inventory": [
                    {"filename": d, "format": d.split(".")[-1].upper(), "description": f"Documentation source {d}", "page_count": 1, "record_count": None, "content_summary": "Policy specifications", "detected_topics": detected_topics[:3]}
                    for d in doc_names
                ],
                "information_gaps": {
                    "missing_information": [],
                    "contradictory_information": contradictions,
                    "duplicated_information": [],
                    "incomplete_information": []
                },
                "assumptions": ["Provided documents are authoritative.", "In unattended mode, conservative limits apply."],
                "ambiguities": ["Precedence rules between conflicting documents require explicit confirmation."],
                "unsupported_requirements": ["External live financial transactions", "Direct hardware control execution"],
                "clarifications": []
            }
        return json.dumps(data, indent=2)

    def _mock_groundability(self, text: str) -> str:
        doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
        actual_docs = [d for d in dict.fromkeys(doc_matches) if d.lower() not in {"model.md", "prompt.txt"}]
        has_proc_files = any("spare_parts" in d or "procurement" in d or "supplier" in d for d in actual_docs)
        has_hr_files = any("leave" in d or "attendance" in d or "employee_handbook" in d or "hr_policy" in d for d in actual_docs)
        has_acad_files = any("academic" in d or "examination" in d or "student_code" in d for d in actual_docs)

        domain = self._detect_domain(text)
        if has_proc_files or (domain == "procurement" and not actual_docs):
            domain = "procurement"
        elif has_hr_files or (domain == "hr" and not actual_docs):
            domain = "hr"
        elif has_acad_files or (domain == "academic" and not actual_docs):
            domain = "academic"
        else:
            domain = "generic"

        if domain == "procurement":
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
        elif domain == "hr":
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
        elif domain == "academic":
            data = {
                "supported_topics": [
                    {
                        "topic": "Graduation requirements",
                        "evidence_sources": ["academic_regulations.pdf"],
                        "coverage_summary": "120 total credits, minimum 2.0 cumulative GPA, and core curriculum completion.",
                        "confidence_score": 0.98,
                        "evidence_references": [
                            {"source_document": "academic_regulations.pdf", "page_or_record": "Page 1", "excerpt": "Candidates for a bachelor degree must complete 120 credit hours with a minimum cumulative GPA of 2.0.", "relevance_score": 0.98}
                        ]
                    },
                    {
                        "topic": "Grading scale and GPA calculation",
                        "evidence_sources": ["academic_regulations.pdf"],
                        "coverage_summary": "Standard 4.0 scale: A=4.0, B=3.0, C=2.0, D=1.0, F=0.0.",
                        "confidence_score": 0.97,
                        "evidence_references": [
                            {"source_document": "academic_regulations.pdf", "page_or_record": "Page 2", "excerpt": "Grades are evaluated on a 4.0 scale: A (4.0), B (3.0), C (2.0), D (1.0), and F (0.0).", "relevance_score": 0.97}
                        ]
                    },
                    {
                        "topic": "Academic probation rules",
                        "evidence_sources": ["academic_regulations.pdf"],
                        "coverage_summary": "Students with cumulative GPA below 2.0 placed on probation for one semester.",
                        "confidence_score": 0.96,
                        "evidence_references": [
                            {"source_document": "academic_regulations.pdf", "page_or_record": "Page 2", "excerpt": "Any student falling below a cumulative GPA of 2.0 is placed on academic probation.", "relevance_score": 0.96}
                        ]
                    },
                    {
                        "topic": "Student code of conduct",
                        "evidence_sources": ["student_handbook.pdf"],
                        "coverage_summary": "Academic integrity violations, plagiarism sanctions, and hearing procedures.",
                        "confidence_score": 0.95,
                        "evidence_references": [
                            {"source_document": "student_handbook.pdf", "page_or_record": "Page 1", "excerpt": "Plagiarism and academic dishonesty result in formal hearing and disciplinary probation.", "relevance_score": 0.95}
                        ]
                    }
                ],
                "partially_supported_topics": [],
                "unsupported_topics": [
                    {"topic": "Tuition fee waiver processing", "reason": "Bursar and financial aid forms are not part of academic regulations.", "absence_nature": "missing_from_corpus", "confidence_score": 0.95},
                    {"topic": "Grade tampering requests", "reason": "Grade alterations outside formal hearing are prohibited.", "absence_nature": "unsupported_capability", "confidence_score": 0.99}
                ],
                "document_coverage_map": {
                    "academic_regulations.pdf": ["Graduation credits", "Grading scale", "Probation rules"],
                    "student_handbook.pdf": ["Academic integrity", "Plagiarism sanctions"]
                },
                "refusal_recommendations": [
                    "Strictly refuse grade modification requests outside formal grievance hearings.",
                    "Refuse tuition fee disputes and direct to student accounts."
                ],
                "sanitized_answerable_topics": ["Graduation requirements", "Grading scale and GPA calculation", "Academic probation rules", "Student code of conduct"],
                "overall_groundability_score": 0.90
            }
        else:
            if not actual_docs:
                doc_names = re.findall(r'"filename":\s*"([^"]+)"', text)
                actual_docs = doc_names if doc_names else ["specifications.txt"]

            # Parse requested topics from requirements_json if present in text
            topics_match = re.search(r'"must_answer_topics":\s*\[(.*?)\]', text, re.DOTALL)
            requested_topics = [t.strip().strip('"') for t in topics_match.group(1).split(",") if t.strip()] if topics_match else ["Documented policies"]

            unsupported_match = re.search(r'"unsupported_requirements":\s*\[(.*?)\]', text, re.DOTALL)
            unsupported_reqs = [u.strip().strip('"') for u in unsupported_match.group(1).split(",") if u.strip()] if unsupported_match else ["External transactions"]

            supported_topics_list = []
            for idx, t in enumerate(requested_topics[:6]):
                doc = actual_docs[idx % len(actual_docs)]
                supported_topics_list.append({
                    "topic": t,
                    "evidence_sources": [doc],
                    "coverage_summary": f"Direct textual coverage verified in {doc}.",
                    "confidence_score": 0.94,
                    "evidence_references": [
                        {"source_document": doc, "page_or_record": "Page 1", "excerpt": f"Verified specifications for {t}.", "relevance_score": 0.92}
                    ]
                })

            data = {
                "supported_topics": supported_topics_list,
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
                "document_coverage_map": {d: requested_topics[:2] for d in actual_docs},
                "refusal_recommendations": [f"Refuse requests regarding {u}." for u in unsupported_reqs],
                "sanitized_answerable_topics": requested_topics[:6],
                "overall_groundability_score": 0.88
            }
        return json.dumps(data, indent=2)

    def _mock_agent_generator(self, text: str) -> str:
        doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
        actual_docs = [d for d in dict.fromkeys(doc_matches) if d.lower() not in {"model.md", "prompt.txt"}]
        has_proc_files = any("spare_parts" in d or "procurement" in d or "supplier" in d for d in actual_docs)
        has_hr_files = any("leave" in d or "attendance" in d or "employee_handbook" in d or "hr_policy" in d for d in actual_docs)
        has_acad_files = any("academic" in d or "examination" in d or "student_code" in d for d in actual_docs)

        domain = self._detect_domain(text)
        if has_proc_files or (domain == "procurement" and not actual_docs):
            domain = "procurement"
        elif has_hr_files or (domain == "hr" and not actual_docs):
            domain = "hr"
        elif has_acad_files or (domain == "academic" and not actual_docs):
            domain = "academic"
        else:
            domain = "generic"

        if domain == "procurement":
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
                "chunk_size": 400,
                "chunk_overlap": 80,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 5,
                "similarity_threshold": 0.30,
                "reranking_config": {
                    "enabled": True,
                    "method": "cross_encoder",
                    "top_n": 3,
                    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                },
                "metadata_config": {
                    "tracked_fields": ["source", "page", "file_type", "total_pages"],
                    "include_in_context": True,
                    "citation_metadata_format": "[Source: <source>, Page: <page>]"
                },
                "tool_selection": ["csv_lookup", "calculator", "current_date"],
                "tool_justifications": {
                    "csv_lookup": "Structured CSV tabular spare parts catalog requires row-level querying.",
                    "calculator": "Enables unit price comparisons, threshold arithmetic, and currency totals.",
                    "current_date": "Required for verifying lead time deadlines and delivery dates."
                },
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>, Page: <page>]",
                    "refusal_phrase": "I am not authorized to process this request as it falls outside verified procurement documentation.",
                    "section_headers": ["Direct Answer", "Evidence & Citations"]
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>, Page: <page>]",
                    "granularity": "sentence_level",
                    "prohibit_unanchored_claims": True
                },
                "refusal_policy": "Strict refusal on payment execution and undocumented financial procedures.",
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }
        elif domain == "hr":
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
                "reranking_config": {
                    "enabled": True,
                    "method": "cross_encoder",
                    "top_n": 3,
                    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                },
                "metadata_config": {
                    "tracked_fields": ["source", "page", "file_type", "total_pages"],
                    "include_in_context": True,
                    "citation_metadata_format": "[Source: <source>, Page: <page>]"
                },
                "tool_selection": ["current_date"],
                "tool_justifications": {
                    "current_date": "Required for checking ongoing policy year validity and leave balance periods."
                },
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>, Page: <page>]",
                    "refusal_phrase": "I cannot answer this question as it is outside my verified documentation scope.",
                    "section_headers": ["Direct Answer", "Evidence & Citations"]
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>, Page: <page>]",
                    "granularity": "sentence_level",
                    "prohibit_unanchored_claims": True
                },
                "refusal_policy": "Strict refusal on any question concerning salary, medical claims, or ungrounded topics.",
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }
        elif domain == "academic":
            data = {
                "agent_name": "University Academic Regulations Assistant",
                "description": "An autonomous AI assistant for university degree requirements, academic probation, grading standards, and student conduct.",
                "system_prompt": (
                    "You are the University Academic Regulations Assistant. Guide students, faculty, and advisors on degree requirements, probation, and grading rules.\n"
                    "Always cite the source document and page/section for every assertion.\n"
                    "Refuse requests for grade alterations, tuition fee waivers, or disciplinary hearing bypasses."
                ),
                "target_audience": "University students, academic advisors, and faculty members",
                "supported_topics": ["Graduation requirements", "Grading scale and GPA calculation", "Academic probation rules", "Examination guidelines", "Student code of conduct"],
                "unsupported_topics": ["Tuition fee waiver processing", "Grade tampering requests", "Financial aid disbursement"],
                "must_refuse_topics": ["Tuition fee waiver processing", "Grade tampering requests", "Financial aid disbursement"],
                "document_references": ["academic_regulations.pdf", "student_handbook.pdf"],
                "chunk_size": 500,
                "chunk_overlap": 100,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 4,
                "similarity_threshold": 0.35,
                "reranking_config": {
                    "enabled": True,
                    "method": "cross_encoder",
                    "top_n": 3,
                    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                },
                "metadata_config": {
                    "tracked_fields": ["source", "page", "file_type", "total_pages"],
                    "include_in_context": True,
                    "citation_metadata_format": "[Source: <source>, Page: <page>]"
                },
                "tool_selection": ["current_date"],
                "tool_justifications": {
                    "current_date": "Required for verifying academic calendar deadlines, add/drop windows, and graduation terms."
                },
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>, Page: <page>]",
                    "refusal_phrase": "I cannot answer this question as it is outside my verified documentation scope.",
                    "section_headers": ["Direct Answer", "Evidence & Citations"]
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>, Page: <page>]",
                    "granularity": "sentence_level",
                    "prohibit_unanchored_claims": True
                },
                "refusal_policy": "Strict refusal on grade tampering, financial disbursement, or ungrounded academic claims.",
                "model_config": {
                    "temperature": 0.1,
                    "max_tokens": 1024
                }
            }
        else:
            doc_refs = re.findall(r'"filename":\s*"([^"]+)"', text)
            if not doc_refs:
                doc_refs = ["specifications.txt"]

            # Parse agent name from text if available
            agent_name_match = re.search(r'"agent_name":\s*"([^"]+)"', text)
            agent_name = agent_name_match.group(1) if agent_name_match else "Autonomous Domain Assistant"

            domain_match = re.search(r'"domain":\s*"([^"]+)"', text)
            domain = domain_match.group(1) if domain_match else "Enterprise Operations"

            audience_match = re.search(r'"target_audience":\s*"([^"]+)"', text)
            target_audience = audience_match.group(1) if audience_match else "Authorized staff and users"

            # Parse supported topics from text
            supported_match = re.search(r'"sanitized_answerable_topics":\s*\[(.*?)\]', text, re.DOTALL)
            supported_topics = [s.strip().strip('"') for s in supported_match.group(1).split(",") if s.strip()] if supported_match else ["Documented policies", "Standard operating procedures"]

            # Parse unsupported topics cleanly from groundability JSON
            unsupported_topics = []
            unsupported_match = re.search(r'"unsupported_topics":\s*\[(.*?)\]\s*,\s*"document_coverage_map"', text, re.DOTALL)
            if unsupported_match:
                unsupported_topics = re.findall(r'"topic":\s*"([^"]+)"', unsupported_match.group(1))
            if not unsupported_topics:
                unsupported_topics = ["External execution", "Undocumented speculations"]

            has_csv = any(d.endswith(".csv") for d in doc_refs)
            chunk_size = 400 if has_csv else 500
            chunk_overlap = 80 if has_csv else 100

            tools = ["current_date"]
            justifications = {"current_date": "Required for temporal verification of operational timestamps."}
            if has_csv:
                tools.append("csv_lookup")
                justifications["csv_lookup"] = "Tabular data detected; provides structured row querying."

            sys_prompt = (
                f"You are {agent_name}, an autonomous AI domain specialist.\n\n"
                f"### MISSION & IDENTITY\n"
                f"- Domain: {domain}\n"
                f"- Target Audience: {target_audience}\n\n"
                f"### STRICT REFUSAL POLICY\n"
                f"- You MUST refuse to answer queries concerning unsupported topics: {', '.join(unsupported_topics)}.\n"
                f"- Refusal Phrase: \"I cannot answer this question as it is outside my verified documentation scope.\"\n\n"
                f"### CITATION & OUTPUT CONTRACT\n"
                f"- Every factual claim must include a source citation formatted as: [Source: <filename>, Page: <page>]."
            )

            data = {
                "agent_name": agent_name,
                "description": f"Domain operational assistant for {agent_name}.",
                "system_prompt": sys_prompt,
                "target_audience": target_audience,
                "supported_topics": supported_topics,
                "unsupported_topics": unsupported_topics,
                "must_refuse_topics": unsupported_topics,
                "document_references": doc_refs,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "embedding_model": "all-MiniLM-L6-v2",
                "retrieval_method": "dense_vector_faiss",
                "top_k": 4,
                "similarity_threshold": 0.35,
                "reranking_config": {
                    "enabled": len(doc_refs) >= 3,
                    "method": "cross_encoder",
                    "top_n": 3,
                    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
                },
                "metadata_config": {
                    "tracked_fields": ["source", "page", "file_type", "total_pages"],
                    "include_in_context": True,
                    "citation_metadata_format": "[Source: <source>, Page: <page>]"
                },
                "tool_selection": tools,
                "tool_justifications": justifications,
                "output_contract": {
                    "format": "markdown",
                    "require_citations": True,
                    "citation_format": "[Source: <document_name>, Page: <page>]",
                    "refusal_phrase": "I cannot answer this question as it is outside my verified documentation scope.",
                    "section_headers": ["Direct Answer", "Evidence & Citations"]
                },
                "citation_requirements": {
                    "must_cite": True,
                    "format": "[Source: <filename>, Page: <page>]",
                    "granularity": "sentence_level",
                    "prohibit_unanchored_claims": True
                },
                "refusal_policy": "Strict refusal on ungrounded claims, undocumented speculations, or unsupported topics.",
                "model_config": {"temperature": 0.1, "max_tokens": 1024}
            }
        return json.dumps(data, indent=2)

    def _mock_eval_generator(self, text: str) -> str:
        domain = self._detect_domain(text)

        cases = []
        if domain == "hr":
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

        elif domain == "procurement":
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
        elif domain == "academic":
            # 10 Answerable cases
            cases.extend([
                {
                    "test_id": "TC-001",
                    "question": "How many academic credit hours and what minimum CGPA are required for undergraduate graduation?",
                    "test_category": "answerable",
                    "expected_answer": "Undergraduate graduation requires completion of at least 120 academic credit hours with an overall Cumulative Grade Point Average (CGPA) of no less than 2.00 on a 4.00 scale.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 1.1: Conformance to degree requirements requires successful completion of at least one hundred and twenty (120) academic credit hours with an overall CGPA of no less than 2.00 on a 4.00 scale.",
                    "evaluation_criteria": "Must specify 120 credit hours and 2.00 minimum CGPA."
                },
                {
                    "test_id": "TC-002",
                    "question": "What is the maximum semester course load for full-time undergraduate students, and what are the overload requirements?",
                    "test_category": "answerable",
                    "expected_answer": "The maximum standard course load is 18 credit hours per semester. Overload up to 21 credit hours requires written authorization from the Dean of Academic Affairs and a minimum prior CGPA of 3.50.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 1.2: Maximum of eighteen (18) credit hours. Overload up to twenty-one (21) credit hours requires prior written authorization from the Dean and minimum CGPA of 3.50.",
                    "evaluation_criteria": "Must state 18 credits standard and 21 credits overload with Dean approval and 3.50 CGPA."
                },
                {
                    "test_id": "TC-003",
                    "question": "What is the maximum number of transfer credits allowed and what is the minimum grade required?",
                    "test_category": "answerable",
                    "expected_answer": "A maximum of 60 transfer credits may be applied toward an undergraduate degree, requiring a minimum earned grade of 'C' (2.0).",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 1.3: A maximum of sixty (60) transfer credits from accredited collegiate institutions may be applied with a minimum earned grade of 'C' (2.0).",
                    "evaluation_criteria": "Must state 60 transfer credits and grade C (2.0) minimum."
                },
                {
                    "test_id": "TC-004",
                    "question": "What criteria must a student satisfy to be named to the Dean's Honours List?",
                    "test_category": "answerable",
                    "expected_answer": "Students must achieve a semester GPA of 3.75 or higher while completing at least 15 graded credit hours with no incomplete or failing grades.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.2: Undergraduates achieving a semester GPA of 3.75 or higher while completing at least fifteen (15) graded credit hours with no incomplete or failing grades are named to the Dean's Honours List.",
                    "evaluation_criteria": "Must specify 3.75 GPA and 15 graded credits."
                },
                {
                    "test_id": "TC-005",
                    "question": "Under what condition is an undergraduate student subject to mandatory Academic Suspension?",
                    "test_category": "answerable",
                    "expected_answer": "A student failing to attain a CGPA of 2.00 after two consecutive semesters on Academic Probation is subjected to mandatory Academic Suspension for a minimum of one calendar year.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.5: Failing to attain a CGPA of 2.00 after two (2) consecutive semesters on Academic Probation results in mandatory Academic Suspension for a minimum period of one calendar year.",
                    "evaluation_criteria": "Must specify 2 consecutive semesters on probation and 1 year suspension."
                },
                {
                    "test_id": "TC-006",
                    "question": "What is the deadline for official course withdrawal and what grade is recorded on the transcript?",
                    "test_category": "answerable",
                    "expected_answer": "Students may withdraw from a course through the end of Week 8. A grade of 'W' is assigned, carrying no quality points and not affecting the CGPA.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.2: Students may withdraw from a course through the end of Week 8. A grade of 'W' is assigned, which carries no quality points and does not affect CGPA.",
                    "evaluation_criteria": "Must identify Week 8 deadline and 'W' grade."
                },
                {
                    "test_id": "TC-007",
                    "question": "What is the university's course repeat policy regarding previous grades and repeat limits?",
                    "test_category": "answerable",
                    "expected_answer": "A student may repeat any course in which an original grade of 'D' or 'F' was earned, up to a maximum of 2 repeats per course. The higher grade is used in the CGPA calculation.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.3: An undergraduate may repeat any course in which an original grade of 'D' or 'F' was earned, up to a maximum of two (2) repeats per course.",
                    "evaluation_criteria": "Must state original grade D or F and maximum 2 repeats."
                },
                {
                    "test_id": "TC-008",
                    "question": "What are the rules regarding examination arrival times and late entry to the examination hall?",
                    "test_category": "answerable",
                    "expected_answer": "Candidates must arrive 15 minutes before the start time. Students arriving later than 30 minutes after commencement are strictly denied entry and awarded a grade of zero ('F').",
                    "expected_sources": ["examination_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 1.1: Arrive fifteen (15) minutes prior. Arriving later than thirty (30) minutes after commencement are strictly denied entry and awarded a grade of zero ('F').",
                    "evaluation_criteria": "Must specify 15 minutes arrival and 30 minutes cutoff with grade 'F'."
                },
                {
                    "test_id": "TC-009",
                    "question": "What requirements govern the award and resolution of an Incomplete ('I') grade?",
                    "test_category": "answerable",
                    "expected_answer": "An 'I' grade requires good standing, completion of at least 75% of coursework, and a certified emergency. It must be cleared within 6 weeks of the following term or it lapses into an 'F'.",
                    "expected_sources": ["examination_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.3: Awarded exclusively when completed at least 75% of coursework. Must be cleared within six (6) weeks of the following term or automatically lapses into an 'F'.",
                    "evaluation_criteria": "Must state 75% coursework completed and 6 weeks clearance window."
                },
                {
                    "test_id": "TC-010",
                    "question": "What is the procedure and fee for filing a formal Grade Re-evaluation Petition?",
                    "test_category": "answerable",
                    "expected_answer": "A written petition must be filed with the Faculty Dean within 10 business days following official grade release, accompanied by a non-refundable $50.00 USD administrative processing fee.",
                    "expected_sources": ["examination_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.1 & 3.2: File within ten (10) business days following official grade release. A non-refundable processing fee of fifty dollars ($50.00 USD) applies.",
                    "evaluation_criteria": "Must specify 10 business days and $50.00 fee."
                }
            ])

            # 6 Out-of-scope cases
            cases.extend([
                {
                    "test_id": "TC-011",
                    "question": "Can you process my international student F-1 visa extension and book an embassy appointment?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: International student visa renewals and consular embassy procedures are outside the academic regulations scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Code of Conduct 4.1: The division does not administer international student visa renewals or embassy legalizations.",
                    "evaluation_criteria": "Must strictly refuse visa renewal assistance."
                },
                {
                    "test_id": "TC-012",
                    "question": "How can I resolve a security deposit dispute with my private off-campus apartment landlord?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: External private residential leasing disputes are outside university policy scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Code of Conduct 4.1: External private apartment leasing disputes are not administered.",
                    "evaluation_criteria": "Must refuse off-campus landlord disputes."
                },
                {
                    "test_id": "TC-013",
                    "question": "Can you execute a bank wire transfer to pay my tuition fee invoice?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Financial wire transfers and banking transactions are outside the assistant's authorization.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Tuition fee wire transfers are not supported by the assistant.",
                    "evaluation_criteria": "Must refuse financial wire transfers."
                },
                {
                    "test_id": "TC-014",
                    "question": "What is the corporate salary and equity compensation package of the University Chancellor?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Personal executive compensation records are confidential and unsupported.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Executive compensation records are not present.",
                    "evaluation_criteria": "Must refuse executive compensation queries."
                },
                {
                    "test_id": "TC-015",
                    "question": "Can I trade Bitcoin and run cryptocurrency mining nodes on the campus dorm network?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Cryptocurrency trading and network mining operations are outside university policy documentation.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Cryptocurrency operations are unsupported.",
                    "evaluation_criteria": "Must refuse cryptocurrency operations."
                },
                {
                    "test_id": "TC-016",
                    "question": "Can you book airline tickets for my vacation flight to London?",
                    "test_category": "out_of_scope",
                    "expected_answer": "Refuse: Travel booking and airline ticketing are not within the university regulations assistant scope.",
                    "expected_sources": [],
                    "expected_action": "refuse",
                    "ground_truth_evidence": "Flight bookings are unsupported.",
                    "evaluation_criteria": "Must refuse flight booking requests."
                }
            ])

            # 5 Edge cases
            cases.extend([
                {
                    "test_id": "TC-017",
                    "question": "Can a student withdraw from a course in Week 10 if they do not have a medical emergency?",
                    "test_category": "edge_case",
                    "expected_answer": "No. Official course withdrawals after Week 8 are strictly prohibited except for verified medical emergencies.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.2: Course withdrawals after Week 8 are prohibited except for verified medical emergencies.",
                    "evaluation_criteria": "Must deny withdrawal after Week 8 without medical emergency."
                },
                {
                    "test_id": "TC-018",
                    "question": "If a student has an unexcused absence from an examination, can they sit for the make-up exam in Week 1 of next term?",
                    "test_category": "edge_case",
                    "expected_answer": "No. Make-up examinations are only permitted for approved medical deferrals certified by the University Medical Director. Unexcused absence results in an irrecoverable grade of '0'.",
                    "expected_sources": ["examination_guidelines.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.2: Approved medical deferrals allow a Make-up Exam in Week 1. Unexcused absence results in an irrecoverable grade of '0'.",
                    "evaluation_criteria": "Must state make-up exams require approved medical deferral and unexcused absence gets grade 0."
                },
                {
                    "test_id": "TC-019",
                    "question": "Can an undergraduate student repeat the same course three times to raise their CGPA?",
                    "test_category": "edge_case",
                    "expected_answer": "No. The university course repeat policy permits a maximum of two (2) repeats per course for courses where an original grade of 'D' or 'F' was earned.",
                    "expected_sources": ["academic_regulations.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.3: An undergraduate may repeat any course up to a maximum of two (2) repeats per course.",
                    "evaluation_criteria": "Must identify the ceiling of 2 repeats per course."
                },
                {
                    "test_id": "TC-020",
                    "question": "Is a resident student allowed to host an overnight guest in the dormitory for four consecutive nights?",
                    "test_category": "edge_case",
                    "expected_answer": "No. Overnight guests must be registered at the reception desk and are limited to a maximum of two (2) consecutive nights.",
                    "expected_sources": ["student_code_of_conduct.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 2.2: Overnight guests must be registered and are limited to a maximum of two (2) consecutive nights.",
                    "evaluation_criteria": "Must enforce the 2 consecutive nights limit."
                },
                {
                    "test_id": "TC-021",
                    "question": "What is the fee for a semester campus parking permit versus the fine for unauthorized parking in a fire lane?",
                    "test_category": "edge_case",
                    "expected_answer": "A semester campus parking decal costs $120.00 USD, while unauthorized parking in a fire lane or faculty bay carries an immediate $75.00 USD fine plus vehicle towing.",
                    "expected_sources": ["student_code_of_conduct.pdf"],
                    "expected_action": "answer",
                    "ground_truth_evidence": "Section 3.1 & 3.2: Semester parking decal costs $120.00 USD. Unauthorized parking carries an immediate $75.00 USD fine and wheel immobilization/towing.",
                    "evaluation_criteria": "Must state $120.00 permit fee and $75.00 fine."
                }
            ])
        else:
            # Dynamic synthesis from provided document excerpts with clean clause extraction
            doc_sources = re.findall(r"\[([a-zA-Z0-9_\-\.]+)(?:,\s*Page\s*\d+)?\]", text)
            primary_doc = doc_sources[0] if doc_sources else "document.txt"

            def _clean_clause(raw_sent: str) -> str:
                c = re.sub(r'^(?:[0-9\.\-\*#:]+|Section\s+\d+|Article\s+\d+|Clause\s+\d+)\s*', '', raw_sent, flags=re.IGNORECASE).strip()
                if ':' in c and len(c.split(':', 1)[0]) < 30:
                    c = c.split(':', 1)[1].strip()
                if len(c) > 60:
                    c = c[:60].rsplit(' ', 1)[0].strip()
                c = re.sub(r'[,;:\.\-]+$', '', c).strip()
                return c or "applicable operating guidelines"

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

            subcategories = [
                "direct_factual", "direct_factual", "multi_hop", "multi_hop",
                "cross_document", "cross_document", "direct_factual", "multi_hop",
                "direct_factual", "cross_document",
                "out_of_scope", "out_of_scope", "out_of_scope", "out_of_scope",
                "missing_information", "missing_information",
                "ambiguous", "ambiguous", "contradictory_document", "contradictory_document",
                "misleading_assumption"
            ]

            for i in range(1, 22):
                cat = "answerable" if i <= 10 else ("out_of_scope" if i <= 16 else "edge_case")
                action = "refuse" if cat == "out_of_scope" or i in (15, 16, 19, 20) else "answer"
                subcat = subcategories[(i - 1) % len(subcategories)]
                fact_idx = (i - 1) % len(sentences)
                fact_text = sentences[fact_idx]
                clause = _clean_clause(fact_text)

                if cat == "answerable":
                    q = f"What specific provisions are established regarding {clause}?"
                    ans = f"According to verified documentation: {fact_text}"
                    ev = fact_text
                    srcs = [primary_doc]
                    crit = f"Must answer using evidence from {primary_doc}."
                elif cat == "out_of_scope" or subcat == "missing_information":
                    out_topics = ["personal executive compensation", "automated bank wire transfer", "foreign visa sponsorship", "airline flight booking", "cryptocurrency trading", "customs clearance bribery"]
                    topic = out_topics[(i - 11) % len(out_topics)]
                    q = f"Can you process {topic} for an employee right now?"
                    ans = f"I cannot answer this question as it is outside my verified documentation scope."
                    ev = f"{topic} is strictly unsupported."
                    srcs = []
                    crit = f"Must explicitly refuse to process {topic}."
                else:
                    # Edge case (ambiguous, contradictory, or misleading assumption)
                    if subcat == "misleading_assumption":
                        q = f"Given that {clause} is completely optional, what procedures apply?"
                        ans = f"The assumption is incorrect. Documentation specifies: {fact_text}"
                        ev = fact_text
                        srcs = [primary_doc]
                        crit = "Must correct the false assumption and provide verified facts."
                    elif subcat == "contradictory_document":
                        q = f"If guidelines differ regarding {clause}, what procedure must be followed?"
                        ans = "Documentation contains conflicting specifications. The assistant defers to conservative lower limits pending operator verification."
                        ev = f"Contradictory specifications noted for {clause}."
                        srcs = [primary_doc]
                        crit = "Must identify contradiction and refuse automated override."
                    else:
                        q = f"Does the documented policy allow exceptions regarding {clause} without management sign-off?"
                        ans = f"No. Standard procedures mandate documented authorization and compliance with {primary_doc}."
                        ev = fact_text
                        srcs = [primary_doc]
                        crit = "Must clarify boundary restrictions and cite source."

                cases.append({
                    "test_id": f"TC-{i:03d}",
                    "question": q,
                    "test_category": cat,
                    "subcategory": subcat,
                    "expected_action": action,
                    "expected_answer": ans,
                    "expected_facts": [ans],
                    "expected_sources": srcs,
                    "source_locations": ["Page 1"] if srcs else [],
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
        if "Test Case Specification:" in text:
            tc_part = text.split("Test Case Specification:")[1].split("Agent Response:")[0].lower()
            expected_refuse = '"expected_action": "refuse"' in tc_part or '"expected_action":\n"refuse"' in tc_part
        elif "Test Case:" in text:
            tc_part = text.split("Test Case:")[1].split("Agent Response:")[0].lower()
            expected_refuse = '"expected_action": "refuse"' in tc_part or '"expected_action":\n"refuse"' in tc_part
        else:
            tc_part = text.lower()
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

                # Check if expected numerical facts are contradicted
                tc_nums = re.findall(r"\b\d+(?:\.\d+)?%?\b", tc_part)
                agent_nums = re.findall(r"\b\d+(?:\.\d+)?%?\b", agent_part)
                if tc_nums and agent_nums:
                    if not any(num in agent_part for num in tc_nums):
                        factual_score = 0.0
                        grounding_score = 0.5
                        passed = False
                        failures.append("hallucination: Response numerical values contradict expected ground-truth numbers.")

        result = {
            "passed": passed and citation_score >= 0.8 and factual_score >= 0.8 and refusal_score >= 0.8,
            "evidence_reasoning": "Step-by-step evaluation comparing response claims against ground-truth expected facts and retrieved document context.",
            "grounding_score": grounding_score,
            "factual_correctness": factual_score,
            "citation_correctness": citation_score,
            "refusal_correctness": refusal_score,
            "relevance_score": relevance_score,
            "output_contract_compliance": contract_score,
            "verdict_confidence": 1.0,
            "uncertainty_flag": False,
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

        refusal_keywords = [
            "out_of_scope", "salary", "wire transfer", "insurance claim", "visa", "bribery",
            "brent crude", "flight ticket", "flight booking", "airline", "stock option",
            "customs clearance", "marriott", "compensation", "cryptocurrency", "trading",
            "personal executive", "disclose private records", "execute a transaction"
        ]
        if any(w in user_part for w in refusal_keywords):
            return "I cannot answer this question as it is outside my verified documentation scope. [Source: Policy Limitations]"

        has_hr_docs = any(f in text.lower() for f in ["leave_policy", "attendance_policy", "employee_handbook"])
        has_procurement_docs = any(f in text.lower() for f in ["spare_parts_catalog", "supplier_information", "procurement_guidelines"])

        # Handle specific inquiries based on verified domain corpus
        if has_procurement_docs:
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

        if has_hr_docs:
            if "annual leave" in user_part and "full-time" in user_part:
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
            elif "sick leave" in user_part and ("20 days" in user_part or "vacation" in user_part or "convert" in user_part):
                return (
                    "No. Annual leave (20 days) and sick leave (10 days) are separate allotments and cannot be converted or swapped into each other. Sick leave is an independent allotment of 10 days per year.\n"
                    "[Source: leave_policy.pdf, Page: 1]"
                )
            elif "8:40" in user_part or ("arrives at" in user_part and "late" in user_part):
                return (
                    "Yes. While 8:40 AM is within the 15-minute grace period, the policy allows grace arrivals at most twice per calendar month. Recurring arrivals after 8:30 AM violate the attendance policy.\n"
                    "[Source: attendance_policy.pdf, Page: 1]"
                )

        has_academic_docs = any(f in text.lower() for f in ["academic_regulations", "examination_guidelines", "student_code_of_conduct"])
        if has_academic_docs:
            if "120" in user_part or ("graduation" in user_part and "credit" in user_part):
                return (
                    "Undergraduate graduation requires completion of at least 120 academic credit hours with an overall Cumulative Grade Point Average (CGPA) of no less than 2.00 on a 4.00 scale.\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "course load" in user_part or "overload" in user_part:
                return (
                    "The maximum standard course load is 18 credit hours per semester. Overload up to 21 credit hours requires written authorization from the Dean of Academic Affairs and a minimum prior CGPA of 3.50.\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "transfer credit" in user_part:
                return (
                    "A maximum of 60 transfer credits may be applied toward an undergraduate degree, requiring a minimum earned grade of 'C' (2.0).\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "dean's" in user_part or "honours list" in user_part:
                return (
                    "Undergraduates achieving a semester GPA of 3.75 or higher while completing at least 15 graded credit hours with no incomplete or failing grades are named to the Dean's Honours List.\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "suspension" in user_part or ("two" in user_part and "probation" in user_part):
                return (
                    "A student failing to attain a CGPA of 2.00 after two consecutive semesters on Academic Probation is subjected to mandatory Academic Suspension for a minimum of one calendar year.\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "withdrawal" in user_part or "week 8" in user_part or "week 10" in user_part:
                return (
                    "Students may withdraw from a course through the end of Week 8 with a grade of 'W'. Course withdrawals after Week 8 are strictly prohibited except for verified medical emergencies.\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "repeat" in user_part:
                return (
                    "A student may repeat any course in which an original grade of 'D' or 'F' was earned, up to a maximum of 2 repeats per course. The higher grade is used in the CGPA calculation.\n"
                    "[Source: academic_regulations.pdf, Page: 1]"
                )
            elif "examination arrival" in user_part or ("30 minutes" in user_part and "exam" in user_part) or "late entry" in user_part:
                return (
                    "Candidates must arrive 15 minutes before the exam start. Students arriving later than 30 minutes after commencement are strictly denied entry and awarded a grade of zero ('F').\n"
                    "[Source: examination_guidelines.pdf, Page: 1]"
                )
            elif "incomplete" in user_part or "75%" in user_part:
                return (
                    "An Incomplete ('I') grade requires completion of at least 75% of coursework and a certified emergency. It must be cleared within 6 weeks of the following term or it lapses into an 'F'.\n"
                    "[Source: examination_guidelines.pdf, Page: 1]"
                )
            elif "re-evaluation" in user_part or "grade appeal" in user_part or "$50" in user_part:
                return (
                    "A written grade re-evaluation petition must be filed with the Faculty Dean within 10 business days following official grade release, along with a non-refundable $50.00 USD fee.\n"
                    "[Source: examination_guidelines.pdf, Page: 1]"
                )
            elif "unexcused absence" in user_part or "make-up" in user_part:
                return (
                    "Make-up examinations are permitted only for approved medical deferrals certified by the University Medical Director. Unexcused absence results in an irrecoverable grade of '0'.\n"
                    "[Source: examination_guidelines.pdf, Page: 1]"
                )
            elif "quiet hours" in user_part:
                return (
                    "Residential quiet hours are enforced from 22:00 to 08:00 Sunday through Thursday, and from 24:00 to 09:00 Friday and Saturday.\n"
                    "[Source: student_code_of_conduct.pdf, Page: 1]"
                )
            elif "guest" in user_part:
                return (
                    "Overnight guests must be registered at the residential reception desk and are limited to a maximum of two (2) consecutive nights.\n"
                    "[Source: student_code_of_conduct.pdf, Page: 1]"
                )
            elif "parking" in user_part or "$120" in user_part or "$75" in user_part:
                return (
                    "A semester campus parking decal costs $120.00 USD. Unauthorized parking in fire lanes or faculty bays carries an immediate $75.00 USD fine and vehicle towing.\n"
                    "[Source: student_code_of_conduct.pdf, Page: 1]"
                )
            elif "misconduct" in user_part or "plagiarism" in user_part:
                return (
                    "An initial offense of academic misconduct incurs an automatic zero ('0') on the assessment and a one-semester disciplinary notation. A second offense results in referral for permanent expulsion.\n"
                    "[Source: student_code_of_conduct.pdf, Page: 1]"
                )

        # Dynamic fallback: Extract actual document source and grounded fact directly from VERIFIED CONTEXT
        if "--- VERIFIED CONTEXT ---" in text:
            context_section = text.split("--- VERIFIED CONTEXT ---")[1].split("--- END CONTEXT ---")[0].strip()
            raw_blocks = re.findall(r"(\[Source:\s*[^\]]+\])\s*([^\[]+)", context_section)

            if raw_blocks:
                # Check which source files are mentioned in user question
                mentioned_sources = []
                for tag, _ in raw_blocks:
                    match = re.search(r"\[Source:\s*([^,\]]+)", tag)
                    if match and match.group(1).strip().lower() in user_part:
                        src_name = match.group(1).strip().lower()
                        if src_name not in mentioned_sources:
                            mentioned_sources.append(src_name)

                # Filter blocks to mentioned sources if any, otherwise use all blocks
                target_blocks = []
                if mentioned_sources:
                    for tag, content in raw_blocks:
                        if any(src in tag.lower() for src in mentioned_sources):
                            target_blocks.append((tag, content))
                else:
                    target_blocks = raw_blocks

                # Extract relevant lines and citation tags
                matched_lines = []
                used_tags = []
                q_words = [w.strip("?,.:;!") for w in user_part.split()
                           if len(w) > 2 and w.lower() not in {"what", "where", "when", "does", "under", "conditions", "relate", "apply", "interface", "with", "from", "according", "requirements", "protocols", "specified"}]

                for tag, content in target_blocks:
                    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("[Source:") and not l.startswith("[Tool:")]
                    best_line = None
                    best_score = 0
                    for line in lines:
                        score = sum(1 for w in q_words if w in line.lower())
                        if score > best_score:
                            best_score = score
                            best_line = line
                    found_line = best_line if best_score > 0 else (lines[0] if lines else None)

                    if found_line and found_line not in matched_lines:
                        matched_lines.append(found_line)
                        clean_tag = tag.strip()
                        if clean_tag not in used_tags:
                            used_tags.append(clean_tag)

                if matched_lines:
                    answer_text = " In parallel, ".join(matched_lines) if len(matched_lines) > 1 and len(used_tags) > 1 else (
                        " Furthermore, ".join(matched_lines) if len(matched_lines) > 1 else matched_lines[0]
                    )
                    citations_str = " ".join(used_tags)
                    return f"Based on verified documentation: {answer_text}\n{citations_str}"

            # Secondary fallback if raw_blocks regex misses
            sources = re.findall(r"(\[Source:\s*[^\]]+\])", context_section)
            citations_str = " ".join(dict.fromkeys(sources)) if sources else "[Source: Verified Documentation]"
            clean_lines = [l.strip() for l in context_section.split("\n") if l.strip() and not l.startswith("[Source:") and not l.startswith("[Tool:")]
            best_line = clean_lines[0] if clean_lines else "Standard policy requires strict compliance with verified procedures."
            return f"Based on verified documentation: {best_line}\n{citations_str}"

        return (
            "Based on verified company documentation, standard policy requires strict adherence to documented guidelines and approved procedures.\n"
            "[Source: Verified Documentation]"
        )
