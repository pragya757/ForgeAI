# DOCUMENT FACT VERIFICATION REPORT
**ForgeAI Independent Verification Document Audit**  
**Date:** 2026-11-28  
**Scope:** Extraction and ground-truth verification of `University_Regulations_Test_Document.pdf` and `Manufacturing_Operations_Test_Document.pdf`.

---

## 1. Document Identity & Integrity Checksums

| Metric | University Regulations Document | Manufacturing Operations Document |
| :--- | :--- | :--- |
| **Filename** | `University_Regulations_Test_Document.pdf` | `Manufacturing_Operations_Test_Document.pdf` |
| **Full Title** | *Northbridge Institute of Technology — Undergraduate Academic Regulations* | *Meridian Components Manufacturing Plant — Operations Manual* |
| **Catalog / Version** | Academic Year 2026–27 \| Version 2.1 \| Effective 1 August 2026 | Version 1.7 \| Effective 1 September 2026 |
| **Total Pages** | 3 pages | 3 pages |
| **Exact File Size** | 33,954 bytes | 34,782 bytes |
| **SHA-256 Checksum** | `8f40715e751a66bd3b4134142e635b7c3938ba64093c1e7f255f7f7b2790da3b` | `95e1b9daf774a2610310ad1aa7ec550256826e82c86bd08de6452383900896e9` |
| **Integrity Status** | **AUTHENTIC ORIGINAL (MATCHED)** | **AUTHENTIC ORIGINAL (MATCHED)** |

---

## 2. Manufacturing Operations Fact Verification Table

