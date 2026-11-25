import pytest
from app.factory.judge import HybridJudge
from app.schemas.evaluation import EvalCase
from app.runtime.chat_runner import ChatResponse
from app.llm.mock_client import MockLLMClient

@pytest.fixture
def judge():
    return HybridJudge(llm_client=MockLLMClient())

def test_scenario_1_correct_citation(judge):
    """Scenario 1: Ground truth and agent answer align, citing correct doc/page."""
    case = EvalCase(
        test_id="SCENARIO_1",
        question="What is the minimum attendance requirement?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="Students must maintain at least 75% attendance in all enrolled courses.",
        expected_facts=["minimum 75% attendance", "enrolled courses"],
        expected_sources=["academic_handbook.pdf"],
        ground_truth_evidence="Section 4.1: Minimum attendance requirement is 75% in all courses.",
        evaluation_criteria="Verify attendance percentage is 75% and cite academic_handbook.pdf."
    )
    resp = ChatResponse(
        answer="According to university policy, students must maintain at least 75% attendance in all enrolled courses [Source: academic_handbook.pdf].",
        sources=["academic_handbook.pdf"],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="Students must maintain at least 75% attendance in all enrolled courses.")
    assert result.passed is True
    assert result.outcome_classification == "correct_with_evidence"
    assert result.factual_correctness >= 0.8
    assert result.citation_correctness == 1.0
    assert result.refusal_correctness == 1.0

def test_scenario_2_missing_citation(judge):
    """Scenario 2: Correct answer text, but citation is omitted."""
    case = EvalCase(
        test_id="SCENARIO_2",
        question="What is the minimum attendance requirement?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="Students must maintain at least 75% attendance in all enrolled courses.",
        expected_facts=["minimum 75% attendance"],
        expected_sources=["academic_handbook.pdf"],
        ground_truth_evidence="Section 4.1: Minimum attendance requirement is 75%.",
        evaluation_criteria="Must cite academic_handbook.pdf."
    )
    resp = ChatResponse(
        answer="Students must maintain at least 75% attendance in all enrolled courses.",
        sources=[],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="Students must maintain at least 75% attendance in all enrolled courses.")
    assert result.passed is False
    assert result.citation_correctness == 0.0
    assert any("citation_defect" in f for f in result.failure_reasons)

def test_scenario_3_wrong_numbers(judge):
    """Scenario 3: Numerical values in answer contradict ground truth numbers."""
    case = EvalCase(
        test_id="SCENARIO_3",
        question="What is the passing grade percentage?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The minimum passing score is 50 percent.",
        expected_facts=["minimum passing score is 50 percent"],
        expected_sources=["grading_policy.pdf"],
        ground_truth_evidence="Grading scale: 50% is required to pass.",
        evaluation_criteria="Passing score must be 50%."
    )
    resp = ChatResponse(
        answer="The minimum passing score is 25 percent for all undergraduate programs [Source: grading_policy.pdf].",
        sources=["grading_policy.pdf"],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="The minimum passing score is 50 percent.")
    assert result.passed is False
    assert result.factual_correctness < 0.8 or any("hallucination" in f for f in result.failure_reasons)

def test_scenario_4_partial_answer(judge):
    """Scenario 4: Answer contains only one of two mandatory criteria."""
    case = EvalCase(
        test_id="SCENARIO_4",
        question="What are the criteria for graduation honors?",
        test_category="answerable",
        subcategory="multi_hop",
        expected_action="answer",
        expected_answer="Graduation honors require a cumulative GPA of 3.8 and zero disciplinary reprimands.",
        expected_facts=[
            "cumulative GPA of 3.8",
            "zero disciplinary reprimands"
        ],
        expected_sources=["regulations.pdf"],
        ground_truth_evidence="Honors requirement: GPA 3.8 and zero disciplinary actions.",
        evaluation_criteria="Both GPA and clean disciplinary record must be stated."
    )
    resp = ChatResponse(
        answer="Graduation honors require students to achieve a cumulative GPA of 3.8 across all completed semesters [Source: regulations.pdf].",
        sources=["regulations.pdf"],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="Graduation honors require a cumulative GPA of 3.8 and zero disciplinary reprimands.")
    assert result.passed is False
    assert result.outcome_classification == "partially_correct"
    assert any("hallucination" in f or "omitted" in f for f in result.failure_reasons)

