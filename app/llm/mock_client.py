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
        # 0. Manufacturing signals (Checked before procurement to avoid false match on 'spare parts')
        if any(d in t for d in ["manufacturing_operations", "plant_operations", "machine_maintenance", "lockout_tagout", "ais-mfg-sop"]) or \
           any(w in t for w in ["manufacturing operations", "plant engineers", "machine maintenance intervals", "quality inspection criteria", "safety lockouts", "shift handover protocols", "manufacturing assistant", "manufacturing_operations", "meridian components"]):
            return "manufacturing"
        # 1. Academic signals (Checked before HR so academic attendance policies do not trigger HR)
        if any(d in t for d in ["academic_regulations", "examination_guidelines", "student_handbook", "university_regulations", "student_code_of_conduct", "northbridge"]) or \
           any(w in t for w in ["academic regulations", "university academic", "student grading", "academic probation", "graduation requirements", "examination guidelines", "university regulations", "regulations assistant", "university_regulations", "northbridge institute", "academic policies", "degree requirements", "higher education"]):
            return "academic"
        # 2. Procurement signals
        if any(d in t for d in ["spare_parts_catalog", "supplier_information", "procurement_guidelines"]) or \
           (any(w in t for w in ["vessel procurement", "marine spares", "purchase order authorization", "po approval", "ship-spares"]) or (any(w in t for w in ["procurement", "spare parts"]) and any(w in t for w in ["vessel", "ship", "marine", "maritime", "superintendent"]))):
            return "procurement"
        # 3. HR signals
        if any(d in t for d in ["leave_policy", "attendance_policy", "employee_handbook", "hr_policy"]) or \
           any(w in t for w in ["hr assistant", "human resources", "leave policies", "attendance rules", "workplace guidelines", "employee questions", "sick leave", "annual leave", "working hours"]):
            return "hr"
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
            doc_names = list(dict.fromkeys(doc_matches)) if doc_matches else ["University_Regulations_Test_Document.pdf"]

            if "university regulations assistant" in text.lower() or ("university" in text.lower() and "regulations" in text.lower()):
                agent_name = "University Regulations Assistant"
            else:
                agent_name = "University Academic Regulations Assistant"

            data = {
                "agent_name": agent_name,
                "purpose": "Assist students, faculty, and academic advisors with questions regarding undergraduate graduation requirements, grading scales, academic probation, examination guidelines, attendance rules, and appeals at Northbridge Institute of Technology based strictly on verified documents.",
                "user_intent": "Provide verified guidance on academic regulations, add/drop periods, passing criteria, GPA calculations, and appeal procedures while refusing unsupported immigration, financial-aid, medical, or legal advice.",
                "target_audience": "University students, academic advisors, and faculty members",
                "domain": "Higher Education Academic Affairs",
                "scope": "Undergraduate academic regulations, course registration, attendance requirements, 100-point assessment scale, GPA calculation, academic warning and probation, leave of absence, formal appeals, and degree graduation criteria.",
                "tone": "Authoritative, academic, and clear",
                "constraints": ["Strict grounding in verified academic regulations manual", "Zero immigration, financial bursary, medical diagnosis, or legal representation advice"],
                "must_answer_topics": ["Graduation requirements (128 credits, CGPA >= 5.0)", "Attendance requirements (minimum 75%)", "Assessment and examination passing marks", "Add/drop and course withdrawal deadlines", "Grading scale and GPA calculation", "Academic warning and probation rules", "Leave of absence and appeal procedures"],
                "must_refuse_topics": ["Immigration and student visa renewals", "Financial-aid bursary disbursement and wire transfers", "Medical diagnosis and psychological counseling", "Legal representation and court disputes", "Direct grade tampering or unauthorized changes"],
                "required_tools": ["current_date"],
                "document_inventory": [
                    {
                        "filename": d,
                        "format": d.split(".")[-1].upper(),
                        "description": f"Undergraduate academic regulations manual {d}",
                        "page_count": 3 if "university_regulations" in d.lower() else 1,
                        "record_count": None,
                        "content_summary": "Northbridge Institute of Technology undergraduate academic regulations covering registration, attendance, grading, standing, appeals, and graduation.",
                        "detected_topics": ["Registration & Add/Drop", "Attendance & Examinations", "Grading Scale & GPA", "Academic Warning & Probation", "Grade Appeals", "Graduation Requirements"]
                    }
                    for d in doc_names
                ],
                "information_gaps": {
                    "missing_information": [],
                    "contradictory_information": [],
                    "duplicated_information": [],
                    "incomplete_information": []
                },
                "assumptions": ["Academic regulations reflect current 2026-27 catalog year (Version 2.1).", "Unattended defaults apply conservative policy interpretation."],
                "ambiguities": ["Undergraduate vs graduate credit transfer reciprocity."],
                "unsupported_requirements": ["Direct transcript alteration", "Tuition fee wire transfers", "Immigration visa processing"],
                "clarifications": []
            }
        elif domain == "manufacturing":
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            actual_doc = doc_matches[0] if (doc_matches and any("manufacturing" in d.lower() for d in doc_matches)) else "Manufacturing_Operations_Test_Document.pdf"
            data = {
                "agent_name": "Manufacturing Operations Assistant",
                "purpose": "Assist plant engineers, machine operators, and maintenance technicians with standard operating procedures, shift handover protocols, quality inspection tolerances, inventory safety stock, preventive maintenance intervals, workplace safety, and escalation routes at Meridian Components.",
                "user_intent": "Understand shift schedules, quality tolerances (+/- 0.05 mm), in-process inspections, reorder triggers (150 units), safety stock (120 units), PO approvals, preventive maintenance (500 hrs / 90 days), and escalation procedures.",
                "target_audience": "Plant engineers, machine operators, warehouse supervisors, and maintenance technicians",
                "domain": "Manufacturing Operations / Industrial Plant Operations",
                "scope": "Operating procedures, shift handovers (15 min overlap), weekly maintenance windows, incoming inspection (5 units/lot), quality hold (>3% defects), inventory control, PO approvals, preventive maintenance, baseline PPE, and 3-year record retention.",
                "tone": "Technical, precise, and safety-oriented",
                "constraints": ["Strict adherence to verified Meridian Components manual (v1.7)", "No unauthorized approvals exceeding delegation limits or hazardous waste advice"],
                "must_answer_topics": ["Shift schedule and handover protocols", "Quality control and tolerance thresholds (+/- 0.05 mm)", "Inventory control and safety stock (120 units)", "Receiving and purchase order approval thresholds", "Preventive maintenance intervals (500 hrs / 90 days)", "Workplace safety, PPE, and incident reporting", "Escalation contacts and record retention (3 years)"],
                "must_refuse_topics": ["Employee payroll and overtime approvals", "Corporate income tax and accounting", "Medical treatment and injury diagnosis", "Legal liability and court representation", "Customer contract legal interpretation", "Hazardous-waste disposal and chemical manifests"],
                "required_tools": ["calculator", "current_date"],
                "document_inventory": [
                    {
                        "filename": actual_doc,
                        "format": "PDF",
                        "description": "Meridian Components Manufacturing Operations & Plant Procedures Manual (Version 1.7)",
                        "page_count": 3,
                        "record_count": None,
                        "content_summary": "Plant operations manual covering shift hours, quality tolerances, inventory thresholds, PO approvals, preventive maintenance, baseline PPE, and escalation procedures.",
                        "detected_topics": ["Shift Operations", "Quality Tolerances", "Inventory & Reorder Levels", "PO Approval Authority", "Preventive Maintenance", "Workplace Safety", "Escalation Contacts"]
                    }
                ],
                "information_gaps": {
                    "missing_information": ["Hazardous chemical disposal protocols are not covered in the plant manual."],
                    "contradictory_information": [],
                    "duplicated_information": [],
                    "incomplete_information": []
                },
                "assumptions": ["Manual reflects current Meridian Components Plant operations (Version 1.7, effective 1 Sept 2026).", "Conservative safety thresholds apply during unattended operations."],
                "ambiguities": ["Customer-specific shelf-life instructions vs standard FIFO."],
                "unsupported_requirements": ["Direct PLC/machinery control execution", "Live ERP database writing", "Payroll execution"],
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
        has_mfg_files = any("manufacturing" in d or "plant_operations" in d for d in actual_docs)

        domain = self._detect_domain(text)
        if has_mfg_files or (domain == "manufacturing" and not actual_docs):
            domain = "manufacturing"
        elif has_proc_files or (domain == "procurement" and not actual_docs):
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
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            actual_doc = doc_matches[0] if (doc_matches and any("university_regulations" in d.lower() for d in doc_matches)) else "University_Regulations_Test_Document.pdf"
            is_single_univ = any("university_regulations" in d.lower() for d in doc_matches) or len(doc_matches) <= 1

            if is_single_univ:
                data = {
                    "supported_topics": [
                        {
                            "topic": "Graduation requirements and degree audit",
                            "evidence_sources": [actual_doc],
                            "coverage_summary": "Minimum 128 credits, satisfy all curriculum requirements, cumulative GPA >= 5.0, graduation application at least 60 calendar days prior.",
                            "confidence_score": 0.98,
                            "evidence_references": [
                                {"source_document": actual_doc, "page_or_record": "Page 3", "excerpt": "Minimum 128 credits, satisfy all curriculum requirements, Cumulative GPA >= 5.0.", "relevance_score": 0.98}
                            ]
                        },
                        {
                            "topic": "Attendance and examination qualification",
                            "evidence_sources": [actual_doc],
                            "coverage_summary": "Students must attend at least 75% of scheduled sessions in each course; calculated separately for lectures, laboratories and studios.",
                            "confidence_score": 0.98,
                            "evidence_references": [
                                {"source_document": actual_doc, "page_or_record": "Page 1", "excerpt": "Students must attend at least 75% of scheduled sessions in each course to qualify for the end-semester examination.", "relevance_score": 0.98}
                            ]
                        },
                        {
                            "topic": "Registration, add/drop, and course withdrawal",
                            "evidence_sources": [actual_doc],
                            "coverage_summary": "Add/drop period first 10 calendar days; course withdrawal deadline end of teaching week 8 (recorded as W, excluded from GPA); late registration 500 fee.",
                            "confidence_score": 0.97,
                            "evidence_references": [
                                {"source_document": actual_doc, "page_or_record": "Page 1", "excerpt": "Add/drop period: First 10 calendar days. Course withdrawal deadline: End of teaching week 8.", "relevance_score": 0.97}
                            ]
                        },
                        {
                            "topic": "Assessment scale, passing mark, and examinations",
                            "evidence_sources": [actual_doc],
                            "coverage_summary": "100-point assessment scale (continuous 40, mid-sem 20, end-sem 40); pass requires >= 40/100 overall and >= 35% on end-sem exam.",
                            "confidence_score": 0.96,
                            "evidence_references": [
                                {"source_document": actual_doc, "page_or_record": "Page 1", "excerpt": "Students must obtain at least 40/100 overall and at least 35% of the end-semester examination component to pass.", "relevance_score": 0.96}
                            ]
                        },
                        {
                            "topic": "Grading scale, GPA, academic warning and probation",
                            "evidence_sources": [actual_doc],
                            "coverage_summary": "10-point scale: A(10) to P(5), F(0); semester GPA < 5.0 results in academic warning; cumulative GPA < 4.0 results in probation with max 15 credits.",
                            "confidence_score": 0.96,
                            "evidence_references": [
                                {"source_document": actual_doc, "page_or_record": "Page 2", "excerpt": "A student with a semester GPA below 5.0 is placed on academic warning. Cumulative GPA below 4.0 is placed on academic probation.", "relevance_score": 0.96}
                            ]
                        },
                        {
                            "topic": "Leave of absence and academic appeals",
                            "evidence_sources": [actual_doc],
                            "coverage_summary": "Leave of absence maximum 2 semesters across degree; appeals submitted within 7 calendar days with 2,000 fee (refunded if upheld), decided within 20 working days.",
                            "confidence_score": 0.97,
                            "evidence_references": [
                                {"source_document": actual_doc, "page_or_record": "Page 2", "excerpt": "Appeals submitted within 7 calendar days, accompanied by a 2,000 appeal fee. Decided within 20 working days.", "relevance_score": 0.97}
                            ]
                        }
                    ],
                    "partially_supported_topics": [],
                    "unsupported_topics": [
                        {"topic": "Immigration and student visa renewals", "reason": "Immigration and visa advice are outside manual scope.", "absence_nature": "missing_from_corpus", "confidence_score": 0.98},
                        {"topic": "Financial-aid bursary disbursement and wire transfers", "reason": "Financial aid wire transfers are unsupported.", "absence_nature": "unsupported_capability", "confidence_score": 0.99},
                        {"topic": "Medical diagnosis and psychological counseling", "reason": "Medical diagnosis is outside scope.", "absence_nature": "missing_from_corpus", "confidence_score": 0.98},
                        {"topic": "Legal representation and court disputes", "reason": "Legal advice is outside scope.", "absence_nature": "missing_from_corpus", "confidence_score": 0.98}
                    ],
                    "document_coverage_map": {
                        actual_doc: ["Registration & Add/Drop", "Attendance & Examinations", "Grading Scale & GPA", "Academic Warning & Probation", "Grade Appeals", "Graduation Requirements"]
                    },
                    "refusal_recommendations": [
                        "Strictly refuse immigration and student visa extension requests.",
                        "Refuse financial aid wire transfer and bursary disbursement requests.",
                        "Refuse medical diagnosis and legal representation requests."
                    ],
                    "sanitized_answerable_topics": ["Graduation requirements and degree audit", "Attendance and examination qualification", "Registration, add/drop, and course withdrawal", "Assessment scale, passing mark, and examinations", "Grading scale, GPA, academic warning and probation", "Leave of absence and academic appeals"],
                    "overall_groundability_score": 0.95
                }
            else:
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
        elif domain == "manufacturing":
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            actual_doc = doc_matches[0] if (doc_matches and any("manufacturing" in d.lower() for d in doc_matches)) else "Manufacturing_Operations_Test_Document.pdf"
            data = {
                "supported_topics": [
                    {
                        "topic": "Shift schedule and handover protocols",
                        "evidence_sources": [actual_doc],
                        "coverage_summary": "Shift A (06:00-14:00), Shift B (14:00-22:00), Shift C (22:00-06:00); minimum 15-minute operational overlap and signed handover checklist.",
                        "confidence_score": 0.98,
                        "evidence_references": [
                            {"source_document": actual_doc, "page_or_record": "Page 1", "excerpt": "Shift handover requires a minimum 15-minute operational overlap between outgoing and incoming shift leads.", "relevance_score": 0.98}
                        ]
                    },
                    {
                        "topic": "Quality control and tolerance thresholds",
                        "evidence_sources": [actual_doc],
                        "coverage_summary": "Incoming sample size 5 units/lot; critical tolerance +/- 0.05 mm; in-process inspection 1 every 50 units (first 5 after changeover); defect rate > 3% triggers line HOLD.",
                        "confidence_score": 0.97,
                        "evidence_references": [
                            {"source_document": actual_doc, "page_or_record": "Page 1", "excerpt": "Critical component dimensional tolerance is +/- 0.05 mm unless drawing specifies tighter limit. Defect rate > 3% triggers immediate HOLD.", "relevance_score": 0.97}
                        ]
                    },
                    {
                        "topic": "Inventory control and safety stock",
                        "evidence_sources": [actual_doc],
                        "coverage_summary": "Reorder trigger 150 units; critical minimum stock 120 units; FIFO rotation; discrepancies > 2% require recount.",
                        "confidence_score": 0.96,
                        "evidence_references": [
                            {"source_document": actual_doc, "page_or_record": "Page 2", "excerpt": "Critical components must never fall below minimum safety stock of 120 units. Reorder trigger is 150 units.", "relevance_score": 0.96}
                        ]
                    },
                    {
                        "topic": "Receiving and purchase order approval thresholds",
                        "evidence_sources": [actual_doc],
                        "coverage_summary": "PO up to 50,000 (Procurement Coordinator); above 50,000 to 2,00,000 (Procurement Manager); above 2,00,000 (Plant Director).",
                        "confidence_score": 0.98,
                        "evidence_references": [
                            {"source_document": actual_doc, "page_or_record": "Page 2", "excerpt": "Purchase orders up to 50,000 approved by Procurement Coordinator; above 50,000 up to 2,00,000 Procurement Manager; above 2,00,000 Plant Director.", "relevance_score": 0.98}
                        ]
                    },
                    {
                        "topic": "Preventive maintenance intervals and machine stops",
                        "evidence_sources": [actual_doc],
                        "coverage_summary": "Preventive maintenance every 500 operating hours or 90 calendar days; stops > 10 min logged; stops > 30 min escalated to Maintenance Supervisor.",
                        "confidence_score": 0.97,
                        "evidence_references": [
                            {"source_document": actual_doc, "page_or_record": "Page 2", "excerpt": "Preventive maintenance is scheduled every 500 operating hours or every 90 calendar days. Stops longer than 30 minutes escalated to Maintenance Supervisor.", "relevance_score": 0.97}
                        ]
                    },
                    {
                        "topic": "Workplace safety, PPE, and escalation authority",
                        "evidence_sources": [actual_doc],
                        "coverage_summary": "Baseline PPE: safety shoes, safety glasses, hearing protection; evacuation drills twice a year; record retention 3 years.",
                        "confidence_score": 0.96,
                        "evidence_references": [
                            {"source_document": actual_doc, "page_or_record": "Page 2", "excerpt": "Required baseline PPE in production areas is safety shoes, safety glasses and hearing protection. Records retained for three years.", "relevance_score": 0.96}
                        ]
                    }
                ],
                "partially_supported_topics": [],
                "unsupported_topics": [
                    {"topic": "Employee payroll and overtime approval", "reason": "Payroll and compensation records are explicitly outside manual scope.", "absence_nature": "missing_from_corpus", "confidence_score": 0.98},
                    {"topic": "Corporate income tax and accounting", "reason": "Income tax and corporate accounting are excluded.", "absence_nature": "unsupported_capability", "confidence_score": 0.99},
                    {"topic": "Hazardous-waste disposal and chemical manifests", "reason": "Hazardous waste disposal requirements are outside manual.", "absence_nature": "missing_from_corpus", "confidence_score": 0.98}
                ],
                "document_coverage_map": {
                    actual_doc: ["Shift Schedule", "Quality Tolerances", "Inventory Control", "PO Approvals", "Preventive Maintenance", "Workplace Safety", "Escalation Contacts"]
                },
                "refusal_recommendations": [
                    "Strictly refuse payroll and overtime approvals and direct to plant HR.",
                    "Refuse hazardous-waste disposal questions as outside documented scope.",
                    "Refuse legal liability, tax, and medical advice requests."
                ],
                "sanitized_answerable_topics": ["Shift schedule and handover protocols", "Quality control and tolerance thresholds", "Inventory control and safety stock", "Receiving and purchase order approval thresholds", "Preventive maintenance intervals and machine stops", "Workplace safety, PPE, and escalation authority"],
                "overall_groundability_score": 0.94
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
        has_mfg_files = any("manufacturing" in d or "plant_operations" in d for d in actual_docs)

        domain = self._detect_domain(text)
        if has_mfg_files or (domain == "manufacturing" and not actual_docs):
            domain = "manufacturing"
        elif has_proc_files or (domain == "procurement" and not actual_docs):
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
        elif domain == "manufacturing":
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            actual_doc = doc_matches[0] if (doc_matches and any("manufacturing" in d.lower() for d in doc_matches)) else "Manufacturing_Operations_Test_Document.pdf"
            data = {
                "agent_name": "Manufacturing Operations Assistant",
                "description": "An autonomous AI assistant for plant operations, machine maintenance intervals, quality inspection tolerances, safety lockout protocols, and spare parts procurement.",
                "system_prompt": (
                    "You are the Manufacturing Operations Assistant. Guide plant engineers and technicians on operating procedures, machine maintenance, quality tolerances, and safety protocols.\n"
                    "Always cite the source document and page/section for every assertion.\n"
                    "Strictly refuse requests to approve payroll overtime, modify ERP vendor contracts, or give legal advice."
                ),
                "target_audience": "Plant engineers, machine operators, and maintenance technicians",
                "supported_topics": ["Shift handover protocols", "Machine maintenance intervals and lubrication", "Quality inspection and tolerance thresholds", "Lockout/Tagout (LOTO) procedures", "Spare parts procurement and safety stock", "Emergency shutdown and evacuation"],
                "unsupported_topics": ["Overtime payroll approvals", "Modifying ERP vendor contracts", "Live machinery control execution"],
                "must_refuse_topics": ["Overtime payroll approvals", "Modifying ERP vendor contracts", "Live machinery control execution", "Worker compensation legal advice", "Corporate equity compensation"],
                "document_references": [actual_doc],
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
                "tool_selection": ["calculator", "current_date"],
                "tool_justifications": {
                    "calculator": "Required for tolerance stack-up and maintenance hour interval calculations.",
                    "current_date": "Required for verifying maintenance log dates and shift rosters."
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
                "refusal_policy": "Strict refusal on any question concerning payroll overtime, ERP contracts, or ungrounded topics.",
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
            doc_sources = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            single_doc = doc_sources[0] if (doc_sources and any("university_regulations" in d.lower() for d in doc_sources)) else None
            is_northbridge = single_doc is not None or "northbridge" in text.lower() or not any("academic_regulations" in d.lower() for d in doc_sources)

            if is_northbridge:
                acad_src = single_doc or "University_Regulations_Test_Document.pdf"
                # 10 Answerable cases for Northbridge Institute of Technology
                cases.extend([
                    {
                        "test_id": "TC-001",
                        "question": "What are the graduation requirements regarding Cumulative GPA and curriculum completion?",
                        "test_category": "answerable",
                        "subcategory": "direct_factual",
                        "expected_answer": "Undergraduate graduation requires completing all programme-required credits, satisfying compulsory course requirements, achieving a cumulative GPA of at least 5.0, and clearing all property and administrative holds.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 3"],
                        "expected_action": "answer",
                        "expected_facts": ["Complete all programme-required credits", "Cumulative GPA of at least 5.0", "Satisfy compulsory course requirements"],
                        "ground_truth_evidence": "Page 3, Section 9: To qualify for an undergraduate award, a student must complete all programme-required credits, satisfy compulsory course requirements, achieve a cumulative GPA of at least 5.0 and clear all institutional property and administrative holds.",
                        "evaluation_criteria": "Must state programme-required credits and cumulative GPA of at least 5.0."
                    },
                    {
                        "test_id": "TC-002",
                        "question": "What is the minimum attendance requirement to qualify for the end-semester examination?",
                        "test_category": "answerable",
                        "subcategory": "direct_factual",
                        "expected_answer": "Students must attend at least 75% of scheduled sessions in each course to qualify for the end-semester examination.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Attend at least 75% of scheduled sessions in each course"],
                        "ground_truth_evidence": "Page 1, Section 3: Students must attend at least 75% of scheduled sessions in each course to qualify for the end-semester examination.",
                        "evaluation_criteria": "Must state at least 75% attendance requirement."
                    },
                    {
                        "test_id": "TC-003",
                        "question": "Can an undergraduate student offset low laboratory attendance with lecture attendance?",
                        "test_category": "answerable",
                        "subcategory": "direct_factual",
                        "expected_answer": "No. Attendance is calculated separately for lectures, laboratories and studio sessions. A student cannot offset low laboratory attendance with lecture attendance.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Attendance is calculated separately", "Cannot offset low laboratory attendance with lecture attendance"],
                        "ground_truth_evidence": "Page 1, Section 3: Attendance is calculated separately for lectures, laboratories and studio sessions. A student cannot offset low laboratory attendance with lecture attendance.",
                        "evaluation_criteria": "Must state attendance is calculated separately and lab attendance cannot be offset with lecture."
                    },
                    {
                        "test_id": "TC-004",
                        "question": "What is the deadline for course add/drop and for course withdrawal?",
                        "test_category": "answerable",
                        "subcategory": "direct_factual",
                        "expected_answer": "The add/drop period is the first 10 calendar days of each semester. The course withdrawal deadline is the end of teaching week 8.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Add/drop period: First 10 calendar days", "Course withdrawal deadline: End of teaching week 8"],
                        "ground_truth_evidence": "Page 1, Section 2: Add/drop period: First 10 calendar days of each semester. Course withdrawal deadline: End of teaching week 8.",
                        "evaluation_criteria": "Must state first 10 calendar days and end of teaching week 8."
                    },
                    {
                        "test_id": "TC-005",
                        "question": "What are the passing mark criteria for a course under the assessment regulations?",
                        "test_category": "answerable",
                        "subcategory": "direct_factual",
                        "expected_answer": "Students must obtain at least 40/100 overall and at least 35% of the end-semester examination component to pass a course.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["At least 40/100 overall", "At least 35% of the end-semester examination component"],
                        "ground_truth_evidence": "Page 1, Section 4: Students must obtain at least 40/100 overall and at least 35% of the end-semester examination component to pass a course.",
                        "evaluation_criteria": "Must state 40/100 overall and 35% of end-semester examination."
                    },
                    {
                        "test_id": "TC-006",
                        "question": "What is the minimum full-time load and maximum standard course load per semester?",
                        "test_category": "answerable",
                        "subcategory": "multi_hop",
                        "expected_answer": "The minimum full-time load is 12 credits per semester, and the maximum standard course load is 21 credits per semester.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Minimum full-time load: 12 credits per semester", "Maximum standard load: 21 credits per semester"],
                        "ground_truth_evidence": "Page 1, Section 2: Minimum full-time load: 12 credits per semester. Maximum standard load: 21 credits per semester.",
                        "evaluation_criteria": "Must state 12 credits minimum and 21 credits maximum."
                    },
                    {
                        "test_id": "TC-007",
                        "question": "Under what condition is a student placed on academic warning and what action is required?",
                        "test_category": "answerable",
                        "subcategory": "grading_and_academic_standing",
                        "expected_answer": "A student with a semester GPA below 5.0 is placed on academic warning and must meet an academic adviser within 15 working days after results are released.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 2"],
                        "expected_action": "answer",
                        "expected_facts": ["Semester GPA below 5.0", "Meet an academic adviser within 15 working days"],
                        "ground_truth_evidence": "Page 2, Section 6: A student with a semester GPA below 5.0 is placed on academic warning and must meet an academic adviser within 15 working days after results are released.",
                        "evaluation_criteria": "Must state semester GPA below 5.0 and meet adviser within 15 working days."
                    },
                    {
                        "test_id": "TC-008",
                        "question": "What triggers academic probation and what credit limit applies while on probation?",
                        "test_category": "answerable",
                        "subcategory": "grading_and_academic_standing",
                        "expected_answer": "A student with a cumulative GPA below 4.0 after two completed semesters is placed on academic probation. Students on probation may register for no more than 15 credits in the next semester.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 2"],
                        "expected_action": "answer",
                        "expected_facts": ["Cumulative GPA below 4.0 after two completed semesters", "Register for no more than 15 credits"],
                        "ground_truth_evidence": "Page 2, Section 6: A student with a cumulative GPA below 4.0 after two completed semesters is placed on academic probation. Students on probation may register for no more than 15 credits in the next semester.",
                        "evaluation_criteria": "Must state cumulative GPA below 4.0 and 15 credits limit."
                    },
                    {
                        "test_id": "TC-009",
                        "question": "What is the deadline for submitting an assessment-mark appeal and how quickly must the Registrar acknowledge it?",
                        "test_category": "answerable",
                        "subcategory": "graduation_and_appeals",
                        "expected_answer": "An assessment-mark appeal must be submitted within seven calendar days of result publication, and the Registrar acknowledges it within three working days.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 2"],
                        "expected_action": "answer",
                        "expected_facts": ["Submitted within seven calendar days of result publication", "Registrar acknowledges within three working days"],
                        "ground_truth_evidence": "Page 2, Section 8: An assessment-mark appeal must be submitted through the student portal within seven calendar days of the publication of the result. The Registrar acknowledges a formal academic appeal within three working days and normally issues a decision within 15 working days.",
                        "evaluation_criteria": "Must state seven calendar days and three working days."
                    },
                    {
                        "test_id": "TC-010",
                        "question": "How is the cumulative GPA calculated when a student repeats a failed course?",
                        "test_category": "answerable",
                        "subcategory": "grading_and_academic_standing",
                        "expected_answer": "Where a student repeats a failed course, the latest attempt is used in the cumulative GPA; the transcript retains the record of both attempts.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 2"],
                        "expected_action": "answer",
                        "expected_facts": ["Latest attempt is used in the cumulative GPA", "Transcript retains the record of both attempts"],
                        "ground_truth_evidence": "Page 2, Section 5: Where a student repeats a failed course, the latest attempt is used in the cumulative GPA; the transcript retains the record of both attempts.",
                        "evaluation_criteria": "Must state latest attempt is used and transcript retains both attempts."
                    }
                ])

                # 6 Out-of-scope cases for Northbridge Institute of Technology
                cases.extend([
                    {
                        "test_id": "TC-011",
                        "question": "Can you process my international student F-1 visa extension and book an embassy appointment?",
                        "test_category": "out_of_scope",
                        "subcategory": "out_of_scope",
                        "expected_answer": "Refuse: International student visa renewals and immigration advice are outside the scope of the academic regulations manual.",
                        "expected_sources": [],
                        "source_locations": [],
                        "expected_action": "refuse",
                        "expected_facts": ["Outside scope: immigration and visa advice"],
                        "ground_truth_evidence": "Page 1, Section 1: They do not provide immigration, financial-aid, medical-diagnosis or legal advice.",
                        "evaluation_criteria": "Must refuse visa inquiries."
                    },
                    {
                        "test_id": "TC-012",
                        "question": "Can you wire transfer my financial aid bursary directly to my personal checking account?",
                        "test_category": "out_of_scope",
                        "subcategory": "out_of_scope",
                        "expected_answer": "Refuse: Financial aid bursary wire transfers and monetary disbursements are unsupported.",
                        "expected_sources": [],
                        "source_locations": [],
                        "expected_action": "refuse",
                        "expected_facts": ["Outside scope: financial-aid and wire transfers"],
                        "ground_truth_evidence": "Page 1, Section 1: They do not provide financial-aid advice.",
                        "evaluation_criteria": "Must refuse financial wire transfers."
                    },
                    {
                        "test_id": "TC-013",
                        "question": "Can you diagnose why I have severe migraines during exam week and prescribe medication?",
                        "test_category": "out_of_scope",
                        "subcategory": "out_of_scope",
                        "expected_answer": "Refuse: Medical diagnosis and medication prescriptions are outside the academic regulations scope.",
                        "expected_sources": [],
                        "source_locations": [],
                        "expected_action": "refuse",
                        "expected_facts": ["Outside scope: medical diagnosis and prescriptions"],
                        "ground_truth_evidence": "Page 1, Section 1: They do not provide medical-diagnosis advice.",
                        "evaluation_criteria": "Must refuse medical diagnosis."
                    },
                    {
                        "test_id": "TC-014",
                        "question": "Can you provide legal representation for my court hearing regarding off-campus property damage?",
                        "test_category": "out_of_scope",
                        "subcategory": "out_of_scope",
                        "expected_answer": "Refuse: Legal advice and legal representation are outside the assistant scope.",
                        "expected_sources": [],
                        "source_locations": [],
                        "expected_action": "refuse",
                        "expected_facts": ["Outside scope: legal advice and representation"],
                        "ground_truth_evidence": "Page 1, Section 1: They do not provide legal advice.",
                        "evaluation_criteria": "Must refuse legal representation."
                    },
                    {
                        "test_id": "TC-015",
                        "question": "What is the application deadline and partner university list for the summer study-abroad program in Tokyo?",
                        "test_category": "edge_case",
                        "subcategory": "missing_information",
                        "expected_answer": "Refuse: Information regarding study-abroad programs in Tokyo or partner university lists is not present in the verified policy manual.",
                        "expected_sources": [],
                        "source_locations": [],
                        "expected_action": "refuse",
                        "expected_facts": ["Missing information: study-abroad program in Tokyo not documented"],
                        "ground_truth_evidence": "Study-abroad programs and partner university lists are absent from the document corpus.",
                        "evaluation_criteria": "Must refuse or indicate missing information."
                    },
                    {
                        "test_id": "TC-016",
                        "question": "Can you book my airline flight tickets from Boston to London for the upcoming winter break?",
                        "test_category": "out_of_scope",
                        "subcategory": "out_of_scope",
                        "expected_answer": "Refuse: Airline travel booking and flight ticketing are unsupported.",
                        "expected_sources": [],
                        "source_locations": [],
                        "expected_action": "refuse",
                        "expected_facts": ["Outside scope: travel and flight booking"],
                        "ground_truth_evidence": "Travel booking tools and services are unsupported.",
                        "evaluation_criteria": "Must refuse flight bookings."
                    }
                ])

                # 5 Edge & Constraint cases for Northbridge Institute of Technology
                cases.extend([
                    {
                        "test_id": "TC-017",
                        "question": "Can an undergraduate student withdraw from a course in Week 10 without documented exceptional circumstances?",
                        "test_category": "edge_case",
                        "subcategory": "graduation_and_appeals",
                        "expected_answer": "No. After the published course-withdrawal deadline at the end of teaching week 8, course withdrawal is permitted only for documented exceptional circumstances.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Course withdrawal deadline: End of teaching week 8", "Requires documented exceptional circumstances"],
                        "ground_truth_evidence": "Page 1, Section 2: After the add/drop period, a course may be withdrawn only by the published withdrawal deadline (end of teaching week 8).",
                        "evaluation_criteria": "Must deny withdrawal in Week 10 without documented exceptions."
                    },
                    {
                        "test_id": "TC-018",
                        "question": "If a course has 40 scheduled sessions and a student attends 28, do they qualify for the end-semester examination?",
                        "test_category": "edge_case",
                        "subcategory": "attendance_and_examinations",
                        "expected_answer": "No. A course with 40 scheduled sessions requires attendance at 30 sessions (75%) to meet the standard threshold. Attending 28 sessions is only 70% and fails to qualify.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Course with 40 scheduled sessions requires attendance at 30 sessions (75%)", "Attending 28 sessions is only 70% and fails to meet threshold"],
                        "ground_truth_evidence": "Page 1, Section 3: Example: A course with 40 scheduled sessions requires attendance at 30 sessions (75%) to meet the standard threshold.",
                        "evaluation_criteria": "Must calculate that 28 of 40 sessions is below 75% threshold."
                    },
                    {
                        "test_id": "TC-019",
                        "question": "What letter grade and grade points are awarded for a composite course score of 85 points?",
                        "test_category": "edge_case",
                        "subcategory": "grading_and_academic_standing",
                        "expected_answer": "A score of 85 falls within the 80–89 score range, earning a letter grade of B and 9 grade points.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 2"],
                        "expected_action": "answer",
                        "expected_facts": ["Letter grade B", "Score range 80–89", "Grade points 9"],
                        "ground_truth_evidence": "Page 2, Section 5: Letter grade B: Score range 80–89, Grade points 9.",
                        "evaluation_criteria": "Must state letter grade B and 9 grade points."
                    },
                    {
                        "test_id": "TC-020",
                        "question": "How many consecutive semesters of leave of absence can an undergraduate take, and what is the maximum across the degree?",
                        "test_category": "edge_case",
                        "subcategory": "grading_and_academic_standing",
                        "expected_answer": "An undergraduate may request a leave of absence for one or two consecutive semesters. The normal maximum across the degree is two semesters.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 2"],
                        "expected_action": "answer",
                        "expected_facts": ["Leave of absence for one or two consecutive semesters", "Normal maximum across the degree is two semesters"],
                        "ground_truth_evidence": "Page 2, Section 7: An undergraduate may request a leave of absence for one or two consecutive semesters. The normal maximum across the degree is two semesters.",
                        "evaluation_criteria": "Must state one or two consecutive semesters and maximum two semesters across degree."
                    },
                    {
                        "test_id": "TC-021",
                        "question": "What fee and approval are required if a student attempts late course registration?",
                        "test_category": "edge_case",
                        "subcategory": "direct_factual",
                        "expected_answer": "Late registration requires programme-chair approval and a 500 administrative fee.",
                        "expected_sources": [acad_src],
                        "source_locations": ["Page 1"],
                        "expected_action": "answer",
                        "expected_facts": ["Requires programme-chair approval", "500 administrative fee"],
                        "ground_truth_evidence": "Page 1, Section 2: Late registration: Requires programme-chair approval and a 500 administrative fee.",
                        "evaluation_criteria": "Must state programme-chair approval and 500 administrative fee."
                    }
                ])
            else:
                acad_src = "academic_regulations.pdf"
                exam_src = "examination_guidelines.pdf"
                conduct_src = "student_code_of_conduct.pdf"

                # Legacy multi-doc test cases (for tests/test_unseen_generalization.py)
                cases.extend([
                    {"test_id": "TC-001", "question": "How many academic credit hours and what minimum CGPA are required for undergraduate graduation?", "test_category": "answerable", "subcategory": "direct_factual", "expected_answer": "Undergraduate graduation requires completion of at least 120 academic credit hours with an overall Cumulative Grade Point Average (CGPA) of no less than 2.00 on a 4.00 scale.", "expected_sources": [acad_src], "source_locations": ["Page 1"], "expected_action": "answer", "expected_facts": ["120 academic credit hours", "CGPA no less than 2.00"], "ground_truth_evidence": "Section 1.1: 120 credit hours and CGPA 2.00", "evaluation_criteria": "Must specify 120 credit hours and 2.00 CGPA."},
                    {"test_id": "TC-002", "question": "What is the maximum semester course load for full-time undergraduate students, and what are the overload requirements?", "test_category": "answerable", "subcategory": "multi_hop", "expected_answer": "The maximum standard course load is 18 credit hours per semester. Overload up to 21 credit hours requires written authorization from the Dean and a minimum prior CGPA of 3.50.", "expected_sources": [acad_src], "source_locations": ["Page 1"], "expected_action": "answer", "expected_facts": ["18 standard credit hours", "21 overload credits with Dean approval"], "ground_truth_evidence": "Section 1.2: 18 standard and 21 overload", "evaluation_criteria": "Must state 18 standard and 21 overload."},
                    {"test_id": "TC-003", "question": "What is the maximum number of transfer credits allowed and what is the minimum grade required?", "test_category": "answerable", "subcategory": "direct_factual", "expected_answer": "A maximum of 60 transfer credits may be applied with a minimum grade of 'C' (2.0).", "expected_sources": [acad_src], "source_locations": ["Page 1"], "expected_action": "answer", "expected_facts": ["60 transfer credits", "Grade C minimum"], "ground_truth_evidence": "Section 1.3: 60 transfer credits", "evaluation_criteria": "Must state 60 transfer credits."},
                    {"test_id": "TC-004", "question": "What criteria must a student satisfy to be named to the Dean's Honours List?", "test_category": "answerable", "subcategory": "multi_hop", "expected_answer": "Students must achieve a semester GPA of 3.75 or higher while completing at least 15 graded credit hours.", "expected_sources": [acad_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["Semester GPA 3.75", "15 graded credit hours"], "ground_truth_evidence": "Section 2.2: GPA 3.75 and 15 credits", "evaluation_criteria": "Must specify 3.75 GPA and 15 credits."},
                    {"test_id": "TC-005", "question": "Under what condition is an undergraduate student subject to mandatory Academic Suspension?", "test_category": "answerable", "subcategory": "grading_and_academic_standing", "expected_answer": "Failing to attain a CGPA of 2.00 after two consecutive semesters on Academic Probation results in mandatory Academic Suspension for one calendar year.", "expected_sources": [acad_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["2 consecutive semesters on probation", "1 calendar year suspension"], "ground_truth_evidence": "Section 2.5: suspension for 1 year", "evaluation_criteria": "Must specify 2 semesters and 1 year."},
                    {"test_id": "TC-006", "question": "What is the deadline for official course withdrawal and what grade is recorded on the transcript?", "test_category": "answerable", "subcategory": "direct_factual", "expected_answer": "Students may withdraw through the end of Week 8. A grade of 'W' is assigned.", "expected_sources": [acad_src], "source_locations": ["Page 1"], "expected_action": "answer", "expected_facts": ["End of Week 8", "Grade of W"], "ground_truth_evidence": "Section 3.2: Week 8 deadline and W grade", "evaluation_criteria": "Must state Week 8 and W grade."},
                    {"test_id": "TC-007", "question": "What is the university's course repeat policy regarding previous grades and repeat limits?", "test_category": "answerable", "subcategory": "direct_factual", "expected_answer": "A student may repeat any course in which an original grade of 'D' or 'F' was earned, up to a maximum of 2 repeats per course.", "expected_sources": [acad_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["Original grade D or F", "Maximum 2 repeats"], "ground_truth_evidence": "Section 3.3: 2 repeats max", "evaluation_criteria": "Must state max 2 repeats."},
                    {"test_id": "TC-008", "question": "What are the rules regarding examination arrival times and late entry to the examination hall?", "test_category": "answerable", "subcategory": "attendance_and_examinations", "expected_answer": "Candidates must arrive 15 minutes before the start time. Students arriving later than 30 minutes after commencement are strictly denied entry and awarded a grade of zero ('F').", "expected_sources": [exam_src], "source_locations": ["Page 1"], "expected_action": "answer", "expected_facts": ["15 minutes arrival", "30 minutes cutoff"], "ground_truth_evidence": "Section 1.1: 15 min arrival and 30 min cutoff", "evaluation_criteria": "Must specify 15 min arrival and 30 min cutoff."},
                    {"test_id": "TC-009", "question": "What requirements govern the award and resolution of an Incomplete ('I') grade?", "test_category": "answerable", "subcategory": "grading_and_academic_standing", "expected_answer": "Requires completion of at least 75% of coursework and a certified emergency. Must be cleared within 6 weeks or lapses into 'F'.", "expected_sources": [exam_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["75% coursework", "6 weeks clearance"], "ground_truth_evidence": "Section 2.3: 75% coursework and 6 weeks", "evaluation_criteria": "Must state 75% coursework and 6 weeks."},
                    {"test_id": "TC-010", "question": "What is the procedure and fee for filing a formal Grade Re-evaluation Petition?", "test_category": "answerable", "subcategory": "graduation_and_appeals", "expected_answer": "A written petition must be filed with the Faculty Dean within 10 business days following grade release, with a .00 fee.", "expected_sources": [exam_src], "source_locations": ["Page 3"], "expected_action": "answer", "expected_facts": ["10 business days", ".00 fee"], "ground_truth_evidence": "Section 3.1: 10 days and  fee", "evaluation_criteria": "Must specify 10 days and  fee."},
                    {"test_id": "TC-011", "question": "Can you process my international student F-1 visa extension and book an embassy appointment?", "test_category": "out_of_scope", "subcategory": "out_of_scope", "expected_answer": "Refuse: Visa renewals are outside scope.", "expected_sources": [], "source_locations": [], "expected_action": "refuse", "expected_facts": ["Refuse visa"], "ground_truth_evidence": "Code 4.1: visa out of scope", "evaluation_criteria": "Must refuse visa."},
                    {"test_id": "TC-012", "question": "How can I resolve a security deposit dispute with my private off-campus apartment landlord?", "test_category": "out_of_scope", "subcategory": "out_of_scope", "expected_answer": "Refuse: Off-campus residential disputes are outside scope.", "expected_sources": [], "source_locations": [], "expected_action": "refuse", "expected_facts": ["Refuse off-campus dispute"], "ground_truth_evidence": "Code 4.1: off campus outside scope", "evaluation_criteria": "Must refuse landlord disputes."},
                    {"test_id": "TC-013", "question": "Can you execute a bank wire transfer to pay my tuition fee invoice?", "test_category": "out_of_scope", "subcategory": "out_of_scope", "expected_answer": "Refuse: Wire transfers are outside scope.", "expected_sources": [], "source_locations": [], "expected_action": "refuse", "expected_facts": ["Refuse wire transfer"], "ground_truth_evidence": "Wire transfers outside scope", "evaluation_criteria": "Must refuse wire transfer."},
                    {"test_id": "TC-014", "question": "What is the corporate salary and equity compensation package of the University Chancellor?", "test_category": "out_of_scope", "subcategory": "out_of_scope", "expected_answer": "Refuse: Executive compensation is outside scope.", "expected_sources": [], "source_locations": [], "expected_action": "refuse", "expected_facts": ["Refuse executive salary"], "ground_truth_evidence": "Salary outside scope", "evaluation_criteria": "Must refuse executive salary."},
                    {"test_id": "TC-015", "question": "What is the institutional application deadline and partner university list for the summer study-abroad program in Tokyo?", "test_category": "edge_case", "subcategory": "missing_information", "expected_answer": "Refuse: Study-abroad programs in Tokyo are not present in documentation.", "expected_sources": [], "source_locations": [], "expected_action": "refuse", "expected_facts": ["Missing Tokyo study abroad"], "ground_truth_evidence": "Tokyo study abroad missing", "evaluation_criteria": "Must refuse missing study abroad info."},
                    {"test_id": "TC-016", "question": "Can you book airline tickets for my vacation flight to London?", "test_category": "out_of_scope", "subcategory": "out_of_scope", "expected_answer": "Refuse: Travel booking is outside scope.", "expected_sources": [], "source_locations": [], "expected_action": "refuse", "expected_facts": ["Refuse travel booking"], "ground_truth_evidence": "Travel booking outside scope", "evaluation_criteria": "Must refuse travel booking."},
                    {"test_id": "TC-017", "question": "Can a student withdraw from a course in Week 10 if they do not have a medical emergency?", "test_category": "edge_case", "subcategory": "graduation_and_appeals", "expected_answer": "No. Course withdrawals after Week 8 are strictly prohibited except for verified medical emergencies.", "expected_sources": [acad_src], "source_locations": ["Page 1"], "expected_action": "answer", "expected_facts": ["Withdrawals after Week 8 prohibited"], "ground_truth_evidence": "Section 3.2: after Week 8 prohibited", "evaluation_criteria": "Must deny withdrawal after Week 8."},
                    {"test_id": "TC-018", "question": "If a student has an unexcused absence from an examination, can they sit for the make-up exam in Week 1 of next term?", "test_category": "edge_case", "subcategory": "attendance_and_examinations", "expected_answer": "No. Make-up exams require approved medical deferrals. Unexcused absence results in grade 0.", "expected_sources": [exam_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["Make-up requires medical deferral", "Grade 0 for unexcused"], "ground_truth_evidence": "Section 2.2: unexcused gets 0", "evaluation_criteria": "Must deny make-up exam for unexcused absence."},
                    {"test_id": "TC-019", "question": "Can an undergraduate student repeat the same course three times to raise their CGPA?", "test_category": "edge_case", "subcategory": "grading_and_academic_standing", "expected_answer": "No. Course repeat policy permits a maximum of two repeats per course.", "expected_sources": [acad_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["Maximum 2 repeats per course"], "ground_truth_evidence": "Section 3.3: max 2 repeats", "evaluation_criteria": "Must state max 2 repeats."},
                    {"test_id": "TC-020", "question": "Is a resident student allowed to host an overnight guest in the dormitory for four consecutive nights?", "test_category": "edge_case", "subcategory": "residential_regulations", "expected_answer": "No. Overnight guests are limited to a maximum of two consecutive nights.", "expected_sources": [conduct_src], "source_locations": ["Page 2"], "expected_action": "answer", "expected_facts": ["Maximum 2 consecutive nights"], "ground_truth_evidence": "Section 2.2: max 2 nights", "evaluation_criteria": "Must enforce 2 consecutive nights limit."},
                    {"test_id": "TC-021", "question": "What is the fee for a semester campus parking permit versus the fine for unauthorized parking in a fire lane?", "test_category": "edge_case", "subcategory": "campus_regulations", "expected_answer": "A semester parking decal costs .00 USD, while unauthorized parking carries a .00 fine.", "expected_sources": [conduct_src], "source_locations": ["Page 3"], "expected_action": "answer", "expected_facts": [".00 permit fee", ".00 fine"], "ground_truth_evidence": "Section 3.1:  permit and  fine", "evaluation_criteria": "Must state  permit and  fine."}
                ])
        elif domain == "manufacturing":
            doc_sources = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            single_doc = doc_sources[0] if (doc_sources and any("manufacturing" in d.lower() for d in doc_sources)) else "Manufacturing_Operations_Test_Document.pdf"
            mfg_src = single_doc

            # 10 Answerable cases for Meridian Components Manufacturing Plant
            cases.extend([
                {
                    "test_id": "TC-001",
                    "question": "What are the scheduled operational hours for Shift A, Shift B, and Shift C?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Shift A operates from 06:00 to 14:00, Shift B operates from 14:00 to 22:00, and Shift C operates from 22:00 to 06:00.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["Shift A 06:00-14:00", "Shift B 14:00-22:00", "Shift C 22:00-06:00"],
                    "ground_truth_evidence": "Page 1, Section 2: Shift A: 06:00–14:00; Shift B: 14:00–22:00; Shift C: 22:00–06:00.",
                    "evaluation_criteria": "Must specify Shift A (06:00-14:00), Shift B (14:00-22:00), and Shift C (22:00-06:00)."
                },
                {
                    "test_id": "TC-002",
                    "question": "By when must production supervisors publish the line plan, and who must approve changes affecting confirmed customer orders?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Production supervisors must publish the next week's line plan by Thursday 16:00. Any change affecting a confirmed customer order must be approved by the Production Manager.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["Publish line plan by Thursday 16:00", "Approved by the Production Manager"],
                    "ground_truth_evidence": "Page 1, Section 2: Production supervisors publish the next week's line plan by Thursday 16:00. Any change affecting a confirmed customer order must be approved by the Production Manager.",
                    "evaluation_criteria": "Must specify Thursday 16:00 deadline and Production Manager approval."
                },
                {
                    "test_id": "TC-003",
                    "question": "When is the weekly maintenance window scheduled and what is the status of production?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "The weekly maintenance window is scheduled every Sunday from 06:00 to 10:00, during which production lines are stopped.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["Sunday 06:00-10:00", "Production lines stopped"],
                    "ground_truth_evidence": "Page 1, Section 2: Weekly maintenance window: Sunday 06:00–10:00 (Production lines stopped).",
                    "evaluation_criteria": "Must specify Sunday 06:00-10:00 and production lines stopped."
                },
                {
                    "test_id": "TC-004",
                    "question": "What is the minimum incoming inspection sample size per delivery lot for raw materials?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Incoming material inspection samples five (5) units from each delivery lot. If one or more sampled units fail a specified check, the lot is placed on HOLD.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["Samples five units from each delivery lot", "Placed on HOLD if one or more fail"],
                    "ground_truth_evidence": "Page 1, Section 4: Incoming material inspection samples five units from each delivery lot. If one or more sampled units fail a specified check, the lot is placed on HOLD pending expanded inspection.",
                    "evaluation_criteria": "Must specify 5 units per delivery lot."
                },
                {
                    "test_id": "TC-005",
                    "question": "Who must approve the first-piece inspection after a changeover before normal batch production resumes, and is verbal approval accepted?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "First-piece approval must be recorded by a Quality Inspector before normal batch production resumes. A verbal approval is not sufficient.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["Recorded by a Quality Inspector", "Verbal approval is not sufficient"],
                    "ground_truth_evidence": "Page 1, Section 3: First-piece approval must be recorded by a Quality Inspector before normal batch production resumes. A verbal approval is not sufficient.",
                    "evaluation_criteria": "Must state Quality Inspector recorded approval and verbal approval is not sufficient."
                },
                {
                    "test_id": "TC-006",
                    "question": "What is the in-process quality inspection frequency during production runs?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "During production, operators inspect the first five units after every changeover and then one unit every 50 units produced.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["First five units after every changeover", "One unit every 50 units produced"],
                    "ground_truth_evidence": "Page 1, Section 4: During production, operators inspect the first five units after every changeover and then one unit every 50 units produced.",
                    "evaluation_criteria": "Must specify first 5 units after changeover and 1 unit every 50 units produced."
                },
                {
                    "test_id": "TC-007",
                    "question": "What pre-start checklist items must the operator complete before machine start-up?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Before start-up, the operator completes the daily pre-start checklist: guards fitted, emergency stop tested, work area clear, correct job card loaded, and required personal protective equipment worn.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 1"],
                    "expected_action": "answer",
                    "expected_facts": ["Guards fitted", "Emergency stop tested", "Work area clear", "Correct job card loaded", "Required PPE worn"],
                    "ground_truth_evidence": "Page 1, Section 3: Before start-up, the operator completes the daily pre-start checklist: guards fitted, emergency stop tested, work area clear, correct job card loaded and required personal protective equipment worn.",
                    "evaluation_criteria": "Must list pre-start checklist checks."
                },
                {
                    "test_id": "TC-008",
                    "question": "What is the reorder trigger level and minimum safety stock for critical components?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Standard components are reordered when stock reaches or falls below 150 units. Critical components must never fall below a minimum safety stock of 120 units.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2"],
                    "expected_action": "answer",
                    "expected_facts": ["Reorder trigger 150 units", "Critical component minimum safety stock 120 units"],
                    "ground_truth_evidence": "Page 2, Section 5: Standard components are reordered when stock reaches or falls below 150 units. Critical components must never fall below the minimum safety stock level of 120 units.",
                    "evaluation_criteria": "Must specify 150 units reorder trigger and 120 units critical minimum safety stock."
                },
                {
                    "test_id": "TC-009",
                    "question": "What is the scheduled interval for preventive maintenance on plant machinery?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Preventive maintenance is scheduled every 500 operating hours or every 90 calendar days, whichever occurs first.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2"],
                    "expected_action": "answer",
                    "expected_facts": ["Every 500 operating hours or every 90 calendar days, whichever occurs first"],
                    "ground_truth_evidence": "Page 2, Section 7: Preventive maintenance is scheduled every 500 operating hours or every 90 calendar days, whichever occurs first.",
                    "evaluation_criteria": "Must state 500 operating hours or 90 calendar days, whichever comes first."
                },
                {
                    "test_id": "TC-010",
                    "question": "How long must production logs, inspection records, and maintenance records be retained?",
                    "test_category": "answerable",
                    "subcategory": "direct_factual",
                    "expected_answer": "Production logs, inspection records, maintenance records, and dispatch records must be retained for three (3) years.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 3"],
                    "expected_action": "answer",
                    "expected_facts": ["Retained for three (3) years"],
                    "ground_truth_evidence": "Page 3, Section 9: Production logs, inspection records, maintenance records and dispatch records must be retained for three years.",
                    "evaluation_criteria": "Must specify 3 years retention period."
                }
            ])

            # 6 Out-of-scope cases for Meridian Components Manufacturing Plant
            cases.extend([
                {
                    "test_id": "TC-011",
                    "question": "Can you approve 8 hours of overtime pay on the shift supervisor payroll sheet?",
                    "test_category": "out_of_scope",
                    "subcategory": "out_of_scope",
                    "expected_answer": "Refuse: Employee payroll, overtime approvals, and wage compensation are outside the scope of the plant operations manual.",
                    "expected_sources": [],
                    "source_locations": [],
                    "expected_action": "refuse",
                    "expected_facts": ["Outside scope: employee payroll and overtime compensation"],
                    "ground_truth_evidence": "Page 3, Section 11: This manual does not define engineering design approval, statutory permits, employee payroll, income tax, insurance coverage, medical treatment, legal liability...",
                    "evaluation_criteria": "Must strictly refuse employee payroll overtime approvals."
                },
                {
                    "test_id": "TC-012",
                    "question": "What are the company corporate income tax deductions for capital machinery depreciation?",
                    "test_category": "out_of_scope",
                    "subcategory": "out_of_scope",
                    "expected_answer": "Refuse: Corporate income tax calculations and financial accounting rules are outside the operations manual scope.",
                    "expected_sources": [],
                    "source_locations": [],
                    "expected_action": "refuse",
                    "expected_facts": ["Outside scope: income tax and corporate financial accounting"],
                    "ground_truth_evidence": "Page 3, Section 11: This manual does not define employee payroll, income tax, insurance coverage...",
                    "evaluation_criteria": "Must strictly refuse income tax inquiries."
                },
                {
                    "test_id": "TC-013",
                    "question": "Can you process a worker's medical insurance claim for a shop floor injury?",
                    "test_category": "out_of_scope",
                    "subcategory": "out_of_scope",
                    "expected_answer": "Refuse: Health insurance claims and worker compensation processing are outside plant operational documentation scope.",
                    "expected_sources": [],
                    "source_locations": [],
                    "expected_action": "refuse",
                    "expected_facts": ["Outside scope: insurance coverage and claims"],
                    "ground_truth_evidence": "Page 3, Section 11: This manual does not define insurance coverage or compensation eligibility.",
                    "evaluation_criteria": "Must refuse health insurance claim requests."
                },
                {
                    "test_id": "TC-014",
                    "question": "Can you provide medical treatment and diagnosis instructions for a deep puncture wound on line 2?",
                    "test_category": "out_of_scope",
                    "subcategory": "out_of_scope",
                    "expected_answer": "Refuse: Medical diagnosis and injury treatment instructions are outside scope and must be referred to qualified medical personnel.",
                    "expected_sources": [],
                    "source_locations": [],
                    "expected_action": "refuse",
                    "expected_facts": ["Outside scope: medical diagnosis and injury treatment"],
                    "ground_truth_evidence": "Page 2, Section 8 & Page 3, Section 11: Questions about diagnosis, treatment, compensation eligibility or legal responsibility are outside this manual.",
                    "evaluation_criteria": "Must strictly refuse medical diagnosis and treatment inquiries."
                },
                {
                    "test_id": "TC-015",
                    "question": "Who is legally liable if a contractor slips on an oil spill in the warehouse loading bay?",
                    "test_category": "out_of_scope",
                    "subcategory": "out_of_scope",
                    "expected_answer": "Refuse: Legal liability and legal responsibility determinations are strictly outside the scope of this manual.",
                    "expected_sources": [],
                    "source_locations": [],
                    "expected_action": "refuse",
                    "expected_facts": ["Outside scope: legal liability and responsibility determinations"],
                    "ground_truth_evidence": "Page 3, Section 11: This manual does not define legal liability or responsibility.",
                    "evaluation_criteria": "Must refuse legal liability queries."
                },
                {
                    "test_id": "TC-016",
                    "question": "What is the procedure for disposing of spent hazardous chemical trichloroethylene solvent waste drums?",
                    "test_category": "out_of_scope",
                    "subcategory": "out_of_scope",
                    "expected_answer": "Refuse: Hazardous-waste disposal requirements and statutory chemical waste handling are outside the scope of this manual.",
                    "expected_sources": [],
                    "source_locations": [],
                    "expected_action": "refuse",
                    "expected_facts": ["Outside scope: hazardous-waste disposal requirements"],
                    "ground_truth_evidence": "Page 3, Section 11: This manual does not define hazardous-waste disposal requirements.",
                    "evaluation_criteria": "Must strictly refuse hazardous-waste disposal inquiries."
                }
            ])

            # 5 Edge & Constraint cases for Meridian Components Manufacturing Plant
            cases.extend([
                {
                    "test_id": "TC-017",
                    "question": "Who must approve a purchase order valued at 150,000 versus an order exceeding 2,00,000?",
                    "test_category": "edge_case",
                    "subcategory": "direct_factual",
                    "expected_answer": "Purchase orders above 50,000 and up to 2,00,000 require approval from the Procurement Manager. Orders above 2,00,000 require approval from the Plant Director.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2"],
                    "expected_action": "answer",
                    "expected_facts": ["150,000 requires Procurement Manager", "Orders above 2,00,000 require Plant Director"],
                    "ground_truth_evidence": "Page 2, Section 6: Orders above 50,000 and up to 2,00,000 require the Procurement Manager. Orders above 2,00,000 require the Plant Director.",
                    "evaluation_criteria": "Must state Procurement Manager for 150,000 and Plant Director for over 2,00,000."
                },
                {
                    "test_id": "TC-018",
                    "question": "What action is required if an inventory physical count reveals a discrepancy greater than 2%?",
                    "test_category": "edge_case",
                    "subcategory": "direct_factual",
                    "expected_answer": "Inventory discrepancies above 2% of the recorded quantity require a recount by a second employee and notification to the Warehouse Supervisor.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2"],
                    "expected_action": "answer",
                    "expected_facts": ["Recount by a second employee", "Notification to the Warehouse Supervisor"],
                    "ground_truth_evidence": "Page 2, Section 5: Inventory discrepancies above 2% of the recorded quantity require a recount by a second employee and notification to the Warehouse Supervisor.",
                    "evaluation_criteria": "Must specify recount by second employee and notification to Warehouse Supervisor."
                },
                {
                    "test_id": "TC-019",
                    "question": "If an unplanned machine stop lasts longer than 30 minutes, who must it be escalated to and within what timeframe?",
                    "test_category": "edge_case",
                    "subcategory": "direct_factual",
                    "expected_answer": "An unplanned stop longer than 30 minutes must be escalated to the Maintenance Supervisor, with a target response within 15 minutes of escalation.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2", "Page 3"],
                    "expected_action": "answer",
                    "expected_facts": ["Escalated to Maintenance Supervisor", "Response target within 15 minutes"],
                    "ground_truth_evidence": "Page 2, Section 7 & Page 3, Section 10: Machine stop over 30 minutes escalates to Maintenance Supervisor with target response within 15 minutes of escalation.",
                    "evaluation_criteria": "Must specify Maintenance Supervisor and 15 minutes target response."
                },
                {
                    "test_id": "TC-020",
                    "question": "What baseline personal protective equipment (PPE) is mandatory in production areas?",
                    "test_category": "edge_case",
                    "subcategory": "direct_factual",
                    "expected_answer": "Required baseline PPE in production areas is safety shoes, safety glasses, and hearing protection.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2"],
                    "expected_action": "answer",
                    "expected_facts": ["Safety shoes", "Safety glasses", "Hearing protection"],
                    "ground_truth_evidence": "Page 2, Section 8: Required baseline PPE in production areas is safety shoes, safety glasses and hearing protection.",
                    "evaluation_criteria": "Must list safety shoes, safety glasses, and hearing protection."
                },
                {
                    "test_id": "TC-021",
                    "question": "How frequently are emergency evacuation drills conducted across the facility?",
                    "test_category": "edge_case",
                    "subcategory": "direct_factual",
                    "expected_answer": "Emergency evacuation drills are conducted twice each calendar year.",
                    "expected_sources": [mfg_src],
                    "source_locations": ["Page 2"],
                    "expected_action": "answer",
                    "expected_facts": ["Twice each calendar year"],
                    "ground_truth_evidence": "Page 2, Section 8: Evacuation drills are conducted twice each calendar year.",
                    "evaluation_criteria": "Must specify twice each calendar year."
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
            "personal executive", "disclose private records", "execute a transaction",
            "apartment", "landlord", "deposit dispute", "off-campus", "study-abroad", "study abroad", "tokyo",
            "overtime", "payroll", "erp vendor", "worker compensation", "chemical disposal", "hazardous chemical",
            "waste manifest", "income tax", "tax deductions", "depreciation", "medical insurance", "puncture wound",
            "medical treatment", "medical diagnosis", "prescribe", "migraines", "legal representation", "court hearing",
            "legal liability", "hazardous-waste", "trichloroethylene", "solvent waste"
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

        has_mfg_docs = any(f in text.lower() for f in ["manufacturing_operations", "manufacturing", "plant_operations", "machine_maintenance", "lockout_tagout", "ais-mfg-sop"])
        if has_mfg_docs:
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            single_doc = doc_matches[0] if (doc_matches and any("manufacturing" in d.lower() for d in doc_matches)) else "Manufacturing_Operations_Test_Document.pdf"
            mfg_tag = single_doc

            # Authentic Meridian Components Plant Procedures Manual (v1.7)
            if "shift a" in user_part or "shift b" in user_part or "shift c" in user_part or ("operational hours" in user_part and "shift" in user_part):
                return (
                    "Shift A operates from 06:00 to 14:00, Shift B operates from 14:00 to 22:00, and Shift C operates from 22:00 to 06:00.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "line plan" in user_part or ("thursday" in user_part and "16:00" in user_part) or "confirmed customer order" in user_part:
                return (
                    "Production supervisors publish the next week's line plan by Thursday 16:00. Any change affecting a confirmed customer order must be approved by the Production Manager.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "first-piece" in user_part or "first piece" in user_part or ("verbal approval" in user_part and "quality" in user_part):
                return (
                    "First-piece approval must be recorded by a Quality Inspector before normal batch production resumes. A verbal approval is not sufficient.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "pre-start" in user_part or "pre start" in user_part or "checklist" in user_part:
                return (
                    "Before start-up, the operator completes the daily pre-start checklist: guards fitted, emergency stop tested, work area clear, correct job card loaded and required personal protective equipment worn.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "handover" in user_part or ("overlap" in user_part and "shift" in user_part):
                return (
                    "Operators must record actual start time, completed quantity, rejected quantity and downtime reason in the production log before the end of each shift.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "weekly maintenance" in user_part or ("sunday" in user_part and "maintenance" in user_part):
                return (
                    "The weekly maintenance window is scheduled every Sunday from 06:00 to 10:00, during which production lines are stopped.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "incoming" in user_part and ("sample size" in user_part or "delivery lot" in user_part or "raw materials" in user_part):
                return (
                    "Incoming material inspection samples five (5) units from each delivery lot. If one or more sampled units fail a specified check, the lot is placed on HOLD pending expanded inspection.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "in-process" in user_part or ("50 units" in user_part and "inspection" in user_part) or ("first 5" in user_part and "changeover" in user_part):
                return (
                    "During production, operators inspect the first five units after every changeover and then one unit every 50 units produced.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "rework" in user_part or "discard" in user_part or "nonconforming" in user_part:
                return (
                    "Any unit outside the approved drawing tolerance must be tagged and moved to the red nonconforming-material area. Operators must not rework or discard nonconforming units without written disposition.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "reorder trigger" in user_part or "150 units" in user_part or ("safety stock" in user_part and "120" in user_part):
                return (
                    "Standard components are reordered when stock reaches or falls below 150 units. Critical components must never fall below the minimum safety stock level of 120 units.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "preventive maintenance" in user_part or ("500 operating hours" in user_part or "90 calendar days" in user_part or "90 days" in user_part):
                return (
                    "Preventive maintenance is scheduled every 500 operating hours or every 90 calendar days, whichever occurs first.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "retention" in user_part or "retained" in user_part or "3 years" in user_part or "three years" in user_part:
                return (
                    "Production logs, inspection records, maintenance records, and dispatch records must be retained for three (3) years.\n"
                    f"[Source: {mfg_tag}, Page: 3]"
                )
            elif "purchase order" in user_part or "150,000" in user_part or "2,00,000" in user_part or "200,000" in user_part or "procurement coordinator" in user_part or "procurement manager" in user_part:
                return (
                    "Purchase orders up to 50,000 may be approved by the Procurement Coordinator. Orders above 50,000 up to 2,00,000 require the Procurement Manager. Orders above 2,00,000 require approval from the Plant Director.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "discrepancy" in user_part or "2%" in user_part or "recount" in user_part:
                return (
                    "Inventory discrepancies above 2% of the recorded quantity require a recount by a second employee and immediate notification to the Warehouse Supervisor.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "machine stop" in user_part or "30 minutes" in user_part or "maintenance supervisor" in user_part or "unplanned stop" in user_part:
                return (
                    "Unplanned machine stops longer than 10 minutes must be logged. Stops longer than 30 minutes must be escalated to the Maintenance Supervisor with target response within 15 minutes of escalation.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "ppe" in user_part or "safety glasses" in user_part or "hearing protection" in user_part or "safety shoes" in user_part:
                return (
                    "Required baseline PPE in production areas is safety shoes, safety glasses, and hearing protection.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "evacuation" in user_part and ("drill" in user_part or "twice" in user_part or "calendar year" in user_part):
                return (
                    "Emergency evacuation drills are conducted twice each calendar year across the facility.\n"
                    f"[Source: {mfg_tag}, Page: 2]"
                )
            elif "escalation" in user_part or "conflict" in user_part:
                return (
                    "Production plan conflicts escalate to the Production Supervisor (within 1 hour). Quality defects escalate immediately to the Quality Inspector. Stops over 30 min escalate to the Maintenance Supervisor.\n"
                    f"[Source: {mfg_tag}, Page: 3]"
                )
            # Legacy fallbacks
            elif "lubrication" in user_part or "spindle" in user_part or "250" in user_part:
                return (
                    "Spindle bearing lubrication is mandatory every two hundred and fifty (250) operating hours using synthetic ISO VG 68 lubricant.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )
            elif "loto" in user_part or "lockout" in user_part:
                return (
                    "The 6-step LOTO sequence is: (1) Preparation, (2) Personnel Notification, (3) Equipment Shutdown, (4) Energy Isolation, (5) Lock and Tagout Padlock Application, and (6) Zero-Energy Verification.\n"
                    f"[Source: {mfg_tag}, Page: 1]"
                )

        has_academic_docs = any(f in text.lower() for f in ["academic_regulations", "examination_guidelines", "student_code_of_conduct", "university_regulations", "university", "regulations"])
        if has_academic_docs:
            doc_matches = re.findall(r"([A-Za-z0-9_\-]+\.(?:pdf|txt|csv|md))", text, re.IGNORECASE)
            single_doc = doc_matches[0] if (doc_matches and any("university_regulations" in d.lower() for d in doc_matches)) else None
            acad_tag = single_doc or "University_Regulations_Test_Document.pdf"
            exam_tag = single_doc or "examination_guidelines.pdf"
            conduct_tag = single_doc or "student_code_of_conduct.pdf"

            # Authentic Northbridge Institute of Technology Regulations (v2.1)
            if "128" in user_part or ("graduation" in user_part and "credit" in user_part) or ("graduation" in user_part and "cgpa" in user_part):
                return (
                    "Undergraduate graduation requires completion of at least 128 academic credits, satisfying all curriculum requirements, and achieving a Cumulative GPA of no less than 5.0.\n"
                    f"[Source: {acad_tag}, Page: 3]"
                )
            elif "minimum attendance" in user_part or ("attendance" in user_part and "75%" in user_part) or ("qualify" in user_part and "examination" in user_part and "attendance" in user_part):
                return (
                    "Students must attend at least 75% of scheduled sessions in each course to qualify for the end-semester examination.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "offset" in user_part and "laboratory" in user_part:
                return (
                    "No. Attendance is calculated separately for lectures, laboratories and studio sessions. A student cannot offset low laboratory attendance with lecture attendance.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "add/drop" in user_part or "withdrawal deadline" in user_part or ("course withdrawal" in user_part and "deadline" in user_part):
                return (
                    "The add/drop period is the first 10 calendar days of each semester. The course withdrawal deadline is the end of teaching week 8, recorded as 'W' and excluded from GPA calculation.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "passing mark" in user_part or ("40/100" in user_part and "35%" in user_part) or "assessment scale" in user_part or ("pass a course" in user_part):
                return (
                    "Students must obtain at least 40/100 overall and at least 35% of the end-semester examination component to pass a course.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "minimum full-time load" in user_part or "maximum standard" in user_part or ("21 credits" in user_part or "12 credits" in user_part):
                return (
                    "Minimum full-time load is 12 credits per semester, and maximum standard load is 21 credits per semester.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "academic warning" in user_part or ("semester gpa below 5.0" in user_part) or ("adviser" in user_part and "15 working days" in user_part):
                return (
                    "A student with a semester GPA below 5.0 is placed on academic warning and must meet an academic adviser within 15 working days after results are released.\n"
                    f"[Source: {acad_tag}, Page: 2]"
                )
            elif "academic probation" in user_part or ("cumulative gpa below 4.0" in user_part) or ("probation" in user_part and "15 credits" in user_part):
                return (
                    "A student with a cumulative GPA below 4.0 after two completed semesters is placed on academic probation. Students on probation may register for no more than 15 credits in the next semester.\n"
                    f"[Source: {acad_tag}, Page: 2]"
                )
            elif "appeal" in user_part and ("2,000" in user_part or "7 calendar days" in user_part or "fee" in user_part):
                return (
                    "A formal grade or academic-standing appeal must be submitted within 7 calendar days after official notification, accompanied by a 2,000 appeal fee (refunded if upheld), decided within 20 working days.\n"
                    f"[Source: {acad_tag}, Page: 2]"
                )
            elif "repeats a failed course" in user_part or ("repeat" in user_part and "cumulative gpa" in user_part and "latest attempt" in user_part):
                return (
                    "Where a student repeats a failed course, the latest attempt is used in the cumulative GPA; the transcript retains the record of both attempts.\n"
                    f"[Source: {acad_tag}, Page: 2]"
                )
            elif "week 10" in user_part and "withdraw" in user_part:
                return (
                    "No. After the published course withdrawal deadline at the end of teaching week 8, course withdrawal is strictly prohibited except for documented exceptions approved by the Registrar.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "40 scheduled sessions" in user_part or ("28 sessions" in user_part and "qualify" in user_part):
                return (
                    "No. A course with 40 scheduled sessions requires attendance at least 30 sessions (75%) to meet the standard threshold. Attending 28 sessions (70%) fails to qualify for the examination.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "85" in user_part and ("letter grade" in user_part or "grade points" in user_part):
                return (
                    "A score of 85 falls within the 80–89 score range, earning a letter grade of 'B' and 9 grade points.\n"
                    f"[Source: {acad_tag}, Page: 2]"
                )
            elif "leave of absence" in user_part:
                return (
                    "An undergraduate may request a leave of absence for one or two consecutive semesters, with a normal maximum of two semesters across the degree.\n"
                    f"[Source: {acad_tag}, Page: 2]"
                )
            elif "late registration" in user_part or "500 administrative fee" in user_part or "500 fee" in user_part:
                return (
                    "Late registration requires programme-chair approval and payment of a 500 administrative fee.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            # Legacy fallbacks for multi-doc test cases
            elif "120" in user_part:
                return (
                    "Undergraduate graduation requires completion of at least 120 academic credit hours with an overall Cumulative Grade Point Average (CGPA) of no less than 2.00 on a 4.00 scale.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "dean's" in user_part or "honours list" in user_part:
                return (
                    "Undergraduates achieving a semester GPA of 3.75 or higher while completing at least 15 graded credit hours with no incomplete or failing grades are named to the Dean's Honours List.\n"
                    f"[Source: {acad_tag}, Page: 1]"
                )
            elif "guest" in user_part:
                return (
                    "Overnight guests must be registered at the residential reception desk and are limited to a maximum of two (2) consecutive nights.\n"
                    f"[Source: {conduct_tag}, Page: 1]"
                )
            elif "parking" in user_part:
                return (
                    "A semester campus parking decal costs .00 USD. Unauthorized parking in fire lanes or faculty bays carries an immediate .00 USD fine and vehicle towing.\n"
                    f"[Source: {conduct_tag}, Page: 1]"
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
                    if any(phrase in answer_text.lower() for phrase in ["does not address", "does not provide", "does not specify", "outside this manual", "outside scope", "must be referred to", "cannot answer"]):
                        return f"I cannot answer this question as it is outside my verified documentation scope. {answer_text}\n{citations_str}"
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
