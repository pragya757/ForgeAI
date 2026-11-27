import pymupdf
import os

def create_university_regulations_pdf(pdf_path: str):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)  # Standard Letter size
    
    content = """ST. JUDE METROPOLITAN UNIVERSITY
COMPREHENSIVE ACADEMIC REGULATIONS & STUDENT POLICY MANUAL
Document Reference: REG-ACAD-UNIV-2025 | Applicability: All Degree Candidates & Resident Students

SECTION 1: DEGREE REQUIREMENTS & CREDIT STRUCTURE
1.1 Graduation Credits & Minimum CGPA: Conformance to undergraduate degree requirements mandates successful completion of at least one hundred and twenty (120) academic credit hours with an overall Cumulative Grade Point Average (CGPA) of no less than 2.00 on a 4.00 scale.
1.2 Maximum Semester Course Load & Overload: Full-time undergraduate students may enroll in a maximum of eighteen (18) credit hours per standard semester. An academic course overload of up to twenty-one (21) credit hours requires prior written authorization from the Dean of Academic Affairs and a minimum prior semester CGPA of 3.50.
1.3 Transfer Credits & Residency Requirement: A maximum of sixty (60) transfer credits from accredited collegiate institutions may be applied toward an undergraduate degree. Transfer courses require a minimum earned grade of 'C' (2.00 quality points) and do not compute into the institutional CGPA. Degree candidates must complete at least thirty (30) of their final forty-five (45) credit hours in resident study.

SECTION 2: GRADING CRITERIA & ACADEMIC STANDING
2.1 Grading Scale & Quality Points: The university utilizes a 4.00 quality point system: A (4.0), A- (3.7), B+ (3.3), B (3.0), B- (2.7), C+ (2.3), C (2.0), C- (1.7), D (1.0), and F (0.0).
2.2 Dean's Honours List: Undergraduates achieving a semester GPA of 3.75 or higher while completing at least fifteen (15) graded credit hours with no incomplete or failing grades are named to the Dean's Honours List.
2.3 Academic Warning & Probation: A student whose cumulative CGPA falls below 2.00 at the conclusion of any semester is placed on Academic Probation for the subsequent term.
2.4 Academic Suspension: Failing to attain a minimum CGPA of 2.00 after two (2) consecutive semesters on Academic Probation results in mandatory Academic Suspension for a minimum period of one calendar year.

SECTION 3: COURSE REGISTRATION, REPEATS & WITHDRAWALS
3.1 Add/Drop Period: Courses may be added or dropped without academic penalty during the first two (2) weeks of the semester. Dropped courses do not appear on official student transcripts.
3.2 Course Withdrawal: Students may officially withdraw from a course through the end of Week 8 with an assigned transcript notation of 'W'. Withdrawals after Week 8 are strictly prohibited except for verified medical emergencies certified by the University Health Center. A grade of 'W' carries no quality points and does not affect the CGPA.
3.3 Course Repeat Policy: An undergraduate student may repeat any course in which an original grade of 'D' or 'F' was earned, up to a maximum of two (2) repeats per course. The higher grade earned replaces earlier grades in CGPA calculation, but all attempts remain recorded on the permanent academic transcript.

SECTION 4: EXAMINATION PROTOCOLS & ATTENDANCE
4.1 Examination Arrival: Candidates must arrive at the examination hall fifteen (15) minutes prior to scheduled commencement. Candidates arriving later than thirty (30) minutes after commencement are strictly denied entry and awarded a grade of zero ('F').
4.2 Identification Requirement: Presentation of a valid University Student Identification Card is mandatory for hall admission. Candidates without valid identification are denied entry.
4.3 Absence from Examinations: Unexcused absence from any scheduled final examination results in an irrecoverable grade of '0'. Approved medical deferrals certified by the University Medical Director permit sitting for a Make-up Examination in Week 1 of the following term.
4.4 Incomplete Grade Policy: An Incomplete ('I') grade is awarded exclusively to students in good standing who have completed at least 75% of total coursework and experience an unanticipated medical emergency. The Incomplete grade must be cleared within six (6) weeks of the following term, or it automatically lapses into an irrecoverable grade of 'F'.

SECTION 5: GRADE APPEALS & RE-EVALUATION PETITIONS
5.1 Grade Re-evaluation Petitions: A formal written petition for grade re-evaluation must be submitted to the Faculty Dean within ten (10) business days following official semester grade release.
5.2 Administrative Fee: Grade re-evaluation petitions must be accompanied by a non-refundable administrative processing fee of fifty dollars ($50.00 USD). If re-evaluation results in a grade increase, the processing fee is fully refunded to the student account.

SECTION 6: STUDENT CODE OF CONDUCT & RESIDENTIAL RULES
6.1 Academic Integrity: Plagiarism, unauthorized collaboration, or cheating on examinations warrants an immediate grade of 'F' for the course and referral to the Academic Disciplinary Committee.
6.2 Residential Quiet Hours: Mandatory quiet hours in residence halls are enforced from 22:00 to 08:00 Sunday through Thursday, and from 24:00 to 09:00 on Friday and Saturday.
6.3 Overnight Guests: Overnight guests must register at the residential reception desk and are limited to a maximum of two (2) consecutive nights. Unregistered overnight guests incur a disciplinary fine of $50.00 USD.
6.4 Campus Parking & Citations: A semester campus parking permit decal costs $120.00 USD. Unauthorized parking in fire lanes or designated faculty bays carries an immediate $75.00 USD fine and vehicle immobilization or towing.

SECTION 7: SCOPE BOUNDARIES & PROHIBITED REQUESTS
7.1 Non-Academic Refusals: The University Regulations Assistant strictly refuses to process tuition bank wire transfers, alter official academic transcripts, negotiate off-campus apartment leases, handle consular student visa extensions, disclose private faculty salaries, or facilitate commercial transactions."""

    rect = pymupdf.Rect(40, 40, 572, 752)
    page.insert_textbox(rect, content, fontsize=8.5, fontname="helv", lineheight=1.25)
    doc.save(pdf_path)
    doc.close()
    print(f"Generated {pdf_path}")

if __name__ == "__main__":
    os.makedirs("demos/university_regulations", exist_ok=True)
    create_university_regulations_pdf("University_Regulations_Test_Document.pdf")
    create_university_regulations_pdf("demos/university_regulations/University_Regulations_Test_Document.pdf")
    os.makedirs("tests/fixtures", exist_ok=True)
    create_university_regulations_pdf("tests/fixtures/University_Regulations_Test_Document.pdf")
