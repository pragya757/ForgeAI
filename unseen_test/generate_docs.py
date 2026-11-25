import os
import pymupdf

def generate_unseen_docs(target_dir: str):
    os.makedirs(target_dir, exist_ok=True)

    # 1. academic_regulations.pdf
    doc1 = pymupdf.open()
    page1 = doc1.new_page()
    reg_text = """ST. JUDE METROPOLITAN UNIVERSITY - UNDERGRADUATE ACADEMIC REGULATIONS
POLICY DOCUMENT REF: REG-ACAD-2025 | APPLICABILITY: ALL DEGREE CANDIDATES

SECTION 1: DEGREE REQUIREMENTS & CREDIT STRUCTURE
1.1 Graduation Credits: Conformance to degree requirements requires successful completion of at least one hundred and twenty (120) academic credit hours with an overall Cumulative Grade Point Average (CGPA) of no less than 2.00 on a 4.00 scale.
1.2 Maximum Semester Course Load: Full-time undergraduate students may enroll in a maximum of eighteen (18) credit hours per standard 15-week semester. Overload enrollment up to twenty-one (21) credit hours requires prior written authorization from the Dean of Academic Affairs and a minimum prior CGPA of 3.50.
1.3 Transfer Credit Allowances: A maximum of sixty (60) transfer credits from accredited collegiate institutions may be applied toward an undergraduate degree. Transfer credits must carry a minimum earned grade of 'C' (2.0) and are recorded without affecting the university CGPA calculation.

SECTION 2: GRADING CRITERIA & ACADEMIC STANDING
2.1 Grading Scale: Grades correspond to numeric quality points: A (4.00), A- (3.70), B+ (3.30), B (3.00), B- (2.70), C+ (2.30), C (2.00), C- (1.70), D (1.00), F (0.00).
2.2 Dean's Honours List: Undergraduates achieving a semester GPA of 3.75 or higher while completing at least fifteen (15) graded credit hours with no incomplete or failing grades are named to the Dean's Honours List.
2.3 Academic Good Standing: A student maintaining a CGPA of 2.00 or higher is in Academic Good Standing.
2.4 Academic Warning & Probation: A student whose CGPA drops below 2.00 is placed on Academic Warning for one semester. If the CGPA remains below 2.00 after the warning semester, the student is placed on Academic Probation.
2.5 Academic Suspension: A student failing to attain a CGPA of 2.00 after two (2) consecutive semesters on Academic Probation is subjected to mandatory Academic Suspension for a minimum period of one calendar year.

SECTION 3: COURSE REGISTRATION, WITHDRAWAL & REPEATS
3.1 Add/Drop Period: Courses may be added or dropped during the first two (2) weeks of the semester without transcript notation.
3.2 Official Course Withdrawal: Students may withdraw from a course through the end of Week 8. A grade of 'W' is assigned, which carries no quality points and does not affect the CGPA. Course withdrawals after Week 8 are prohibited except for verified medical emergencies.
3.3 Course Repeat Policy: An undergraduate may repeat any course in which an original grade of 'D' or 'F' was earned, up to a maximum of two (2) repeats per course. The higher grade is utilized in the CGPA calculation, although all course attempts remain permanent on the transcript.
"""
    page1.insert_text((50, 50), reg_text, fontsize=9.5, lineheight=1.28)
    doc1.save(os.path.join(target_dir, "academic_regulations.pdf"))
    doc1.close()

    # 2. examination_guidelines.pdf
    doc2 = pymupdf.open()
    page2 = doc2.new_page()
    exam_text = """ST. JUDE METROPOLITAN UNIVERSITY - EXAMINATION PROTOCOLS & GUIDELINES
POLICY DOCUMENT REF: EXAM-POL-04 | OFFICE OF THE UNIVERSITY REGISTRAR

SECTION 1: EXAMINATION HALL ADMISSION & CANDIDATE CONDUCT
1.1 Examination Arrival: Candidates must arrive at the examination hall fifteen (15) minutes prior to scheduled start. Students arriving later than thirty (30) minutes after commencement are strictly denied entry and awarded a grade of zero ('F') for the examination.
1.2 Identification Requirement: Presentation of a valid University Student Identification Card is mandatory to sit for any invigilated examination.
1.3 Prohibited Electronic Devices: Cellular phones, smartwatches, programmable graphing calculators, and wireless transmission devices are strictly barred from examination venues. Possession of an unauthorized device during an exam incurs Level 2 Disciplinary Sanctions.

SECTION 2: ABSENCE, ILLNESS & SPECIAL DEFERRALS
2.1 Illness on Exam Day: A candidate incapacitated by acute illness must report to the University Health Centre for clinical certification. Medical certificates from external physicians must be verified by the University Medical Director within forty-eight (48) hours of the exam.
2.2 Deferred / Make-up Examinations: Approved medical deferrals allow the candidate to sit for a scheduled Make-up Examination during Week 1 of the subsequent academic term. Unexcused absence results in an irrecoverable grade of '0'.
2.3 Incomplete ('I') Grades: An 'I' grade is awarded exclusively when a student in good academic standing has completed at least seventy-five percent (75%) of coursework but cannot complete final assessments due to certified emergency. The 'I' grade must be cleared within six (6) weeks of the following term or automatically lapses into an 'F'.

SECTION 3: REGISTRATION & GRADE RE-EVALUATION APPEALS
3.1 Formal Grade Appeals: Students disputing a final course evaluation must file a written Grade Re-evaluation Petition with the Faculty Dean within ten (10) business days following official grade release.
3.2 Non-Refundable Fee: A non-refundable administrative processing fee of fifty dollars ($50.00 USD) applies to each course evaluation appeal.
3.3 Re-grading Outcomes: The re-evaluated grade assigned by an independent secondary examiner is final and may result in an increased, unchanged, or decreased grade.
"""
    page2.insert_text((50, 50), exam_text, fontsize=9.5, lineheight=1.28)
    doc2.save(os.path.join(target_dir, "examination_guidelines.pdf"))
    doc2.close()

    # 3. student_code_of_conduct.pdf
    doc3 = pymupdf.open()
    page3 = doc3.new_page()
    conduct_text = """ST. JUDE METROPOLITAN UNIVERSITY - STUDENT CODE OF CONDUCT & COMMUNITY STANDARDS
POLICY DOCUMENT REF: STU-CODE-2024 | DIVISION OF STUDENT AFFAIRS

SECTION 1: ACADEMIC HONESTY & SCHOLASTIC INTEGRITY
1.1 Violations of Scholastic Integrity: Plagiarism, unauthorized collaboration, fabrication of research findings, and unauthorized possession of assessment materials constitute Level 1 Academic Misconduct.
1.2 First Offense Penalties: For an initial validated offense, the student receives an automatic zero ('0') on the assessment and a one-semester disciplinary notation on the internal record.
1.3 Second Offense Penalties: Any subsequent violation of scholastic integrity results in immediate referral to the Senate Disciplinary Tribunal with recommendation for permanent expulsion.

SECTION 2: CAMPUS LIVING & RESIDENTIAL REGULATIONS
2.1 Residential Quiet Hours: Quiet hours in all university dormitories and residential colleges are enforced from 22:00 to 08:00 Sunday through Thursday, and from 24:00 to 09:00 Friday and Saturday.
2.2 Guest Policy: Overnight guests must be registered at the residential reception desk and are limited to a maximum of two (2) consecutive nights.
2.3 Substance Prohibitions: Smoking, vaping, and the possession of illicit substances are strictly prohibited on all university grounds and residential halls.

SECTION 3: VEHICLE PARKING & TRAFFIC REGULATIONS
3.1 Campus Parking Permits: All motorized vehicles operating on campus must display a valid semester parking decal purchased through the Campus Security Office for one hundred and twenty dollars ($120.00 USD).
3.2 Unauthorized Parking Fines: Unauthorized parking in designated faculty bays, fire lanes, or accessible parking spaces carries an immediate seventy-five dollar ($75.00 USD) fine and vehicle wheel immobilization (towing).

SECTION 4: SCOPE EXCLUSIONS & NON-UNIVERSITY JURISDICTIONS
4.1 The Division of Student Affairs does NOT administer international student visa renewals, embassy legalizations, tuition fee wire transfers, or external private apartment leasing disputes. Students requiring consular or financial advice are directed to the International Students Office and Bursar respectively.
"""
    page3.insert_text((50, 50), conduct_text, fontsize=9.5, lineheight=1.28)
    doc3.save(os.path.join(target_dir, "student_code_of_conduct.pdf"))
    doc3.close()

    print(f"Successfully generated 3 unseen university policy documents in: {target_dir}")

if __name__ == "__main__":
    generate_unseen_docs("unseen_test/documents")