def test_scenario_5_hallucination(judge):
    """Scenario 5: Answer invents facts not present in reference."""
    case = EvalCase(
        test_id="SCENARIO_5",
        question="What financial stipends do master students receive?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The handbook does not provide monetary stipends for standard master students.",
        expected_facts=["does not provide monetary stipends"],
        expected_sources=["handbook.pdf"],
        ground_truth_evidence="Master programs are self-funded; no general stipend is provided.",
        evaluation_criteria="Must state that no monetary stipends are provided."
    )
    resp = ChatResponse(
        answer="All master students receive a guaranteed monthly stipend of $1,500 and free housing [Source: handbook.pdf].",
        sources=["handbook.pdf"],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="Standard master students are self-funded through tuition.")
    assert result.passed is False
    assert result.factual_correctness < 0.8
    assert any("hallucination" in f for f in result.failure_reasons)

def test_scenario_6_correct_refusal(judge):
    """Scenario 6: Out-of-scope query is correctly refused by agent."""
    case = EvalCase(
        test_id="SCENARIO_6",
        question="How do I change the oil filter on a Boeing 777 aircraft engine?",
        test_category="out_of_scope",
        subcategory="out_of_scope",
        expected_action="refuse",
        expected_answer="Refuse: This question is outside academic regulations.",
        expected_facts=[],
        expected_sources=[],
        ground_truth_evidence="Aircraft maintenance is not part of academic regulations.",
        evaluation_criteria="Agent must decline answering."
    )
    resp = ChatResponse(
        answer="I cannot answer this question as aircraft maintenance is outside the scope of my verified academic documentation.",
        sources=[],
        refused=True
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="")
    assert result.passed is True
    assert result.outcome_classification == "correct_refusal"
    assert result.refusal_correctness == 1.0

def test_scenario_7_incorrect_refusal(judge):
    """Scenario 7: Agent erroneously refuses an in-scope question."""
    case = EvalCase(
        test_id="SCENARIO_7",
        question="What is the deadline for course withdrawal?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The course withdrawal deadline is the end of the fourth week of classes.",
        expected_facts=["fourth week of classes"],
        expected_sources=["academic_calendar.pdf"],
        ground_truth_evidence="Withdrawals are allowed up to the fourth week.",
        evaluation_criteria="Answer must state fourth week deadline."
    )
    resp = ChatResponse(
        answer="I cannot answer this request because it is outside my verified policies.",
        sources=[],
        refused=True
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="Course withdrawal is permitted until the fourth week of classes.")
    assert result.passed is False
    assert result.outcome_classification == "incorrect_refusal"
    assert result.refusal_correctness == 0.0
    assert any("wrong_refusal" in f for f in result.failure_reasons)

def test_scenario_8_paraphrased_answer(judge):
    """Scenario 8: Correct semantic answer expressed with different lexical phrasing."""
    case = EvalCase(
        test_id="SCENARIO_8",
        question="When must graduate theses be submitted?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The final graduate thesis submission deadline is May 15.",
        expected_facts=["final graduate thesis submission deadline is may 15"],
        expected_sources=["thesis_guide.pdf"],
        ground_truth_evidence="Thesis submission deadline: May 15.",
        evaluation_criteria="Must state May 15 deadline."
    )
    resp = ChatResponse(
        answer="For all postgraduate candidates, the final date to lodge your completed dissertation is scheduled on May 15th [Source: thesis_guide.pdf].",
        sources=["thesis_guide.pdf"],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="The final graduate thesis submission deadline is May 15.")
    assert result.passed is True
    assert result.outcome_classification == "correct_with_evidence"
    assert result.citation_correctness == 1.0

def test_scenario_9_plausible_irrelevant_info(judge):
    """Scenario 9: Answer offers plausible details from the domain without answering the specific query."""
    case = EvalCase(
        test_id="SCENARIO_9",
        question="What is the fee for late registration?",
        test_category="answerable",
        subcategory="direct_factual",
        expected_action="answer",
        expected_answer="The late registration fee is $100 per week.",
        expected_facts=["late registration fee is $100 per week"],
        expected_sources=["fees.pdf"],
        ground_truth_evidence="Late registration fee is $100 per week of delay.",
        evaluation_criteria="Must indicate the $100 late registration fee."
    )
    resp = ChatResponse(
        answer="Students can register for courses online using the student portal during standard office hours Monday through Friday [Source: fees.pdf].",
        sources=["fees.pdf"],
        refused=False
    )
    result = judge.evaluate_case(case, resp, retrieved_chunks_text="The late registration fee is $100 per week. General registration is available via student portal.")
    assert result.passed is False
    assert result.factual_correctness < 0.8
    assert any("hallucination" in f for f in result.failure_reasons)
