import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime

from app.factory.pipeline import ForgeAIFactory
from app.runtime.chat_runner import GenericChatRunner
from app.llm import get_llm_client
from app.tools.registry import registry
from app.schemas.requirements import DocumentItem

# 1. Page Configuration & Custom Theme
st.set_page_config(
    page_title="ForgeAI - Autonomous Agent Factory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .status-badge-pass {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-badge-fail {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar: Preset Demonstration Selector & Architecture Guide
st.sidebar.title("⚡ ForgeAI Control Center")
st.sidebar.caption("OceanAI Campus Recruitment Demonstration")

preset_choice = st.sidebar.selectbox(
    "Choose Demonstration Preset",
    [
        "Demo 1: HR Policy Assistant",
        "Demo 2: Ship-Spares Procurement Assistant",
        "Demo 3: Academic Regulations (Unseen Domain)",
        "Custom Agent Build"
    ],
    index=0
)

# Preset Brief and Path Mappings
PRESETS = {
    "Demo 1: HR Policy Assistant": {
        "brief": "Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents.",
        "docs": "demos/hr_assistant/documents",
        "artifacts": "demos/hr_assistant/artifacts",
        "iterations": 2
    },
    "Demo 2: Ship-Spares Procurement Assistant": {
        "brief": "Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents.",
        "docs": "demos/procurement_assistant/documents",
        "artifacts": "demos/procurement_assistant/artifacts",
        "iterations": 2
    },
    "Demo 3: Academic Regulations (Unseen Domain)": {
        "brief": "Create a University Academic Regulations Assistant that answers student and faculty questions regarding graduation requirements, grading scales, examination guidelines, academic probation, and the student code of conduct using university policy manuals.",
        "docs": "unseen_test/documents",
        "artifacts": "unseen_test/artifacts",
        "iterations": 2
    },
    "Custom Agent Build": {
        "brief": "Create an enterprise customer support assistant that answers technical product queries, onboarding steps, and return policies.",
        "docs": "outputs/custom_agent/documents",
        "artifacts": "outputs/custom_agent/artifacts",
        "iterations": 3
    }
}

active_preset = PRESETS[preset_choice]

# Sidebar Quick Action: Load Pre-Built Committed Artifacts
if st.sidebar.button("📂 Load Pre-Built Artifacts for Selected Demo"):
    target_artifacts = active_preset["artifacts"]
    req_file = os.path.join(target_artifacts, "requirements.json")
    if os.path.exists(req_file):
        st.session_state["artifacts_dir"] = target_artifacts
        st.session_state["doc_folder"] = active_preset["docs"]
        # Load artifacts into session state
        with open(os.path.join(target_artifacts, "requirements.json")) as f:
            req_data = json.load(f)
        with open(os.path.join(target_artifacts, "groundability_report.json")) as f:
            ground_data = json.load(f)
        with open(os.path.join(target_artifacts, "agent_definition.json")) as f:
            agent_data = json.load(f)
        with open(os.path.join(target_artifacts, "eval_set.json")) as f:
            eval_data = json.load(f)
        with open(os.path.join(target_artifacts, "scorecards.json")) as f:
            sc_data = json.load(f)
        with open(os.path.join(target_artifacts, "iteration_logs.json")) as f:
            iter_data = json.load(f)
        report_md_file = os.path.join(target_artifacts, "final_report.md")
        report_md = open(report_md_file).read() if os.path.exists(report_md_file) else ""

        st.session_state["loaded_demo"] = {
            "requirements": req_data,
            "groundability": ground_data,
            "agent_definition": agent_data,
            "eval_set": eval_data,
            "scorecards": sc_data,
            "iteration_logs": iter_data,
            "report_md": report_md
        }
        st.sidebar.success(f"Loaded artifacts from `{target_artifacts}`")
    else:
        st.sidebar.error(f"Artifacts not found at `{target_artifacts}`. Please run factory first.")

st.sidebar.divider()
st.sidebar.markdown("### 🏛 Core Architecture (9 Modules)")
st.sidebar.markdown("""
1. **Intake Interviewer** (Max 5 Clarifications)
2. **Groundability Guard** (Evidence Verification)
3. **Agent Generator** (Dynamic Config & Refusals)
4. **Auto-Eval Generator** ($\\ge 20$ Test Cases)
5. **Hybrid Judge** (Deterministic + Semantic)
6. **Critic-Optimizer Loop** (Targeted, Max 3 Iterations)
7. **Honest Reporter** (Markdown + JSON)
8. **Generic Chat Runner** (Tool Isolation & Safety)
9. **Two Demonstrations** (HR & Procurement)
""")

# Top Header
st.markdown('<div class="main-header">⚡ ForgeAI: The Agent That Builds Agents</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous Agent Factory for Enterprise & Operations GenAI (OceanAI Recruitment)</div>', unsafe_allow_html=True)

# 3. Main Navigation Tabs
tabs = st.tabs([
    "🏭 1. Agent Factory",
    "🛡 2. Requirements & Groundability",
    "🧪 3. Evaluation & Scorecards",
    "🔍 4. Failure Deep Dive",
    "💬 5. Generic Chat Runner",
    "📦 6. Downloads & System Status"
])

# -------------------------------------------------------------------------------------------------
# TAB 1: AGENT FACTORY (Brief Submission, Document Upload, Clarifications, Pipeline Trigger)
# -------------------------------------------------------------------------------------------------
with tabs[0]:
    st.subheader("1. Project Overview & Agent Factory Pipeline")
    st.markdown(r"""
    **ForgeAI** is an autonomous AI agent factory. Given a user's natural language brief and document collection,
    it inspects documentation, verifies groundability, produces complete agent definitions, generates $\ge 20$ evaluation test cases,
    judges performance, and performs targeted optimization loops ($\le 3$ iterations).
    """)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### Step 1: Natural Language Brief Submission")
        brief_input = st.text_area(
            "Agent Description",
            value=active_preset["brief"],
            height=110,
            help="Describe the intended persona, purpose, target audience, and operational guidelines."
        )

        st.markdown("#### Step 2: Document Source Specification")
        doc_folder_input = st.text_input(
            "Document Directory Path",
            value=active_preset["docs"],
            help="Path to folder containing PDF, TXT, or CSV files."
        )

        # File Upload Option for Custom Files
        uploaded_files = st.file_uploader(
            "Or upload documents directly (PDF, TXT, CSV)",
            accept_multiple_files=True,
            type=["pdf", "txt", "csv"]
        )
        if uploaded_files:
            upload_dest = "outputs/custom_agent/documents"
            os.makedirs(upload_dest, exist_ok=True)
            for uf in uploaded_files:
                with open(os.path.join(upload_dest, uf.name), "wb") as f:
                    f.write(uf.getbuffer())
            doc_folder_input = upload_dest
            st.success(f"Uploaded {len(uploaded_files)} files to `{upload_dest}`")

        output_dir_input = st.text_input(
            "Artifacts Directory",
            value=active_preset["artifacts"],
            help="Destination folder for generated definitions, scorecards, and reports."
        )

    with col2:
        st.markdown("#### Step 3: Clarification Dialogue (Intake)")
        st.caption("Ask up to 5 clarifying questions before generation or use unattended defaults.")

        clarification_answers = {}
        if st.button("🔍 Generate Clarifying Questions (Max 5)", use_container_width=True):
            if os.path.exists(doc_folder_input):
                with st.spinner("Analyzing brief against document collection..."):
                    tmp_factory = ForgeAIFactory()
                    st.session_state["clarification_questions"] = tmp_factory.interviewer.generate_clarifying_questions(brief_input, doc_folder_input)
            else:
                st.error(f"Document directory not found: '{doc_folder_input}'")

        if "clarification_questions" in st.session_state and st.session_state["clarification_questions"]:
            st.info(f"ForgeAI formulated {len(st.session_state['clarification_questions'])} clarifying questions:")
            for idx, q_text in enumerate(st.session_state["clarification_questions"], 1):
                ans = st.text_input(f"Q{idx}: {q_text}", key=f"clarify_{idx}")
                if ans.strip():
                    clarification_answers[q_text] = ans.strip()

        st.markdown("#### Step 4: Optimization Guardrails")
        iterations_slider = st.slider("Max Optimization Iterations", min_value=1, max_value=3, value=active_preset["iterations"])
        st.info("Ceiling constraint: ForgeAI strictly enforces a maximum of 3 iterations with automatic rollback on regressions.")

    st.divider()

    # Trigger Factory Run
    if st.button("🚀 Run Autonomous Agent Factory", type="primary", use_container_width=True):
        if not os.path.exists(doc_folder_input):
            st.error(f"Document folder not found: '{doc_folder_input}'")
        else:
            with st.spinner("Executing ForgeAI Pipeline (Intake -> Guard -> Generator -> Auto-Eval -> Judge -> Optimizer -> Reporter)..."):
                progress_box = st.empty()
                progress_box.info("Pipeline initialized. Ingesting documents and evaluating requirements...")

                try:
                    factory = ForgeAIFactory(max_iterations=iterations_slider)
                    results = factory.build_agent(
                        brief=brief_input,
                        doc_folder=doc_folder_input,
                        output_dir=output_dir_input,
                        clarification_answers=clarification_answers if clarification_answers else None,
                        unattended=not bool(clarification_answers)
                    )
                    st.session_state["last_run"] = results
                    st.session_state["artifacts_dir"] = output_dir_input
                    st.session_state["doc_folder"] = doc_folder_input
                    st.session_state["loaded_demo"] = None  # Clear static view in favor of live run

                    progress_box.success("🎉 Agent built, tested, and optimized successfully!")
                    st.balloons()
                except Exception as e:
                    progress_box.error(f"Error executing factory pipeline: {str(e)}")

# -------------------------------------------------------------------------------------------------
# TAB 2: REQUIREMENTS & GROUNDABILITY (Inventory, Requirements, Groundability, Config, Tools)
# -------------------------------------------------------------------------------------------------
with tabs[1]:
    st.subheader("2. Requirements, Groundability & Generated Configuration")

    # Determine data source: live run or loaded preset
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        reqs = run_data["requirements"] if isinstance(run_data["requirements"], dict) else run_data["requirements"].model_dump()
        ground = run_data["groundability"] if isinstance(run_data["groundability"], dict) else run_data["groundability"].model_dump()
        agent_def = run_data["agent_definition"] if isinstance(run_data["agent_definition"], dict) else run_data["agent_definition"].model_dump()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Agent Name", agent_def.get("agent_name", "AI Assistant"))
        c2.metric("Groundability Score", f"{ground.get('overall_groundability_score', 0) * 100:.1f}%")
        c3.metric("Indexed Files", len(reqs.get("document_inventory", [])))
        c4.metric("Mounted Tools", len(agent_def.get("tool_selection", [])))

        st.divider()

        # Document Inventory Table
        st.markdown("### Document Inventory")
        inv_list = reqs.get("document_inventory", [])
        if inv_list:
            inv_rows = []
            for doc in inv_list:
                topics_str = ", ".join(doc.get("detected_topics", [])) if doc.get("detected_topics") else "Corpus document"
                inv_rows.append({
                    "Filename": doc.get("filename"),
                    "Format": doc.get("format"),
                    "Pages / Records": doc.get("page_count") or doc.get("record_count") or 1,
                    "Detected Topics": topics_str,
                    "Description": doc.get("description", "")
                })
            st.dataframe(pd.DataFrame(inv_rows), use_container_width=True)

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Structured Requirements")
            st.write(f"**Purpose:** {reqs.get('purpose')}")
            st.write(f"**Target Audience:** {reqs.get('target_audience')}")
            st.write(f"**Operational Scope:** {reqs.get('scope')}")
            st.write(f"**Conversational Tone:** {reqs.get('tone')}")

            st.markdown("#### Must-Answer Topics")
            for mat in reqs.get("must_answer_topics", []):
                st.write(f"- ✅ {mat}")

            st.markdown("#### Must-Refuse Topics")
            for mrt in reqs.get("must_refuse_topics", []):
                st.write(f"- 🚫 **REFUSE:** {mrt}")

        with col_right:
            st.markdown("### Groundability Guard Analysis")
            st.markdown("#### Supported Topics (Corpus Evidenced)")
            for st_item in ground.get("supported_topics", []):
                srcs = ", ".join(st_item.get("evidence_sources", []))
                st.write(f"- **{st_item.get('topic')}**: {st_item.get('coverage_summary')} *(Sources: `{srcs}`)*")

            st.markdown("#### Unsupported Topics (Strict Refusal Enforced)")
            for ut_item in ground.get("unsupported_topics", []):
                nature = ut_item.get("absence_nature", "unsupported")
                st.write(f"- ⛔ **{ut_item.get('topic')}** `[{nature}]`: {ut_item.get('reason')}")

        st.divider()

        # Generated Agent Configuration & Tool Selection
        st.markdown("### Generated Agent Definition & Tool Security")
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("#### Retrieval & Architecture Configuration")
            cfg_table = [
                {"Parameter": "Embedding Model", "Value": agent_def.get("embedding_model")},
                {"Parameter": "Retrieval Method", "Value": agent_def.get("retrieval_method")},
                {"Parameter": "Chunk Size", "Value": f"{agent_def.get('chunk_size')} chars"},
                {"Parameter": "Chunk Overlap", "Value": f"{agent_def.get('chunk_overlap')} chars"},
                {"Parameter": "Top-K", "Value": agent_def.get("top_k")},
                {"Parameter": "Similarity Threshold", "Value": agent_def.get("similarity_threshold")},
                {"Parameter": "Refusal Policy", "Value": agent_def.get("refusal_policy")}
            ]
            st.dataframe(pd.DataFrame(cfg_table), use_container_width=True)

        with col_c2:
            st.markdown("#### Selected Tools & Justifications")
            tools = agent_def.get("tool_selection", [])
            justifications = agent_def.get("tool_justifications", {})
            st.write(f"**Mounted Tools:** `{', '.join(tools) if tools else 'None (Strict RAG Mode)'}`")
            if justifications:
                just_rows = [{"Tool": t, "Justification": justifications.get(t, "Authorized tool.")} for t in tools]
                st.dataframe(pd.DataFrame(just_rows), use_container_width=True)
            st.info("🔒 Tool Isolation: Tools absent from definition are blocked at the registry level via PermissionError.")

    else:
        st.info("Run an agent build in Tab 1 or click 'Load Pre-Built Artifacts' in the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 3: EVALUATION & SCORECARDS (Test Cases, Iteration Scorecards, Before-After Comparison)
# -------------------------------------------------------------------------------------------------
with tabs[2]:
    st.subheader("3. Autonomous Evaluation, Scorecards & Optimization History")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        eval_set = run_data["eval_set"] if isinstance(run_data["eval_set"], dict) else run_data["eval_set"].model_dump()
        scorecards = run_data["scorecards"] if isinstance(run_data["scorecards"], list) else [run_data["scorecards"]]
        # Normalize scorecards to dicts if needed
        sc_dicts = [sc if isinstance(sc, dict) else sc.model_dump() for sc in scorecards]

        initial_sc = sc_dicts[0]
        final_sc = sc_dicts[-1]

        # Top Metric Banner
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Evaluation Cases", eval_set.get("total_cases", len(eval_set.get("cases", []))))
        m2.metric("Baseline Pass Rate", f"{initial_sc.get('pass_rate', 0) * 100:.1f}%")
        final_rate = final_sc.get("pass_rate", 0) * 100
        delta = final_rate - (initial_sc.get('pass_rate', 0) * 100)
        m3.metric("Final Pass Rate", f"{final_rate:.1f}%", delta=f"{delta:+.1f}%")
        m4.metric("Optimization Iterations", len(sc_dicts))

        st.divider()

        # Progression Table Across Iterations
        st.markdown("### Optimization Progression History")
        prog_rows = []
        for sc in sc_dicts:
            m = sc.get("metric_breakdown", {})
            prog_rows.append({
                "Iteration": f"Iter {sc.get('iteration')}",
                "Total Tests": sc.get("total_tests"),
                "Passed": sc.get("passed_tests"),
                "Failed": sc.get("failed_tests"),
                "Pass Rate (%)": f"{sc.get('pass_rate', 0)*100:.1f}%",
                "Grounding (%)": f"{m.get('grounding', 0)*100:.0f}%",
                "Factual (%)": f"{m.get('factual_correctness', 0)*100:.0f}%",
                "Citation (%)": f"{m.get('citation_correctness', 0)*100:.0f}%",
                "Refusal (%)": f"{m.get('refusal_correctness', 0)*100:.0f}%",
                "Contract (%)": f"{m.get('output_contract_compliance', 0)*100:.0f}%",
                "Status": sc.get("status")
            })
        st.dataframe(pd.DataFrame(prog_rows), use_container_width=True)

        st.divider()

        # Evaluation Test Cases Table
        st.markdown(f"### Evaluation Test Cases ({len(eval_set.get('cases', []))} Cases)")
        case_rows = []
        for case in eval_set.get("cases", []):
            case_rows.append({
                "Test ID": case.get("test_id"),
                "Category": case.get("subcategory") or case.get("test_category"),
                "Expected Action": case.get("expected_action"),
                "Question": case.get("question"),
                "Expected Answer / Facts": "; ".join(case.get("expected_facts", []))[:120] + "...",
                "Source Document": ", ".join(case.get("expected_sources", []))
            })
        st.dataframe(pd.DataFrame(case_rows), use_container_width=True)

    else:
        st.info("Run an agent build in Tab 1 or click 'Load Pre-Built Artifacts' in the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 4: FAILURE DEEP DIVE (Auditability, Raw Responses, Judge Reasoning)
# -------------------------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("4. Transparent Audit: Remaining Failures & Raw Responses")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        scorecards = run_data["scorecards"] if isinstance(run_data["scorecards"], list) else [run_data["scorecards"]]
        sc_dicts = [sc if isinstance(sc, dict) else sc.model_dump() for sc in scorecards]
        final_sc = sc_dicts[-1]
        failed_cases = [c for c in final_sc.get("case_results", []) if not c.get("passed")]

        if not failed_cases:
            st.success("🎉 All evaluation test cases passed successfully! Zero unresolved defects detected.")
        else:
            st.warning(f"⚠️ A total of **{len(failed_cases)}** test cases remain unresolved. In accordance with ForgeAI honesty principles, raw responses and judge decisions are preserved below for auditing:")

            for fc in failed_cases:
                with st.expander(f"❌ `{fc.get('test_id')}`: {fc.get('question')}"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Grounding", f"{fc.get('grounding_score', 0):.2f}")
                    c2.metric("Factual", f"{fc.get('factual_correctness', 0):.2f}")
                    c3.metric("Citation", f"{fc.get('citation_correctness', 0):.2f}")
                    c4.metric("Refusal", f"{fc.get('refusal_correctness', 0):.2f}")

                    st.markdown("**Failure Reasons:**")
                    for r in fc.get("failure_reasons", []):
                        st.write(f"- 🔴 {r}")

                    st.markdown("**Judge Evidence Reasoning:**")
                    st.info(fc.get("evidence_reasoning") or fc.get("explanation") or "Criteria threshold not satisfied.")

                    st.markdown("**Raw Agent Response:**")
                    st.code(fc.get("agent_response", ""), language="text")

    else:
        st.info("Run an agent build in Tab 1 or click 'Load Pre-Built Artifacts' in the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 5: GENERIC CHAT RUNNER (Live Interactive Testing)
# -------------------------------------------------------------------------------------------------
with tabs[4]:
    st.subheader("5. Live Generic Agent Chat Runner")
    default_def_path = active_preset["artifacts"] + "/agent_definition.json"
    default_doc_path = active_preset["docs"]

    col_cp1, col_cp2 = st.columns([2, 1])
    with col_cp1:
        agent_def_path = st.text_input("Agent Definition Path", value=default_def_path)
        agent_doc_path = st.text_input("Corpus Directory Path", value=default_doc_path)
    with col_cp2:
        if st.button("🔄 Clear Chat History"):
            st.session_state["live_chat_history"] = []
            st.success("Chat history reset.")

    if os.path.exists(agent_def_path):
        if "live_chat_history" not in st.session_state:
            st.session_state["live_chat_history"] = []

        # Display history
        for msg in st.session_state["live_chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citations"):
                    st.caption(f"Citations: {', '.join(msg['citations'])}")
                if msg.get("tool_calls"):
                    st.info(f"Tool Executed: {[tc['tool'] for tc in msg['tool_calls']]}")

        user_input = st.chat_input("Ask a question to the generated agent...")
        if user_input:
            st.session_state["live_chat_history"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Agent retrieving evidence and synthesizing grounded response..."):
                runner = GenericChatRunner(definition_path=agent_def_path, doc_folder=agent_doc_path)
                chat_resp = runner.ask(user_input)

            with st.chat_message("assistant"):
                st.markdown(chat_resp.answer)
                if chat_resp.citations:
                    st.caption(f"📚 Citations: {', '.join(chat_resp.citations)}")
                if chat_resp.tool_calls:
                    st.info(f"🛠 Authorized Tools Executed: {[tc['tool'] for tc in chat_resp.tool_calls]}")
                if chat_resp.refused:
                    st.warning("🛡 Refusal Policy: Query determined out-of-scope or unevidenced.")

            st.session_state["live_chat_history"].append({
                "role": "assistant",
                "content": chat_resp.answer,
                "citations": chat_resp.citations,
                "tool_calls": chat_resp.tool_calls
            })
    else:
        st.warning(f"Agent definition file not found at '{agent_def_path}'. Run a factory build first.")

# -------------------------------------------------------------------------------------------------
# TAB 6: DOWNLOADS & SYSTEM DIAGNOSTICS (Artifact Export & LLM Diagnostics)
# -------------------------------------------------------------------------------------------------
with tabs[5]:
    st.subheader("6. Artifact Downloads & System Diagnostics")

    target_artifacts_dir = st.session_state.get("artifacts_dir", active_preset["artifacts"])

    st.markdown("### One-Click Artifact Downloads")
    d1, d2, d3 = st.columns(3)

    final_report_md = os.path.join(target_artifacts_dir, "final_report.md")
    if os.path.exists(final_report_md):
        with open(final_report_md, "r", encoding="utf-8") as f:
            d1.download_button("📄 Download Markdown Report (final_report.md)", f.read(), "final_report.md", "text/markdown")

    quality_json = os.path.join(target_artifacts_dir, "quality_report.json")
    if os.path.exists(quality_json):
        with open(quality_json, "r", encoding="utf-8") as f:
            d2.download_button("📊 Download Quality Report (quality_report.json)", f.read(), "quality_report.json", "application/json")

    agent_def_file = os.path.join(target_artifacts_dir, "agent_definition.json")
    if os.path.exists(agent_def_file):
        with open(agent_def_file, "r", encoding="utf-8") as f:
            d3.download_button("🤖 Download Agent Definition (agent_definition.json)", f.read(), "agent_definition.json", "application/json")

    d4, d5, d6 = st.columns(3)
    eval_set_file = os.path.join(target_artifacts_dir, "eval_set.json")
    if os.path.exists(eval_set_file):
        with open(eval_set_file, "r", encoding="utf-8") as f:
            d4.download_button("🧪 Download Evaluation Set (eval_set.json)", f.read(), "eval_set.json", "application/json")

    scorecards_file = os.path.join(target_artifacts_dir, "scorecards.json")
    if os.path.exists(scorecards_file):
        with open(scorecards_file, "r", encoding="utf-8") as f:
            d5.download_button("📈 Download Scorecards (scorecards.json)", f.read(), "scorecards.json", "application/json")

    iteration_logs_file = os.path.join(target_artifacts_dir, "iteration_logs.json")
    if os.path.exists(iteration_logs_file):
        with open(iteration_logs_file, "r", encoding="utf-8") as f:
            d6.download_button("🔄 Download Iteration Logs (iteration_logs.json)", f.read(), "iteration_logs.json", "application/json")

    st.divider()

    # System Diagnostics & LLM Backend Status
    st.markdown("### System & Health Diagnostics")
    diag_col1, diag_col2 = st.columns(2)

    with diag_col1:
        st.markdown("#### LLM Backend")
        llm = get_llm_client()
        avail, msg = llm.is_available()
        st.write(f"**Selected Provider:** `{os.getenv('LLM_PROVIDER', 'ollama')}`")
        st.write(f"**Configured Model:** `{os.getenv('FORGEAI_MODEL', 'llama3.1:8b')}`")
        st.write(f"**Status:** {'🟢 Online' if avail else '🟡 Fallback / Mock Mode Active'}")
        st.code(msg)

    with diag_col2:
        st.markdown("#### Registered Tools")
        for tool_name in registry.list_tools():
            t = registry.get_tool(tool_name)
            st.write(f"- **`{tool_name}`**: {t.description}")
