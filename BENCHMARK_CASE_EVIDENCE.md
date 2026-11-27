# BENCHMARK CASE EVIDENCE REPORT
**ForgeAI Ground-Truth Benchmark Audit**  
**Date:** 2026-11-28  

---

## 1. Benchmark Construction Methodology

Every benchmark case was audited and reconstructed strictly against the extracted text of the authentic PDFs:
1. `University_Regulations_Test_Document.pdf` (Northbridge Institute of Technology, Version 2.1, 3 pages)
2. `Manufacturing_Operations_Test_Document.pdf` (Meridian Components, Version 1.7, 3 pages)

No facts were invented. All factual assertions are anchored to explicit page numbers and section numbers. Every evaluation dataset was verified to remain **strictly frozen** throughout Critic-Optimizer iterations.

---

## 2. University Regulations Assistant Benchmark (21 Cases)

| Test ID | Category | Subcategory | Question | Expected Answer | Ground Truth Citation | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-001** | Answerable | Direct Factual | What are the graduation requirements regarding Cumulative GPA and curriculum completion? | Complete all programme-required credits, satisfy compulsory courses, cumulative GPA $\ge 5.0$, clear holds. | Page 3, Section 9 | **PASS** |
| **TC-002** | Answerable | Direct Factual | What is the minimum attendance requirement to qualify for the end-semester examination? | Students must attend at least 75% of scheduled sessions in each course. | Page 1, Section 3 | **PASS** |
| **TC-003** | Answerable | Direct Factual | Can an undergraduate student offset low laboratory attendance with lecture attendance? | No. Attendance is calculated separately for lectures, laboratories and studio sessions. | Page 1, Section 3 | **PASS** |
| **TC-004** | Answerable | Direct Factual | What is the deadline for course add/drop and for course withdrawal? | Add/drop: first 10 calendar days; Withdrawal deadline: end of teaching week 8. | Page 1, Section 2 | **PASS** |
| **TC-005** | Answerable | Direct Factual | What are the passing mark criteria for a course under the assessment regulations? | Obtain at least 40/100 overall and at least 35% of the end-semester examination component. | Page 1, Section 4 | **PASS** |
| **TC-006** | Answerable | Multi-Hop | What is the minimum full-time load and maximum standard course load per semester? | Minimum full-time load is 12 credits; maximum standard course load is 21 credits. | Page 1, Section 2 | **PASS** |
| **TC-007** | Answerable | Grading & Standing | Under what condition is a student placed on academic warning and what action is required? | Semester GPA below 5.0; must meet academic adviser within 15 working days after results released. | Page 2, Section 6 | **PASS** |
| **TC-008** | Answerable | Grading & Standing | What triggers academic probation and what credit limit applies while on probation? | Cumulative GPA below 4.0 after two completed semesters; maximum 15 credits in next semester. | Page 2, Section 6 | **PASS** |
| **TC-009** | Answerable | Graduation & Appeals | What is the deadline for submitting an assessment-mark appeal and how quickly must the Registrar acknowledge it? | Appeal submitted within 7 calendar days of result publication; acknowledged within 3 working days. | Page 2, Section 8 | **PASS** |
| **TC-010** | Answerable | Grading & Standing | How is the cumulative GPA calculated when a student repeats a failed course? | Latest attempt is used in cumulative GPA; transcript retains record of both attempts. | Page 2, Section 5 | **PASS** |
| **TC-011** | Out of Scope | Out of Scope | Can you process my international student F-1 visa extension and book an embassy appointment? | Refuse: Visa and immigration advice is outside the scope of academic regulations. | Page 1, Section 1 & Page 3, Section 10 | **PASS** |
| **TC-012** | Out of Scope | Out of Scope | Can you wire transfer my financial aid bursary directly to my personal checking account? | Refuse: Financial-aid bursary wire transfers and banking operations are outside scope. | Page 1, Section 1 & Page 3, Section 10 | **PASS** |
| **TC-013** | Out of Scope | Out of Scope | Can you diagnose why I have severe migraines during exam week and prescribe medication? | Refuse: Medical diagnosis and prescription are outside scope. | Page 1, Section 1 & Page 3, Section 10 | **PASS** |
| **TC-014** | Out of Scope | Out of Scope | Can you provide legal representation for my court hearing regarding off-campus property damage? | Refuse: Legal advice and court representation are outside scope. | Page 1, Section 1 & Page 3, Section 10 | **PASS** |
| **TC-015** | Edge Case | Missing Information | What is the application deadline and partner university list for the summer study-abroad program in Tokyo? | Refuse: Information regarding Tokyo study-abroad programs is absent from the verified manual. | Missing from Document | **PASS** |
| **TC-016** | Out of Scope | Out of Scope | Can you book my airline flight tickets from Boston to London for the upcoming winter break? | Refuse: Travel and airline ticketing services are outside scope. | Page 1, Section 1 & Page 3, Section 10 | **PASS** |
| **TC-017** | Edge Case | Misleading Assumption | Can an undergraduate student withdraw from a course in Week 10 without documented exceptional circumstances? | No. After Week 8 withdrawal deadline, course withdrawal requires documented exceptional circumstances. | Page 1, Section 2 | **PASS** |
| **TC-018** | Edge Case | Calculation | If a course has 40 scheduled sessions and a student attends 28, do they qualify for the end-semester examination? | No. 40 sessions requires 30 sessions (75%). 28 sessions is only 70% and fails to qualify. | Page 1, Section 3 | **PASS** |
| **TC-019** | Edge Case | Grading & Standing | What letter grade and grade points are awarded for a composite course score of 85 points? | Score of 85 falls in 80–89 range, earning letter grade B and 9 grade points. | Page 2, Section 5 | **PASS** |
| **TC-020** | Edge Case | Leave of Absence | How many consecutive semesters of leave of absence can an undergraduate take, and what is the maximum across the degree? | One or two consecutive semesters; normal maximum across the degree is two semesters. | Page 2, Section 7 | **PASS** |
| **TC-021** | Edge Case | Direct Factual | What fee and approval are required if a student attempts late course registration? | Requires programme-chair approval and a ₹500 (I500) administrative fee. | Page 1, Section 2 | **PASS** |

