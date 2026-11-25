import os
import pymupdf

def create_hr_documents(target_dir: str):
    os.makedirs(target_dir, exist_ok=True)

    # 1. leave_policy.pdf
    doc1 = pymupdf.open()
    page1 = doc1.new_page()
    leave_text = """APEX GLOBAL TECHNOLOGIES - HR POLICY MANUAL
DOCUMENT REF: POL-HR-001 | VERSION 3.2 | ANNUAL REVISION

SECTION 1: PURPOSE AND APPLICABILITY
This policy governs all paid and unpaid leave entitlements for standard full-time employees of Apex Global Technologies.

SECTION 2: ANNUAL LEAVE (VACATION)
2.1 Entitlement: Full-time employees accrue twenty (20) working days of paid annual leave per calendar year.
2.2 Accrual: Leave accrues monthly on a pro-rata basis (1.67 days per full calendar month worked).
2.3 Probation Period Restriction: During the initial three (3) month probationary period, employees accrue annual leave but cannot take paid vacation days until successful confirmation.
2.4 Carryover Limits: Employees may carry over a maximum of five (5) unused annual leave days into the subsequent calendar year. All carried-over days must be utilized prior to March 31, after which they are forfeited.
2.5 Advance Notice: Requests for leave of five (5) consecutive days or more must be submitted via the HR Portal at least fourteen (14) days in advance and approved by the line manager.
2.6 Notice Period Restriction: During an employee's formal resignation notice period, annual leave cannot be taken to shorten the required notice period unless explicitly approved in writing by HR and management.

SECTION 3: SICK LEAVE & MEDICAL EMERGENCIES
3.1 Entitlement: Employees are allocated ten (10) days of fully paid sick leave per calendar year. Sick leave is an independent allotment and cannot be converted into annual leave.
3.2 Medical Certification: For any sick leave duration exceeding two (2) consecutive working days, an official medical certificate from a registered physician is mandatory upon return to work.
3.3 Notification: Employees must notify their supervisor via email or phone by 09:00 AM on the first day of illness.

SECTION 4: COMPASSIONATE & BEREAVEMENT LEAVE
4.1 Entitlement: Up to five (5) consecutive paid working days are granted in the event of the death of an immediate family member (spouse, child, parent, or sibling).
4.2 Extended Family: Two (2) days of paid leave are granted for the death of grandparents or in-laws.

SECTION 5: PARENTAL & PATERNITY LEAVE
5.1 Maternity Leave: Eligible female employees receive twelve (12) weeks of fully paid maternity leave.
5.2 Paternity Leave: Eligible male employees receive five (5) consecutive days of paid paternity leave upon presentation of the certified birth certificate or adoption order.
"""
    page1.insert_text((50, 60), leave_text, fontsize=10, lineheight=1.3)
    doc1.save(os.path.join(target_dir, "leave_policy.pdf"))
    doc1.close()

    # 2. attendance_policy.pdf
    doc2 = pymupdf.open()
    page2 = doc2.new_page()
    att_text = """APEX GLOBAL TECHNOLOGIES - WORKPLACE ATTENDANCE & HOURS POLICY
DOCUMENT REF: POL-HR-002 | REVISED OPERATIONAL STANDARDS

SECTION 1: WORKING HOURS & COLLABORATION CORE
1.1 Standard Business Hours: The standard working week is Monday through Friday. Standard office hours are 08:30 to 17:30, including a one-hour unpaid lunch break.
1.2 Core Hours: Mandatory core collaboration hours are 10:00 to 16:00. All employees, whether in-office or working remotely, must be accessible during core hours.
1.3 Work-from-Home (WFH): Up to two (2) days of remote work per week are permitted with manager approval. Home office equipment reimbursements are not provided under standard policy.

SECTION 2: PUNCTUALITY & TARDINESS
2.1 Grace Window: A fifteen (15) minute grace period is permitted for unplanned commuting delays. Arrivals up to 08:45 are tolerated without formal penalty at most twice (2) per calendar month.
2.2 Recurring Tardiness: Recurring arrivals after 08:30 beyond the two monthly grace occurrences are recorded as unexcused tardiness and trigger formal management review.

SECTION 3: PUBLIC HOLIDAYS & OVERTIME RULES
3.1 Official Holidays: Apex observes eleven (11) designated public holidays annually as published on the company intranet.
3.2 Salaried Exempt Personnel: Salaried software engineers and managerial employees are classified as exempt and do not receive hourly overtime pay.
3.3 Compensatory Day Off (In-Lieu): If an exempt salaried employee is required to work on a declared public holiday, they receive an equivalent compensatory day off (day-in-lieu) to be taken within sixty (60) days.

SECTION 4: UNEXCUSED ABSENCES & JOB ABANDONMENT
4.1 Notification Requirement: Any unscheduled absence must be reported to the line manager by 08:45 AM.
4.2 Job Abandonment Threshold: Absence from work for three (3) consecutive working days without authorized communication or notice is deemed voluntary job abandonment and constitutes grounds for immediate termination.
"""
    page2.insert_text((50, 60), att_text, fontsize=10, lineheight=1.3)
    doc2.save(os.path.join(target_dir, "attendance_policy.pdf"))
    doc2.close()

    # 3. employee_handbook.pdf
    doc3 = pymupdf.open()
    page3 = doc3.new_page()
    hb_text = """APEX GLOBAL TECHNOLOGIES - GENERAL EMPLOYEE HANDBOOK
DOCUMENT REF: HB-CORP-2024 | GENERAL CODE OF CONDUCT & OPERATIONS

SECTION 1: INTRODUCTION & ETHICAL CODE
Apex Global Technologies is committed to maintaining a collaborative, professional, and harassment-free workplace. All staff must treat colleagues, partners, and clients with respect and dignity.

SECTION 2: PROBATIONARY EMPLOYMENT
2.1 Initial Assessment: All newly hired employees undergo a probationary evaluation period of three (3) months starting on their first day of active employment.
2.2 Probation Extension: Management reserves the right to extend the probationary period by up to an additional three (3) months if performance criteria require further evaluation.
2.3 Confirmation: Successful confirmation is communicated formally in writing following a 90-day review.
2.4 Probation Leave Rules: As stated in the Leave Policy, accrued annual leave cannot be taken during probation.

SECTION 3: COMPENSATION CONFIDENTIALITY & PROHIBITIONS
3.1 Strict Confidentiality: Individual salary details, performance bonus percentages, executive compensation, and equity vesting schedules are strictly confidential.
3.2 Inquiry Refusal: Internal knowledge agents and assistants are explicitly prohibited from retrieving or disclosing individual compensation records. Inquiries must be directed to Finance.

SECTION 4: PROGRESSIVE DISCIPLINARY PROCEDURE
8.1 Disciplinary Framework: Breaches of company policy or conduct standards are addressed through progressive discipline consisting of four sequential tiers:
   Tier 1: Formal Verbal Counseling (documented by manager)
   Tier 2: Written Warning (placed in HR employee file for 12 months)
   Tier 3: Final Written Warning accompanied by a 30-day Performance Improvement Plan (PIP)
   Tier 4: Termination of Employment for failure to remediate conduct or performance.
8.2 Gross Misconduct: Gross misconduct, theft, fraud, violence, or deliberate harassment results in immediate summary termination without prior warning.

SECTION 5: RESIGNATION & NOTICE PERIOD
9.1 Resignation Notice: Standard confirmed employees must provide thirty (30) calendar days written notice.
9.2 Notice Offsetting: Accrued annual leave days cannot be used to offset or shorten the thirty-day notice period without written sign-off from the Department Head and HR.
"""
    page3.insert_text((50, 60), hb_text, fontsize=10, lineheight=1.3)
    doc3.save(os.path.join(target_dir, "employee_handbook.pdf"))
    doc3.close()
    print(f"Successfully generated HR documents in: {target_dir}")

if __name__ == "__main__":
    create_hr_documents("demos/hr_assistant/documents")
