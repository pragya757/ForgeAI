import os
import json
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.factory.pipeline import ForgeAIFactory
from app.runtime.chat_runner import GenericChatRunner
from app.llm import get_llm_client
from app.tools.registry import registry
from app.schemas.requirements import DocumentItem

def safe_to_dict(obj: Any) -> Dict[str, Any]:
    """Safely convert Pydantic models or dicts to a standardized dictionary."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump()
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    if isinstance(obj, dict):
        return dict(obj)
    return {}

def safe_to_dict_list(items: Any) -> List[Dict[str, Any]]:
    """Safely convert a list of Pydantic models or dicts to a list of dictionaries."""
    if not items:
        return []
    if isinstance(items, list):
        return [safe_to_dict(it) for it in items]
    return [safe_to_dict(items)]

# -------------------------------------------------------------------------------------------------
# 1. Page Configuration & Favicon
# -------------------------------------------------------------------------------------------------
FAVICON_PATH = "assets/favicon.png" if os.path.exists("assets/favicon.png") else "assets/forgeai_icon.png"
PAGE_ICON = FAVICON_PATH if os.path.exists(FAVICON_PATH) else "⚡"

st.set_page_config(
    page_title="ForgeAI — The Agent Factory",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------------------------------------
# 2. Premium AI SaaS Visual Theme (Electric Cyan & Deep Black)
# -------------------------------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #050505;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header Container */
    .brand-header-container {
        display: flex;
        align-items: center;
        gap: 24px;
        padding: 12px 0 24px 0;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 24px;
    }
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        line-height: 1.1;
        margin: 0;
    }
    .brand-title span {
        color: #00D9F5;
        text-shadow: 0 0 20px rgba(0, 217, 245, 0.5);
    }
    .brand-tagline {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 3px;
        color: #00D9F5;
        margin-top: 4px;
        text-transform: uppercase;
    }
    .brand-desc {
        font-size: 0.98rem;
        color: #94A3B8;
        margin-top: 6px;
    }

    /* Sidebar Branding & Accents */
    [data-testid="stSidebar"] {
        background-color: #080C14;
        border-right: 1px solid #1E293B;
    }
    .sidebar-brand-box {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 8px 0 18px 0;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 16px;
    }
    .sidebar-brand-text {
        font-size: 1.35rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.2;
    }
    .sidebar-brand-text span {
        color: #00D9F5;
    }
    .sidebar-tagline {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 2px;
        color: #00D9F5;
        text-transform: uppercase;
    }

    /* Cards & Containers */
    .forge-card {
        background-color: #0B0F19;
        border: 1px solid #1E293B;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .forge-card:hover {
        border-color: rgba(0, 217, 245, 0.4);
        box-shadow: 0 0 16px rgba(0, 217, 245, 0.08);
    }
    .forge-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .forge-card-title span {
        color: #00D9F5;
    }

    /* Badges */
    .badge-cyan {
        background-color: rgba(0, 217, 245, 0.12);
        color: #00D9F5;
        border: 1px solid rgba(0, 217, 245, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-pass {
        background-color: rgba(16, 185, 129, 0.12);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-fail {
        background-color: rgba(239, 68, 68, 0.12);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 3px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }

    /* Streamlit Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1E293B;
        padding-bottom: 4px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.9rem;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #00D9F5;
        background-color: rgba(0, 217, 245, 0.05);
    }
    .stTabs [aria-selected="true"] {
        color: #00D9F5 !important;
        background-color: rgba(0, 217, 245, 0.08) !important;
        border-bottom: 2px solid #00D9F5 !important;
        text-shadow: 0 0 10px rgba(0, 217, 245, 0.4);
    }

    /* Primary Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00D9F5, #008cb0) !important;
        color: #050505 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
        box-shadow: 0 0 15px rgba(0, 217, 245, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 0 25px rgba(0, 217, 245, 0.6) !important;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------------
# 3. Sidebar: Brand Identity, Presets & Architecture Controls
# -------------------------------------------------------------------------------------------------
LOGO_PATH = "assets/forgeai_logo.png"
ICON_PATH = "assets/forgeai_icon.png"

# Sidebar Branding
with st.sidebar:
    if os.path.exists(ICON_PATH):
        col_ico, col_txt = st.columns([1, 3])
        with col_ico:
            st.image(ICON_PATH, width=54)
        with col_txt:
            st.markdown("""
            <div style="margin-top: 2px;">
                <div class="sidebar-brand-text">Forge<span>AI</span></div>
                <div class="sidebar-tagline">THE AGENT FACTORY</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sidebar-brand-box">
            <div>
                <div class="sidebar-brand-text">Forge<span>AI</span></div>
                <div class="sidebar-tagline">THE AGENT FACTORY</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.caption("Autonomous Agent Engineering & Evaluation Engine")
    st.divider()

    st.markdown("### 🎯 Demonstration Presets")
    preset_choice = st.selectbox(
        "Select Target Domain",
        [
            "Demo 1: HR Policy Assistant",
            "Demo 2: Ship-Spares Procurement Assistant",
            "Demo 3: Academic Regulations (Unseen Domain)",
            "Demo 4: Medical Clinic Operations",
            "Custom Agent Build"
        ],
        index=0
    )

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
        "Demo 4: Medical Clinic Operations": {
            "brief": "Create a medical clinic policy assistant that helps staff and patients understand triage appointment scheduling, patient health information privacy rules, medical record release timelines, and telehealth consultation regulations.",
            "docs": "generalization_test/documents",
            "artifacts": "generalization_test/artifacts",
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

    if st.button("📂 Load Pre-Built Artifacts", width="stretch"):
        target_artifacts = active_preset["artifacts"]
        req_file = os.path.join(target_artifacts, "requirements.json")
        if os.path.exists(req_file):
            st.session_state["artifacts_dir"] = target_artifacts
            st.session_state["doc_folder"] = active_preset["docs"]
            st.session_state["last_run"] = None
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
            st.success(f"Artifacts loaded from `{target_artifacts}`")
        else:
            st.error(f"Artifacts not found at `{target_artifacts}`.")

    st.divider()
    st.markdown("### 🏛 Core Architecture (9 Modules)")
    st.markdown("""
    1. **Intake Interviewer** (Max 5 Clarifications)
    2. **Groundability Guard** (Corpus Verification)
    3. **Agent Generator** (Dynamic Config & Guardrails)
    4. **Auto-Eval Generator** ($\\ge 20$ Frozen Cases)
    5. **Hybrid Judge** (Deterministic + Semantic)
    6. **Critic-Optimizer** (Max 3 Iterations, Rollback)
    7. **Honest Quality Reporter** (Markdown + JSON)
    8. **Generic Agent Runtime** (Tool Least-Privilege)
    9. **4 Demonstration Domains** (Zero Code Edits)
    """)

# -------------------------------------------------------------------------------------------------
# 4. Top Main Header (ForgeAI Logo & Tagline)
# -------------------------------------------------------------------------------------------------
if os.path.exists(LOGO_PATH):
    h_col1, h_col2 = st.columns([1.6, 3])
    with h_col1:
        st.image(LOGO_PATH, width=320)
    with h_col2:
        st.markdown("""
        <div style="padding-top: 10px;">
            <div class="brand-tagline">THE AGENT FACTORY</div>
            <div class="brand-desc">Transform documents and natural language briefs into production-grade, evaluated, and self-optimizing AI agents.</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="brand-header-container">
        <div>
            <div class="brand-title">Forge<span>AI</span></div>
            <div class="brand-tagline">THE AGENT FACTORY</div>
            <div class="brand-desc">Transform documents and ideas into intelligent, evaluated AI agents.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------------
# 5. Eight-Stage Main Dashboard Navigation
# -------------------------------------------------------------------------------------------------
tabs = st.tabs([
    "🛠️ 1. Agent Creation",
    "📋 2. Requirements Analysis",
    "🛡️ 3. Groundability Check",
    "⚙️ 4. Agent Generation",
    "🧪 5. Evaluation",
    "🔄 6. Optimization",
    "📊 7. Final Report",
    "💬 8. Agent Playground"
])

# -------------------------------------------------------------------------------------------------
# TAB 1: AGENT CREATION (Brief, Uploads, Clarifications, Factory Trigger)
# -------------------------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("### 🛠️ Step 1: Agent Specification & Autonomous Generation")
    st.markdown("""
    Define the target agent's mission in natural language, upload knowledge documents, and trigger the
    end-to-end autonomous factory.
    """)

    col_build1, col_build2 = st.columns([3, 2])

    with col_build1:
        st.markdown("#### User Brief Submission")
        brief_input = st.text_area(
            "Agent Persona & Mission Brief",
            value=active_preset["brief"],
            height=110,
            help="Describe the persona, intended capabilities, boundaries, tone, and audience."
        )

        st.markdown("#### Knowledge Document Source")
        doc_folder_input = st.text_input(
            "Corpus Directory Path",
            value=active_preset["docs"],
            help="Directory containing PDF, TXT, or CSV knowledge sources."
        )

        uploaded_files = st.file_uploader(
            "Upload files directly (PDF, TXT, CSV)",
            accept_multiple_files=True,
            type=["pdf", "txt", "csv"]
        )
        if uploaded_files:
            if "custom_session_id" not in st.session_state:
                st.session_state["custom_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_dest = f"outputs/runs/{st.session_state['custom_session_id']}/documents"
            upload_artifacts = f"outputs/runs/{st.session_state['custom_session_id']}/artifacts"
            os.makedirs(upload_dest, exist_ok=True)
            for uf in uploaded_files:
                with open(os.path.join(upload_dest, uf.name), "wb") as f:
                    f.write(uf.getbuffer())
            doc_folder_input = upload_dest
            default_artifacts_dir = upload_artifacts
            st.session_state["loaded_demo"] = None
            st.success(f"Ingested {len(uploaded_files)} file(s) into isolated directory `{upload_dest}`")
        else:
            default_artifacts_dir = active_preset["artifacts"]

        output_dir_input = st.text_input(
            "Artifacts Destination Path",
            value=default_artifacts_dir,
            help="Destination folder for requirements, agent definitions, eval sets, and reports."
        )

        if uploaded_files:
            st.info(f"📁 **Active Corpus:** Custom Upload ({len(uploaded_files)} files: {', '.join([uf.name for uf in uploaded_files])})")
        else:
            st.caption(f"📁 **Active Corpus:** Preset ({doc_folder_input})")

    with col_build2:
        st.markdown("#### Clarification Dialogue (Intake)")
        st.caption("Optionally answer up to 5 clarifying questions formulated by ForgeAI.")

        clarification_answers = {}
        if st.button("🔍 Generate Clarifying Questions", width="stretch"):
            if os.path.exists(doc_folder_input):
                with st.spinner("Analyzing brief against knowledge corpus..."):
                    tmp_factory = ForgeAIFactory()
                    st.session_state["clarification_questions"] = tmp_factory.interviewer.generate_clarifying_questions(brief_input, doc_folder_input)
            else:
                st.error(f"Directory not found: '{doc_folder_input}'")

        if "clarification_questions" in st.session_state and st.session_state["clarification_questions"]:
            st.info(f"ForgeAI formulated {len(st.session_state['clarification_questions'])} targeted questions:")
            for idx, q_text in enumerate(st.session_state["clarification_questions"], 1):
                ans = st.text_input(f"Q{idx}: {q_text}", key=f"clarify_{idx}")
                if ans.strip():
                    clarification_answers[q_text] = ans.strip()

        st.markdown("#### Optimization Ceilings")
        iterations_slider = st.slider("Max Optimization Iterations", min_value=1, max_value=3, value=active_preset["iterations"])
        st.caption("ForgeAI strictly caps optimization to <= 3 iterations with regression rollback.")

    st.divider()

    if st.button("🚀 Run Autonomous Agent Factory", type="primary", width="stretch"):
        if not os.path.exists(doc_folder_input):
            st.error(f"Document directory '{doc_folder_input}' does not exist.")
        else:
            with st.spinner("Executing ForgeAI Factory Pipeline (Intake -> Guard -> Generator -> Auto-Eval -> Judge -> Optimizer -> Reporter)..."):
                progress_box = st.empty()
                progress_box.info("Pipeline active. Ingesting documents, extracting requirements, and assessing groundability...")

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
                    st.session_state["loaded_demo"] = None
                    progress_box.success("🎉 Agent built, evaluated, and optimized successfully!")
                    st.balloons()
                except Exception as e:
                    progress_box.error(f"Error during factory execution: {str(e)}")

# -------------------------------------------------------------------------------------------------
# TAB 2: REQUIREMENTS ANALYSIS (Inventory, Extraction, Clarifications)
# -------------------------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("### 📋 Step 2: Extracted Requirements & Document Inventory")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        reqs = safe_to_dict(run_data.get("requirements"))
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Indexed Documents", len(reqs.get("document_inventory", [])))
        col_m2.metric("Must-Answer Topics", len(reqs.get("must_answer_topics", [])))
        col_m3.metric("Must-Refuse Topics", len(reqs.get("must_refuse_topics", [])))

        st.markdown("#### Document Inventory")
        inv_list = reqs.get("document_inventory", [])
        if inv_list:
            inv_rows = []
            for doc_item in inv_list:
                doc = safe_to_dict(doc_item)
                topics_str = ", ".join(doc.get("detected_topics", [])) if doc.get("detected_topics") else "General corpus"
                inv_rows.append({
                    "Filename": doc.get("filename"),
                    "Format": doc.get("format"),
                    "Pages / Records": doc.get("page_count") or doc.get("record_count") or 1,
                    "Detected Topics": topics_str,
                    "Summary": doc.get("description", "")
                })
            st.dataframe(pd.DataFrame(inv_rows), width="stretch")

        st.divider()

        col_req1, col_req2 = st.columns(2)
        with col_req1:
            st.markdown("#### Structured Persona & Scope")
            st.write(f"**Agent Name:** `{reqs.get('agent_name')}`")
            st.write(f"**Purpose:** {reqs.get('purpose')}")
            st.write(f"**Target Audience:** {reqs.get('target_audience')}")
            st.write(f"**Operational Scope:** {reqs.get('scope')}")
            st.write(f"**Tone:** `{reqs.get('tone')}`")

        with col_req2:
            st.markdown("#### Topic Boundaries")
            st.markdown("**In-Scope (Must Answer):**")
            for t in reqs.get("must_answer_topics", []):
                st.write(f"- ✅ {t}")
            st.markdown("**Out-of-Scope (Strict Refusal):**")
            for t in reqs.get("must_refuse_topics", []):
                st.write(f"- ⛔ **REFUSE:** {t}")
    else:
        st.info("Run an agent build in Step 1 or load a pre-built demo from the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 3: GROUNDABILITY CHECK (Corpus Support & Evidence Mapping)
# -------------------------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("### 🛡️ Step 3: Groundability Analysis & Evidence Verification")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        ground = safe_to_dict(run_data.get("groundability"))
        score = ground.get("overall_groundability_score", 0.0)

        g_col1, g_col2, g_col3 = st.columns(3)
        g_col1.metric("Groundability Score", f"{score * 100:.1f}%")
        g_col2.metric("Supported Topics", len(ground.get("supported_topics", [])))
        g_col3.metric("Unsupported Topics", len(ground.get("unsupported_topics", [])))

        st.divider()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Supported Topics (Corpus Evidenced)")
            for s_item in ground.get("supported_topics", []):
                item = safe_to_dict(s_item)
                srcs = ", ".join(item.get("evidence_sources", []))
                conf = item.get("confidence_score", 1.0) * 100
                st.markdown(f"**{item.get('topic')}** `<span class='badge-pass'>{conf:.0f}% confidence</span>`", unsafe_allow_html=True)
                st.write(f"{item.get('coverage_summary')} *(Sources: `{srcs}`)*")

        with col_g2:
            st.markdown("#### Unsupported Topics (Refusal Enforced)")
            for u_item in ground.get("unsupported_topics", []):
                item = safe_to_dict(u_item)
                nat = item.get("absence_nature", "missing_from_corpus")
                st.markdown(f"**{item.get('topic')}** `<span class='badge-fail'>{nat}</span>`", unsafe_allow_html=True)
                st.write(f"Reason: {item.get('reason')}")

        st.divider()
        st.markdown("#### Refusal Policy Directives")
        for rec in ground.get("refusal_recommendations", []):
            st.write(f"- 🛡️ {rec}")
    else:
        st.info("Run an agent build in Step 1 or load a pre-built demo from the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 4: AGENT GENERATION (Config, Prompts & Tool Registry)
# -------------------------------------------------------------------------------------------------
with tabs[3]:
    st.markdown("### ⚙️ Step 4: Generated Declarative Agent Definition")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        agent_def = safe_to_dict(run_data.get("agent_definition"))

        col_cfg1, col_cfg2 = st.columns([1, 1])

        with col_cfg1:
            st.markdown("#### Architecture & Retrieval Parameters")
            params = [
                {"Parameter": "Agent Name", "Value": str(agent_def.get("agent_name"))},
                {"Parameter": "Embedding Model", "Value": str(agent_def.get("embedding_model"))},
                {"Parameter": "Retrieval Method", "Value": str(agent_def.get("retrieval_method"))},
                {"Parameter": "Chunk Size", "Value": f"{agent_def.get('chunk_size')} chars"},
                {"Parameter": "Chunk Overlap", "Value": f"{agent_def.get('chunk_overlap')} chars"},
                {"Parameter": "Top-K", "Value": str(agent_def.get("top_k"))},
                {"Parameter": "Similarity Threshold", "Value": str(agent_def.get("similarity_threshold"))},
                {"Parameter": "Refusal Policy", "Value": str(agent_def.get("refusal_policy"))}
            ]
            st.dataframe(pd.DataFrame(params), width="stretch")

        with col_cfg2:
            st.markdown("#### Tool Registry & Security Allowlisting")
            tools = agent_def.get("tool_selection", [])
            justifications = agent_def.get("tool_justifications", {})
            st.write(f"**Mounted Tools:** `{', '.join(tools) if tools else 'None (Strict RAG)'}`")
            if justifications:
                j_rows = [{"Tool": t, "Justification": justifications.get(t, "Authorized tool.")} for t in tools]
                st.dataframe(pd.DataFrame(j_rows), width="stretch")
            st.caption("🔒 Least-Privilege Security: Unmounted tools are blocked at the registry level via PermissionError.")

        st.divider()
        st.markdown("#### Generated System Prompt")
        st.code(agent_def.get("system_prompt", ""), language="markdown")
    else:
        st.info("Run an agent build in Step 1 or load a pre-built demo from the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 5: EVALUATION (Test Cases & Results)
# -------------------------------------------------------------------------------------------------
with tabs[4]:
    st.markdown("### 🧪 Step 5: Evaluation Dataset & Benchmark Results")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        eval_set = safe_to_dict(run_data.get("eval_set"))
        scorecards = run_data["scorecards"] if isinstance(run_data.get("scorecards"), list) else [run_data.get("scorecards")]
        sc_dicts = [safe_to_dict(sc) for sc in scorecards if sc]
        final_sc = sc_dicts[-1] if sc_dicts else {}

        ev_c1, ev_c2, ev_c3, ev_c4 = st.columns(4)
        ev_c1.metric("Benchmark Cases", len(eval_set.get("cases", [])))
        ev_c2.metric("Pass Rate", f"{final_sc.get('pass_rate', 0)*100:.1f}%")
        ev_c3.metric("Passed Cases", final_sc.get("passed_tests", 0))
        ev_c4.metric("Failed Cases", final_sc.get("failed_tests", 0))

        st.divider()

        st.markdown(f"#### Generated Test Cases ({len(eval_set.get('cases', []))} Cases)")
        cases_data = []
        for case_item in eval_set.get("cases", []):
            c = safe_to_dict(case_item)
            cases_data.append({
                "Test ID": c.get("test_id"),
                "Category": c.get("subcategory") or c.get("test_category"),
                "Action": c.get("expected_action"),
                "Question": c.get("question"),
                "Expected Facts": "; ".join(c.get("expected_facts", []))[:100] + "...",
                "Sources": ", ".join(c.get("expected_sources", []))
            })
        st.dataframe(pd.DataFrame(cases_data), width="stretch")
    else:
        st.info("Run an agent build in Step 1 or load a pre-built demo from the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 6: OPTIMIZATION (Critic-Optimizer Rounds & Scorecards)
# -------------------------------------------------------------------------------------------------
with tabs[5]:
    st.markdown("### 🔄 Step 6: Critic–Optimizer Progression & Targeted Repairs")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        raw_scorecards = run_data.get("scorecards", [])
        scorecards = raw_scorecards if isinstance(raw_scorecards, list) else [raw_scorecards]
        sc_dicts = [safe_to_dict(sc) for sc in scorecards if sc]

        st.markdown("#### Progression History Across Iterations")
        opt_rows = []
        for sc in sc_dicts:
            m = sc.get("metric_breakdown", {})
            opt_rows.append({
                "Iteration": f"Round {sc.get('iteration', 1)}",
                "Pass Rate (%)": f"{sc.get('pass_rate', 0)*100:.1f}%",
                "Passed": sc.get("passed_tests", 0),
                "Failed": sc.get("failed_tests", 0),
                "Grounding (%)": f"{m.get('grounding', 0)*100:.0f}%",
                "Factual (%)": f"{m.get('factual_correctness', 0)*100:.0f}%",
                "Citation (%)": f"{m.get('citation_correctness', 0)*100:.0f}%",
                "Refusal (%)": f"{m.get('refusal_correctness', 0)*100:.0f}%",
                "Contract (%)": f"{m.get('output_contract_compliance', 0)*100:.0f}%",
                "Status": sc.get("status", "COMPLETE")
            })
        st.dataframe(pd.DataFrame(opt_rows), width="stretch")

        st.divider()

        raw_logs = run_data.get("iteration_logs", [])
        iter_logs = safe_to_dict_list(raw_logs)
        if iter_logs:
            st.markdown("#### Critic Targeted Change History")
            for log in iter_logs:
                iter_num = log.get("iteration_number") or log.get("iteration", 1)
                diagnosis = log.get("identified_root_causes") or log.get("root_cause_diagnosis") or "Targeted optimization refinement"
                fail_cats = log.get("failure_categories")
                if isinstance(fail_cats, list):
                    fail_cat_str = ", ".join(str(c) for c in fail_cats) if fail_cats else "general"
                else:
                    fail_cat_str = str(log.get("failure_category", "general"))

                score_before = log.get("previous_score", log.get("score_before", 0.0))
                score_after = log.get("new_score", log.get("score_after", 0.0))
                changes = log.get("changes_applied", [])

                with st.expander(f"Iteration {iter_num}: {diagnosis}"):
                    st.write(f"**Failure Category:** `{fail_cat_str}`")
                    st.write(f"**Score Before:** {score_before * 100:.1f}% ➔ **Score After:** {score_after * 100:.1f}%")
                    if changes:
                        st.json(changes)
                    else:
                        st.info("No configuration modifications required for this round.")
    else:
        st.info("Run an agent build in Step 1 or load a pre-built demo from the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 7: FINAL REPORT (Quality Scorecard, Failure Audit, Downloads)
# -------------------------------------------------------------------------------------------------
with tabs[6]:
    st.markdown("### 📊 Step 7: Final Quality Report & Audit Transparency")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        raw_scorecards = run_data.get("scorecards", [])
        scorecards = raw_scorecards if isinstance(raw_scorecards, list) else [raw_scorecards]
        sc_dicts = [safe_to_dict(sc) for sc in scorecards if sc]
        final_sc = sc_dicts[-1] if sc_dicts else {}
        raw_cases = final_sc.get("case_results", [])
        case_dicts = [safe_to_dict(c) for c in raw_cases]
        failed_cases = [c for c in case_dicts if not c.get("passed")]

        st.markdown("#### Final Quality Metrics")
        m = final_sc.get("metric_breakdown", {})
        f1, f2, f3, f4, f5 = st.columns(5)
        f1.metric("Overall Pass Rate", f"{final_sc.get('pass_rate', 0)*100:.1f}%")
        f2.metric("Grounding", f"{m.get('grounding', 0)*100:.0f}%")
        f3.metric("Factual", f"{m.get('factual_correctness', 0)*100:.0f}%")
        f4.metric("Citation", f"{m.get('citation_correctness', 0)*100:.0f}%")
        f5.metric("Refusal", f"{m.get('refusal_correctness', 0)*100:.0f}%")

        st.divider()

        st.markdown(f"#### Remaining Failed Cases ({len(failed_cases)})")
        if not failed_cases:
            st.success("🎉 All evaluation test cases passed with zero unresolved defects!")
        else:
            st.warning("In accordance with ForgeAI honesty principles, raw responses and judge decisions are preserved below:")
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

                    st.markdown("**Judge Reasoning:**")
                    st.info(fc.get("evidence_reasoning") or fc.get("explanation") or "Criteria threshold not satisfied.")

                    st.markdown("**Raw Agent Response:**")
                    st.code(fc.get("agent_response", ""), language="text")

        st.divider()

        st.markdown("#### Artifact Downloads")
        target_artifacts_dir = st.session_state.get("artifacts_dir", active_preset["artifacts"])
        dl_c1, dl_c2, dl_c3 = st.columns(3)

        final_report_md = os.path.join(target_artifacts_dir, "final_report.md")
        if os.path.exists(final_report_md):
            with open(final_report_md, "r", encoding="utf-8") as f:
                dl_c1.download_button("📄 Markdown Report (final_report.md)", f.read(), "final_report.md", "text/markdown")

        quality_json = os.path.join(target_artifacts_dir, "quality_report.json")
        if os.path.exists(quality_json):
            with open(quality_json, "r", encoding="utf-8") as f:
                dl_c2.download_button("📊 Quality Report (quality_report.json)", f.read(), "quality_report.json", "application/json")

        agent_def_file = os.path.join(target_artifacts_dir, "agent_definition.json")
        if os.path.exists(agent_def_file):
            with open(agent_def_file, "r", encoding="utf-8") as f:
                dl_c3.download_button("🤖 Agent Definition (agent_definition.json)", f.read(), "agent_definition.json", "application/json")
    else:
        st.info("Run an agent build in Step 1 or load a pre-built demo from the sidebar.")

# -------------------------------------------------------------------------------------------------
# TAB 8: AGENT PLAYGROUND (Interactive Chat Runner)
# -------------------------------------------------------------------------------------------------
with tabs[7]:
    st.markdown("### 💬 Step 8: Interactive Agent Playground")
    current_artifacts_dir = st.session_state.get("artifacts_dir", active_preset["artifacts"])
    current_doc_dir = st.session_state.get("doc_folder", active_preset["docs"])
    default_def_path = os.path.join(current_artifacts_dir, "agent_definition.json")
    default_doc_path = current_doc_dir

    cp_col1, cp_col2 = st.columns([3, 1])
    with cp_col1:
        agent_def_path = st.text_input("Active Agent Definition Path", value=default_def_path)
        agent_doc_path = st.text_input("Active Corpus Directory", value=default_doc_path)
    with cp_col2:
        st.write("")
        st.write("")
        if st.button("🔄 Reset Chat History", width="stretch"):
            st.session_state["live_chat_history"] = []
            st.success("Chat history cleared.")

    if os.path.exists(agent_def_path):
        if "live_chat_history" not in st.session_state:
            st.session_state["live_chat_history"] = []

        for msg in st.session_state["live_chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citations"):
                    st.caption(f"📚 Citations: {', '.join(msg['citations'])}")
                if msg.get("tool_calls"):
                    st.info(f"🛠️ Executed Tools: {[tc['tool'] for tc in msg['tool_calls']]}")

        user_input = st.chat_input("Ask the generated agent a question...")
        if user_input:
            st.session_state["live_chat_history"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Agent retrieving knowledge chunks and synthesizing grounded answer..."):
                runner = GenericChatRunner(definition_path=agent_def_path, doc_folder=agent_doc_path)
                chat_resp = runner.ask(user_input)

            with st.chat_message("assistant"):
                st.markdown(chat_resp.answer)
                if chat_resp.citations:
                    st.caption(f"📚 Citations: {', '.join(chat_resp.citations)}")
                if chat_resp.tool_calls:
                    st.info(f"🛠️ Authorized Tools Executed: {[tc['tool'] for tc in chat_resp.tool_calls]}")
                if chat_resp.refused:
                    st.warning("🛡️ Refusal Guardrail: Query deemed out-of-scope or ungrounded.")

            st.session_state["live_chat_history"].append({
                "role": "assistant",
                "content": chat_resp.answer,
                "citations": chat_resp.citations,
                "tool_calls": chat_resp.tool_calls
            })
    else:
        st.warning(f"Agent definition file not found at '{agent_def_path}'. Run an agent build first.")