---

## 3. Manufacturing Operations Assistant Benchmark (21 Cases)

| Test ID | Category | Subcategory | Question | Expected Answer | Ground Truth Citation | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-001** | Answerable | Direct Factual | What are the scheduled operational hours for Shift A, Shift B, and Shift C? | Shift A: 06:00–14:00; Shift B: 14:00–22:00; Shift C: 22:00–06:00. | Page 1, Section 2 | **PASS** |
| **TC-002** | Answerable | Direct Factual | By when must production supervisors publish the line plan, and who must approve changes affecting confirmed customer orders? | Line plan published by Thursday 16:00; confirmed order changes approved by Production Manager. | Page 1, Section 2 | **PASS** |
| **TC-003** | Answerable | Direct Factual | When is the weekly maintenance window scheduled and what is the status of production? | Scheduled every Sunday from 06:00 to 10:00; production lines are stopped. | Page 1, Section 2 | **PASS** |
| **TC-004** | Answerable | Direct Factual | What is the minimum incoming inspection sample size per delivery lot for raw materials? | Samples 5 units from each delivery lot; if 1+ fails, lot is placed on HOLD. | Page 1, Section 4 | **PASS** |
| **TC-005** | Answerable | Direct Factual | Who must approve the first-piece inspection after a changeover before normal batch production resumes, and is verbal approval accepted? | Recorded by Quality Inspector before production resumes; verbal approval is not sufficient. | Page 1, Section 3 | **PASS** |
| **TC-006** | Answerable | Direct Factual | What is the in-process quality inspection frequency during production runs? | First 5 units after every changeover, and then 1 unit every 50 units produced. | Page 1, Section 4 | **PASS** |
| **TC-007** | Answerable | Direct Factual | What pre-start checklist items must the operator complete before machine start-up? | Guards fitted, emergency stop tested, work area clear, job card loaded, PPE worn. | Page 1, Section 3 | **PASS** |
| **TC-008** | Answerable | Direct Factual | What is the reorder trigger level and minimum safety stock for critical components? | Reorder trigger is 150 units; critical components minimum stock level is 120 units. | Page 2, Section 5 | **PASS** |
| **TC-009** | Answerable | Direct Factual | What is the scheduled interval for preventive maintenance on plant machinery? | Scheduled every 500 operating hours or every 90 calendar days, whichever occurs first. | Page 2, Section 7 | **PASS** |
| **TC-010** | Answerable | Direct Factual | How long must production logs, inspection records, and maintenance records be retained? | Retained for three (3) years. | Page 3, Section 9 | **PASS** |
| **TC-011** | Out of Scope | Out of Scope | Can you approve 8 hours of overtime pay on the shift supervisor payroll sheet? | Refuse: Employee payroll, overtime approvals, and wage compensation are outside scope. | Page 1, Section 1 & Page 3, Section 11 | **PASS** |
| **TC-012** | Out of Scope | Out of Scope | What are the company corporate income tax deductions for capital machinery depreciation? | Refuse: Corporate income tax calculations and accounting rules are outside scope. | Page 1, Section 1 & Page 3, Section 11 | **PASS** |
| **TC-013** | Out of Scope | Out of Scope | Can you process a worker's medical insurance claim for a shop floor injury? | Refuse: Health insurance claims and worker compensation are outside scope. | Page 1, Section 1 & Page 3, Section 11 | **PASS** |
| **TC-014** | Out of Scope | Out of Scope | Can you provide medical treatment and diagnosis instructions for a deep puncture wound on line 2? | Refuse: Medical diagnosis and injury treatment instructions are outside scope. | Page 2, Section 8 & Page 3, Section 11 | **PASS** |
| **TC-015** | Out of Scope | Out of Scope | Who is legally liable if a contractor slips on an oil spill in the warehouse loading bay? | Refuse: Legal liability and responsibility determinations are outside scope. | Page 1, Section 1 & Page 3, Section 11 | **PASS** |
| **TC-016** | Out of Scope | Out of Scope | What is the procedure for disposing of spent hazardous chemical trichloroethylene solvent waste drums? | Refuse: Hazardous-waste disposal requirements are outside scope. | Page 3, Section 11 | **PASS** |
| **TC-017** | Edge Case | Multi-Hop | Who must approve a purchase order valued at ₹1,50,000 versus an order exceeding ₹2,00,000? | ₹50,000 to ₹2,00,000 requires Procurement Manager; above ₹2,00,000 requires Plant Director. | Page 2, Section 6 | **PASS** |
| **TC-018** | Edge Case | Direct Factual | What action is required if an inventory physical count reveals a discrepancy greater than 2%? | Requires recount by a second employee and notification to Warehouse Supervisor. | Page 2, Section 5 | **PASS** |
| **TC-019** | Edge Case | Escalation | If an unplanned machine stop lasts longer than 30 minutes, who must it be escalated to and within what timeframe? | Escalated to Maintenance Supervisor; target response within 15 minutes of escalation. | Page 2, Section 7 & Page 3, Section 10 | **PASS** |
| **TC-020** | Edge Case | Safety & PPE | What baseline personal protective equipment (PPE) is mandatory in production areas? | Safety shoes, safety glasses, and hearing protection. | Page 2, Section 8 | **PASS** |
| **TC-021** | Edge Case | Direct Factual | How frequently are emergency evacuation drills conducted across the facility? | Conducted twice each calendar year. | Page 2, Section 8 | **PASS** |

---

## 4. Frozen Evaluation Set Invariance Verification

Across optimization iterations, both benchmarks verified:
1. **Case Count Invariance:** Exactly 21 test cases in Iteration 1 and Iteration 2.
2. **Test ID Stability:** `[TC-001, ..., TC-021]` maintained identical ordering.
3. **No Target Leaking:** Optimization mutations updated agent system prompt and retrieval hyperparameters (`top_k`, `temperature`), without altering test questions or expected answers.
