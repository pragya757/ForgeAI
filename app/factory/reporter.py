import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.schemas.requirements import Requirements
from app.schemas.groundability import GroundabilityReport
from app.schemas.agent_definition import AgentDefinition
from app.schemas.scorecard import IterationScorecard, IterationLog

class HonestReportGenerator:
    """Module 7: Honest Report Generator - Synthesizes transparent, evidence-based quality reports."""

    def generate_report(
        self,
        brief: str,
        requirements: Requirements,
        groundability: GroundabilityReport,
        final_agent: AgentDefinition,
        scorecards: List[IterationScorecard],
        iteration_logs: List[IterationLog],
        output_dir: str
    ) -> str:
        """Construct comprehensive Markdown report and serialize JSON artifacts."""
        os.makedirs(output_dir, exist_ok=True)

        initial_scorecard = scorecards[0] if scorecards else None
        final_scorecard = scorecards[-1] if scorecards else None

        initial_pass_rate = (initial_scorecard.pass_rate * 100) if initial_scorecard else 0.0
        final_pass_rate = (final_scorecard.pass_rate * 100) if final_scorecard else 0.0

        failed_cases = [r for r in final_scorecard.case_results if not r.passed] if final_scorecard else []

        status_str = "SUCCESS (PASSED)" if final_pass_rate >= 85.0 else ("PARTIAL SUCCESS" if final_pass_rate >= 60.0 else "UNSATISFACTORY")

        # Build Markdown content
        lines = [
            f"# ForgeAI Honest Agent Quality & Verification Report",
            f"",
            f"**Generated On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Agent Name:** {final_agent.agent_name}  ",
            f"**Evaluation Status:** `{status_str}`  ",
            f"**Final Pass Rate:** **{final_pass_rate:.1f}%** (Initial: {initial_pass_rate:.1f}%)  ",
            f"**Optimization Iterations Executed:** {len(scorecards)} (Max Limit: 3)  ",
            f"",
            f"---",
            f"",
            f"## 1. Executive Brief & Requirements Analysis",
            f"",
            f"### Original Natural Language Brief",
            f"> {brief.strip()}",
            f"",
            f"### Agent Scope & Purpose",
            f"- **Purpose:** {requirements.purpose}",
            f"- **Target Audience:** {requirements.target_audience}",
            f"- **Operational Tone:** {requirements.tone}",
            f"- **Document Inventory:** {len(requirements.document_inventory)} files indexed",
        ]

        for doc in requirements.document_inventory:
            lines.append(f"  - `{doc.filename}` ({doc.format}, pages/chunks: {doc.page_count or 'N/A'}): {doc.description}")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 2. Groundability Guard Assessment",
            f"",
            f"- **Overall Groundability Index:** `{groundability.overall_groundability_score * 100:.1f}%`",
            f"",
            f"### Supported Topics (Verifiable in Corpus)",
        ])
        for t in groundability.supported_topics:
            lines.append(f"- **{t.topic}**: {t.coverage_summary} *(Sources: {', '.join(t.evidence_sources)})*")

        if groundability.partially_supported_topics:
            lines.append(f"\n### Partially Supported Topics")
            for pt in groundability.partially_supported_topics:
                lines.append(f"- **{pt.topic}**: Missing: {pt.missing_aspects} *(Sources: {', '.join(pt.evidence_sources)})*")

        lines.append(f"\n### Unsupported Topics (Strict Refusal Enforced)")
        for ut in groundability.unsupported_topics:
            lines.append(f"- **{ut.topic}**: {ut.reason}")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 3. Tool Selection & Authorized Capabilities",
            f"",
            f"- **Selected Tools:** `{', '.join(final_agent.tool_selection) if final_agent.tool_selection else 'None (Strict RAG only)'}`",
            f"- **Tool Isolation Policy:** Only explicitly authorized tools are mounted to this agent runtime. All extraneous or unrequested tools are strictly prohibited.",
            f"",
            f"---",
            f"",
            f"## 4. Retrieval & Architecture Configuration",
            f"",
            f"| Parameter | Value | Justification |",
            f"|---|---|---|",
            f"| Embedding Model | `{final_agent.embedding_model}` | Dense semantic vector representations |",
            f"| Retrieval Method | `{final_agent.retrieval_method}` | High-performance inner-product cosine similarity |",
            f"| Chunk Size | `{final_agent.chunk_size}` chars | Aligned with document paragraph length |",
            f"| Chunk Overlap | `{final_agent.chunk_overlap}` chars | Boundary context retention across splits |",
            f"| Top-K Chunks | `{final_agent.top_k}` | Optimized balance between context recall and noise |",
            f"| Similarity Threshold | `{final_agent.similarity_threshold}` | Strict cutoff preventing hallucinations |",
            f"",
            f"---",
            f"",
            f"## 5. Evaluation Scorecards & Metric Breakdown",
            f"",
            f"| Iteration | Total Tests | Passed | Failed | Pass Rate | Grounding | Factual | Citation | Refusal | Relevance | Contract |",
            f"|---|---|---|---|---|---|---|---|---|---|---|",
        ])

        for sc in scorecards:
            m = sc.metric_breakdown
            lines.append(
                f"| Iteration {sc.iteration} | {sc.total_tests} | {sc.passed_tests} | {sc.failed_tests} | "
                f"**{sc.pass_rate * 100:.1f}%** | {m.get('grounding', 0)*100:.0f}% | {m.get('factual_correctness', 0)*100:.0f}% | "
                f"{m.get('citation_correctness', 0)*100:.0f}% | {m.get('refusal_correctness', 0)*100:.0f}% | "
                f"{m.get('relevance', 0)*100:.0f}% | {m.get('output_contract_compliance', 0)*100:.0f}% |"
            )

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 6. Critic-Optimizer Iteration History",
            f"",
        ])

        if not iteration_logs:
            lines.append("No optimization iterations were required; agent achieved target passing thresholds on initial baseline.")
        else:
            for log in iteration_logs:
                lines.extend([
                    f"### Iteration {log.iteration_number} Diagnostics",
                    f"- **Score Before:** `{log.previous_score * 100:.1f}%` -> **Score After:** `{log.new_score * 100:.1f}%` ({log.improvement_or_regression})",
                    f"- **Failed Test IDs:** `{', '.join(log.failed_test_ids)}`",
                    f"- **Failure Modes Identified:** `{', '.join(log.failure_categories)}`",
                    f"- **Root Cause Analysis:** {log.identified_root_causes}",
                    f"- **Targeted Modifications Applied:**",
                ])
                for ch in log.changes_applied:
                    lines.append(f"  - Changed `{ch.get('target')}` from `{ch.get('previous_value')}` to `{ch.get('new_value')}`: *{ch.get('reason')}*")
                lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## 7. Remaining Failed Cases & Honest Limitations",
            f"",
        ])

        if not failed_cases:
            lines.append("All evaluation test cases passed successfully.")
        else:
            lines.append(f"A total of **{len(failed_cases)}** test cases remain unresolved:")
            for fc in failed_cases:
                lines.extend([
                    f"#### Test Case: `{fc.test_id}`",
                    f"- **Question:** {fc.question}",
                    f"- **Failure Reasons:** {', '.join(fc.failure_reasons)}",
                    f"- **Agent Response:** `{fc.agent_response[:250]}...`",
                    f"- **Metric Scores:** Factual: {fc.factual_correctness}, Refusal: {fc.refusal_correctness}, Citation: {fc.citation_correctness}",
                    f""
                ])

        lines.extend([
            f"### Documented Limitations",
            f"1. **Document-Corpus Completeness:** The agent answers strictly from provided text. Inquiries on topics not in the corpus are systematically refused.",
            f"2. **OCR / Layout Dependency:** Documents with scanned images or unextractable text elements rely on textual OCR pre-processing.",
            f"3. **Refusal Conservative Policy:** To avoid false claims, questions that contain ambiguous overlap with refusal rules are directed to human authorities.",
            f"",
            f"---",
            f"*Generated autonomously by ForgeAI - Autonomous AI Agent Factory*"
        ])

        report_markdown = "\n".join(lines)

        # Save Markdown report
        report_path = os.path.join(output_dir, "final_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)

        # Save scorecards.json
        scorecards_path = os.path.join(output_dir, "scorecards.json")
        with open(scorecards_path, "w", encoding="utf-8") as f:
            scorecards_data = [sc.model_dump() for sc in scorecards]
            json.dump(scorecards_data, f, indent=2)

        # Save iteration_logs.json
        iter_path = os.path.join(output_dir, "iteration_logs.json")
        with open(iter_path, "w", encoding="utf-8") as f:
            iter_data = [it.model_dump() for it in iteration_logs]
            json.dump(iter_data, f, indent=2)

        return report_markdown