| Item / Known Topic | PDF Page | Section | Exact Source Statement in PDF | Benchmark Expected Answer | Verification Result |
| :--- | :---: | :---: | :--- | :--- | :---: |
| **Sunday Maintenance Window** | Page 1 | Sec 2 & Quick Ref | "Weekly maintenance window: Sunday 06:00–10:00 (Production lines stopped)" | Scheduled every Sunday from 06:00 to 10:00; production lines stopped. | **MATCH** *(Historical audit bug of 06:00–14:00 fixed)* |
| **Incoming Sample Size** | Page 1 | Sec 4 & Quick Ref | "Incoming material inspection samples five units from each delivery lot. If one or more sampled units fail a specified check, the lot is placed on HOLD pending expanded inspection." | Samples 5 units from each delivery lot; if 1+ fails, placed on HOLD. | **MATCH** |
| **In-Process Inspection Frequency** | Page 1 | Sec 4 & Quick Ref | "During production, operators inspect the first five units after every changeover and then one unit every 50 units produced." | First 5 units after changeover, then 1 unit every 50 units produced. | **MATCH** |
| **Critical Dimensional Tolerance** | Page 1 | Sec 1 & 4 | "It does not establish product-design tolerances beyond those listed here... Any unit outside the approved drawing tolerance must be tagged and moved to the red nonconforming-material area." | Standard drawing tolerance; tagged and moved to red nonconforming area. | **MATCH** *(Fabricated "+/- 0.05 mm" removed)* |
| **Quality Hold Trigger** | Page 1 | Sec 4 | "If one or more sampled units fail a specified check, the lot is placed on HOLD pending expanded inspection." | Placed on HOLD pending expanded inspection. | **MATCH** *(Fabricated "3% defect rate" removed)* |
| **Line Plan Publication & Order Changes** | Page 1 | Sec 2 | "Production supervisors publish the next week's line plan by Thursday 16:00. Any change affecting a confirmed customer order must be approved by the Production Manager." | Published Thursday by 16:00; confirmed order changes approved by Production Manager. | **MATCH** |
| **Machine Operation Authorization** | Page 1 | Sec 3 | "Only employees listed as currently qualified on the machine authorization register may operate a production machine without direct supervision." | Only employees on machine authorization register may operate unsupervised. | **MATCH** |
| **Pre-Start Checklist** | Page 1 | Sec 3 | "Before start-up, the operator completes the daily pre-start checklist: guards fitted, emergency stop tested, work area clear, correct job card loaded and required personal protective equipment worn." | Guards fitted, emergency stop tested, work area clear, job card loaded, PPE worn. | **MATCH** |
| **First-Piece Approval** | Page 1 | Sec 3 | "First-piece approval must be recorded by a Quality Inspector before normal batch production resumes. A verbal approval is not sufficient." | Must be recorded by Quality Inspector; verbal approval is not sufficient. | **MATCH** |
| **Reorder Trigger** | Page 2 | Sec 5 & Quick Ref | "Critical components have a minimum stock level of 120 units and a reorder trigger of 150 units. The Procurement Coordinator reviews triggered items each working day." | Reorder trigger is 150 units. | **MATCH** |
| **Critical Minimum Stock** | Page 2 | Sec 5 & Quick Ref | "Critical components have a minimum stock level of 120 units..." | Minimum stock level is 120 units. | **MATCH** |
| **Inventory Discrepancy** | Page 2 | Sec 5 | "Inventory discrepancies above 2% of the recorded quantity require a recount by a second employee and notification to the Warehouse Supervisor." | Recount by second employee and notify Warehouse Supervisor. | **MATCH** |
| **Purchase Order Approvals** | Page 2 | Sec 6 & Sec 10 | "Purchase orders up to I50,000 may be approved by the Procurement Coordinator. Orders above I50,000 and up to I2,00,000 require the Procurement Manager. Orders above I2,00,000 require the Plant Director." | Up to ₹50,000: Procurement Coord; ₹50,000–₹2,00,000: Procurement Mgr; above ₹2,00,000: Plant Director. | **MATCH** |
| **Preventive Maintenance Interval** | Page 2 | Sec 7 & Quick Ref | "Preventive maintenance is scheduled every 500 operating hours or every 90 calendar days, whichever occurs first." | Every 500 operating hours or 90 calendar days, whichever occurs first. | **MATCH** |
| **Machine Stoppage Escalation (>30 min)** | Page 2 | Sec 7 & Sec 10 | "Stops longer than 30 minutes must be escalated to the Maintenance Supervisor. Target response: Within 15 minutes of escalation." | Maintenance Supervisor within 15 minutes. | **MATCH** |
| **Baseline PPE in Production Areas** | Page 2 | Sec 8 | "Required baseline PPE in production areas is safety shoes, safety glasses and hearing protection." | Safety shoes, safety glasses, hearing protection. | **MATCH** |
| **Evacuation Drills** | Page 2 | Sec 8 | "Evacuation drills are conducted twice each calendar year." | Twice each calendar year. | **MATCH** |
| **Record Retention** | Page 3 | Sec 9 & Quick Ref | "Production logs, inspection records, maintenance records and dispatch records must be retained for three years." | 3 years retention period. | **MATCH** |
| **Out-of-Scope Boundary Topics** | Page 3 | Sec 11 | "This manual does not define engineering design approval, statutory permits, employee payroll, income tax, insurance coverage, medical treatment, legal liability, customer contract interpretation or hazardous-waste disposal requirements." | Assistant refuses out-of-scope queries (payroll, taxes, medical treatment, legal liability, hazardous waste). | **MATCH** |

---

## 3. University Regulations Fact Verification Table

| Item / Known Topic | PDF Page | Section | Exact Source Statement in PDF | Benchmark Expected Answer | Verification Result |
| :--- | :---: | :---: | :--- | :--- | :---: |
| **Attendance Threshold** | Page 1 | Sec 3 & Quick Ref | "Students must attend at least 75% of scheduled sessions in each course to qualify for the end-semester examination." | At least 75% attendance in scheduled sessions. | **MATCH** |
| **Component Attendance Calculation** | Page 1 | Sec 3 | "Attendance is calculated separately for lectures, laboratories and studio sessions. A student cannot offset low laboratory attendance with lecture attendance." | Tracked separately; cannot offset lab attendance with lecture hours. | **MATCH** |
| **Add/Drop Period** | Page 1 | Sec 2 & Quick Ref | "Add/drop period: First 10 calendar days of each semester" | First 10 calendar days of each semester. | **MATCH** |
| **Course Withdrawal Deadline** | Page 1 | Sec 2 & Quick Ref | "Course withdrawal deadline: End of teaching week 8. A withdrawn course is recorded as W and is not included in GPA calculation." | By end of teaching week 8; recorded as W, excluded from GPA. | **MATCH** |
| **Full-Time Enrollment Credits** | Page 1 | Sec 2 | "Minimum full-time load: 12 credits per semester. Maximum standard load: 21 credits per semester." | 12 credits minimum, 21 credits maximum standard load. | **MATCH** |
| **Late Course Registration** | Page 1 | Sec 2 | "Late registration: Requires programme-chair approval and a I500 administrative fee" | Programme-chair approval and a ₹500 (I500) fee. | **MATCH** |
| **Passing Score Threshold** | Page 1 | Sec 4 & Quick Ref | "Students must obtain at least 40/100 overall and at least 35% of the end-semester examination component to pass a course." | 40/100 overall and at least 35% of end-semester exam component. | **MATCH** |
| **Examination Absence** | Page 2 | Sec 4 | "An examination absence is recorded as Absent unless the student submits a formal mitigating-circumstances request within three working days after the examination." | Mitigating-circumstances request submitted within 3 working days. | **MATCH** |
| **Grading Scale & GPA Points** | Page 2 | Sec 5 | "A: 90–100 (10 pts), B: 80–89 (9 pts), C: 70–79 (8 pts), D: 60–69 (7 pts), E: 50–59 (6 pts), P: 40–49 (5 pts), F: Below 40 (0 pts)." | Credit-weighted average; B earns 9 pts (80–89). | **MATCH** |
| **Course Repeat Policy** | Page 2 | Sec 5 | "Where a student repeats a failed course, the latest attempt is used in the cumulative GPA; the transcript retains the record of both attempts." | Latest attempt used in cumulative GPA; transcript retains both attempts. | **MATCH** *(Historical assumption of max 2 repeats corrected)* |
| **Academic Warning Trigger** | Page 2 | Sec 6 & Quick Ref | "A student with a semester GPA below 5.0 is placed on academic warning and must meet an academic adviser within 15 working days after results are released." | Semester GPA below 5.0; meet adviser within 15 working days. | **MATCH** |
| **Academic Probation Trigger** | Page 2 | Sec 6 & Quick Ref | "A student with a cumulative GPA below 4.0 after two completed semesters is placed on academic probation." | Cumulative GPA below 4.0 after two completed semesters. | **MATCH** |
| **Probation Credit Ceiling** | Page 2 | Sec 6 | "Students on probation may register for no more than 15 credits in the next semester unless the Academic Progress Committee grants written permission." | Maximum 15 credits in the next semester. | **MATCH** |
| **Leave of Absence Limit** | Page 2 | Sec 7 | "An undergraduate may request a leave of absence for one or two consecutive semesters. The normal maximum across the degree is two semesters." | 1 or 2 consecutive semesters; maximum 2 semesters across degree. | **MATCH** |
| **Formal Mark Appeal Submission** | Page 2 | Sec 8 & Quick Ref | "An assessment-mark appeal must be submitted through the student portal within seven calendar days of the publication of the result." | Within 7 calendar days of result publication. | **MATCH** |
| **Formal Appeal Acknowledgement** | Page 2 | Sec 8 & Quick Ref | "The Registrar acknowledges a formal academic appeal within three working days and normally issues a decision within 15 working days." | Acknowledged within 3 working days; decision within 15 working days. | **MATCH** |
| **Graduation Requirements** | Page 3 | Sec 9 | "To qualify for an undergraduate award, a student must complete all programme-required credits, satisfy compulsory course requirements, achieve a cumulative GPA of at least 5.0 and clear all institutional property and administrative holds." | Complete programme-required credits, compulsory requirements, cumulative GPA $\ge 5.0$, clear holds. | **MATCH** *(Historical assumption of "128 credits" clarified as programme credits)* |
| **Out-of-Scope Boundary Topics** | Page 3 | Sec 10 | "These regulations do not specify scholarship amounts, tuition-refund calculations, visa eligibility, hostel allocation, medical treatment, disability diagnosis, tax obligations or legal liability." | Assistant refuses out-of-scope queries (visa, financial aid, medical diagnosis, legal representation). | **MATCH** |
