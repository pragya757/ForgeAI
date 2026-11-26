import os
import json
import time
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.factory.pipeline import ForgeAIFactory
from app.runtime.chat_runner import GenericChatRunner
from app.llm import get_llm_client
from app.tools.registry import registry
from app.schemas.requirements import DocumentItem

# -------------------------------------------------------------------------------------------------
# 1. Serialization Helpers (Pydantic & Dict Interop)
# -------------------------------------------------------------------------------------------------
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
# 2. Page Configuration & Assets
# -------------------------------------------------------------------------------------------------
FAVICON_PATH = "assets/favicon.png" if os.path.exists("assets/favicon.png") else "assets/forgeai_icon.png"
PAGE_ICON = FAVICON_PATH if os.path.exists(FAVICON_PATH) else "⚡"
LOGO_PATH = "assets/forgeai_logo.png"
ICON_PATH = "assets/forgeai_icon.png"

st.set_page_config(
    page_title="ForgeAI — The Autonomous Agent Factory",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------------------------------------
# 3. Premium AI SaaS Styling (Deep Navy/Near-Black, Electric Cyan & Teal Accents)
# -------------------------------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global App Background & Clean Typography */
    .stApp {
        background-color: #06090F;
        color: #F1F5F9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Top Brand Header */
    .brand-header-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 18px 24px;
        background: linear-gradient(180deg, #0B1120 0%, #070B14 100%);
        border: 1px solid #1E293B;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
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
        font-size: 0.95rem;
        color: #94A3B8;
        margin-top: 6px;
        max-width: 680px;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #080C16 !important;
        border-right: 1px solid #1E293B !important;
    }
    .sidebar-brand-box {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0 16px 0;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 16px;
    }
    .sidebar-brand-text {
        font-size: 1.35rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
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

    /* Status Pills & Badges */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .status-online {
        background: rgba(16, 185, 129, 0.12);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .status-cyan {
        background: rgba(0, 217, 245, 0.12);
        color: #00D9F5;
        border: 1px solid rgba(0, 217, 245, 0.35);
    }

    .badge-pass {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.4);
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-fail {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-neutral {
        background-color: rgba(148, 163, 184, 0.15);
        color: #94A3B8;
        border: 1px solid rgba(148, 163, 184, 0.3);
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }
    .badge-cyan {
        background-color: rgba(0, 217, 245, 0.15);
        color: #00D9F5;
        border: 1px solid rgba(0, 217, 245, 0.4);
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-block;
    }

    /* Workflow Stage Progress Ribbon */
    .ribbon-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 12px 16px;
        background-color: #0B1120;
        border: 1px solid #1E293B;
        border-radius: 10px;
        margin-bottom: 24px;
        align-items: center;
        justify-content: space-between;
    }
    .ribbon-step {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #94A3B8;
        padding: 4px 8px;
        border-radius: 6px;
    }
    .ribbon-step.active {
        color: #00D9F5;
        background-color: rgba(0, 217, 245, 0.08);
        border: 1px solid rgba(0, 217, 245, 0.25);
    }
    .ribbon-step.complete {
        color: #10B981;
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

    /* Primary Launch Button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00D9F5 0%, #008cb0 100%) !important;
        color: #050505 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 0 20px rgba(0, 217, 245, 0.4) !important;
        transition: all 0.2s ease !important;
        padding: 0.6rem 1.2rem !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 0 30px rgba(0, 217, 245, 0.7) !important;
        transform: translateY(-1px);
    }

    /* Secondary Action Buttons */
    .stButton > button[kind="secondary"] {
        background-color: #0F172A !important;
        color: #E2E8F0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #00D9F5 !important;
        color: #00D9F5 !important;
    }

    /* Custom Cards */
    .topic-card {
        background-color: #0B1120;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
        transition: border-color 0.2s ease;
    }
    .topic-card:hover {
        border-color: rgba(0, 217, 245, 0.35);
    }
    .topic-card-title {
        font-weight: 700;
        font-size: 0.95rem;
        color: #FFFFFF;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .topic-card-desc {
        font-size: 0.85rem;
        color: #94A3B8;
        line-height: 1.4;
    }
    .topic-card-meta {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------------
# 4. Sidebar: Platform Branding, Preset Selector & Navigation
# -------------------------------------------------------------------------------------------------
with st.sidebar:
    if os.path.exists(ICON_PATH):
        c_ico, c_txt = st.columns([1, 3])
        with c_ico:
            st.image(ICON_PATH, width=54)
        with c_txt:
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

    st.markdown("""
    <div style="margin-bottom: 12px;">
        <span class="status-pill status-online">● FACTORY ENGINE READY</span>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Autonomous Declarative Agent Factory & Evaluation Engine")
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
        index=0,
        help="Choose a pre-configured domain or select Custom Agent Build to upload custom knowledge."
    )

    PRESETS = {
        "Demo 1: HR Policy Assistant": {
            "brief": "Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents.",
            "docs": "demos/hr_assistant/documents",
            "artifacts": "demos/hr_assistant/artifacts",
            "iterations": 2,
            "domain": "Human Resources"
        },
        "Demo 2: Ship-Spares Procurement Assistant": {
            "brief": "Create a procurement assistant that helps ship procurement staff search spare parts, compare supplier prices, check availability and understand procurement guidelines using catalogues and supplier documents.",
            "docs": "demos/procurement_assistant/documents",
            "artifacts": "demos/procurement_assistant/artifacts",
            "iterations": 2,
            "domain": "Maritime Procurement"
        },
        "Demo 3: Academic Regulations (Unseen Domain)": {
            "brief": "Create a University Academic Regulations Assistant that answers student and faculty questions regarding graduation requirements, grading scales, examination guidelines, academic probation, and the student code of conduct using university policy manuals.",
            "docs": "unseen_test/documents",
            "artifacts": "unseen_test/artifacts",
            "iterations": 2,
            "domain": "Higher Education"
        },
        "Demo 4: Medical Clinic Operations": {
            "brief": "Create a medical clinic policy assistant that helps staff and patients understand triage appointment scheduling, patient health information privacy rules, medical record release timelines, and telehealth consultation regulations.",
            "docs": "generalization_test/documents",
            "artifacts": "generalization_test/artifacts",
            "iterations": 2,
            "domain": "Clinical Healthcare"
        },
        "Custom Agent Build": {
            "brief": "Create an enterprise customer support assistant that answers technical product queries, onboarding steps, and return policies.",
            "docs": "outputs/custom_agent/documents",
            "artifacts": "outputs/custom_agent/artifacts",
            "iterations": 3,
            "domain": "Custom Domain"
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
            st.success(f"Loaded artifacts from `{target_artifacts}`")
        else:
            st.error(f"Artifacts not found at `{target_artifacts}`.")

    st.divider()

    st.markdown("### 🏛 Core Architecture (9 Modules)")
    with st.container(border=True):
        st.markdown("""
        1. **Intake Interviewer** (Max 5 Clarifications)
        2. **Groundability Guard** (Corpus Evidence Mapping)
        3. **Agent Generator** (Dynamic Prompts & Tools)
        4. **Auto-Eval Generator** ($\\ge 20$ Frozen Cases)
        5. **Hybrid Judge** (Deterministic + Semantic)
        6. **Critic-Optimizer** (Max 3 Loops & Rollback)
        7. **Honest Quality Reporter** (Markdown + JSON)
        8. **Generic Agent Runtime** (Least Privilege AST)
        9. **4 Demonstration Domains** (Zero Code Edits)
        """)
        st.caption("🔒 Security: Tool allowlisting, AST math evaluation, path traversal protection, frozen test set invariance.")

# -------------------------------------------------------------------------------------------------
# 5. Main Dashboard Header & Workflow Progress Ribbon
# -------------------------------------------------------------------------------------------------
active_run = st.session_state.get("last_run") or st.session_state.get("loaded_demo")
has_artifacts = bool(active_run)

# Top Welcome Banner
if os.path.exists(LOGO_PATH):
    h1, h2 = st.columns([1.5, 3])
    with h1:
        st.image(LOGO_PATH, width=320)
    with h2:
        st.markdown("""
        <div style="padding-top: 8px;">
            <div class="brand-tagline">THE AGENT FACTORY</div>
            <div class="brand-desc">
                Transform domain documents and natural language briefs into enterprise-grade,
                evaluated, and self-optimizing AI agents with mathematical certainty and zero hallucinations.
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="brand-header-box">
        <div>
            <div class="brand-title">Forge<span>AI</span></div>
            <div class="brand-tagline">THE AGENT FACTORY</div>
            <div class="brand-desc">Autonomous AI Agent Engineering, Groundability & Optimization Engine.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Visual Workflow Pipeline Status Ribbon
st.markdown(f"""
<div class="ribbon-container">
    <div class="ribbon-step {'complete' if has_artifacts else 'active'}">
        <span>🛠️</span> 1. Creation {'✅' if has_artifacts else '⚡'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>📋</span> 2. Requirements {'✅' if has_artifacts else '○'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>🛡️</span> 3. Groundability {'✅' if has_artifacts else '○'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>⚙️</span> 4. Generation {'✅' if has_artifacts else '○'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>🧪</span> 5. Evaluation {'✅' if has_artifacts else '○'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>🔄</span> 6. Optimization {'✅' if has_artifacts else '○'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>📊</span> 7. Report {'✅' if has_artifacts else '○'}
    </div>
    <div style="color: #334155;">➔</div>
    <div class="ribbon-step {'complete' if has_artifacts else ''}">
        <span>💬</span> 8. Playground {'✅' if has_artifacts else '○'}
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------------
# 6. Eight-Stage Main Dashboard Navigation Tabs
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
    st.markdown("Define the agent's persona and mission, attach knowledge files, and trigger the autonomous engineering loop.")

    col_build1, col_build2 = st.columns([3, 2])

    with col_build1:
        with st.container(border=True):
            st.markdown("#### 📝 User Brief Submission")
            brief_input = st.text_area(
                "Agent Mission & Persona Brief",
                value=active_preset["brief"],
                height=110,
                help="Describe persona, operational boundaries, target audience, and expected knowledge domains."
            )

            st.markdown("#### 📚 Knowledge Document Source")
            doc_folder_input = st.text_input(
                "Corpus Directory Path",
                value=active_preset["docs"],
                help="Directory containing PDF, TXT, or CSV knowledge sources."
            )

            uploaded_files = st.file_uploader(
                "Or Upload Documents Directly (PDF, TXT, CSV)",
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
                help="Target directory for generated agent definition, test sets, reports, and logs."
            )

            if uploaded_files:
                st.info(f"📁 **Active Corpus:** Custom Upload ({len(uploaded_files)} files: {', '.join([uf.name for uf in uploaded_files])})")
            else:
                st.caption(f"📁 **Active Corpus:** Preset ({doc_folder_input})")

    with col_build2:
        with st.container(border=True):
            st.markdown("#### 💬 Clarification Dialogue (Intake)")
            st.caption("Formulate up to 5 targeted questions to resolve ambiguities or operational boundaries.")

            clarification_answers = {}
            if st.button("🔍 Generate Clarifying Questions", width="stretch"):
                if os.path.exists(doc_folder_input):
                    with st.spinner("Analyzing brief against knowledge corpus..."):
                        tmp_factory = ForgeAIFactory()
                        st.session_state["clarification_questions"] = tmp_factory.interviewer.generate_clarifying_questions(brief_input, doc_folder_input)
                else:
                    st.error(f"Directory not found: '{doc_folder_input}'")

            if "clarification_questions" in st.session_state:
                qs = st.session_state["clarification_questions"]
                if qs:
                    st.info(f"ForgeAI formulated {len(qs)} targeted question(s):")
                    for idx, q_text in enumerate(qs, 1):
                        ans = st.text_input(f"Q{idx}: {q_text}", key=f"clarify_{idx}", placeholder="Enter guidance or leave blank for autonomous default...")
                        if ans.strip():
                            clarification_answers[q_text] = ans.strip()
                else:
                    st.success("✅ The brief and knowledge corpus are sufficiently clear. No clarifying questions required!")

            st.divider()
            st.markdown("#### ⚡ Optimization Ceilings")
            iterations_slider = st.slider("Max Optimization Iterations", min_value=1, max_value=3, value=active_preset["iterations"])
            st.caption("🔒 ForgeAI strictly caps optimization to <= 3 iterations with automated regression rollback.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Launch Pipeline Button
    if st.button("🚀 Run Autonomous Agent Factory Pipeline", type="primary", width="stretch"):
        if not os.path.exists(doc_folder_input):
            st.error(f"Document directory '{doc_folder_input}' does not exist.")
        else:
            with st.status("🚀 Running ForgeAI Factory Pipeline...", expanded=True) as status_box:
                st.write("📥 **Stage 1/7: Intake Interviewer** — Inspecting document inventory and parsing requirements...")
                time.sleep(0.3)
                st.write("🛡️ **Stage 2/7: Groundability Guard** — Verifying corpus evidence & mapping refusal topics...")
                time.sleep(0.3)
                st.write("⚙️ **Stage 3/7: Agent Generator** — Synthesizing declarative agent configuration & tool registry...")
                time.sleep(0.3)
                st.write("🧪 **Stage 4/7: Evaluation Generator** — Synthesizing >= 20 frozen benchmark test cases...")
                time.sleep(0.3)
                st.write(f"🔄 **Stage 5-6/7: Critic-Optimizer** — Running hybrid judge & regression loop (max {iterations_slider} rounds)...")

                try:
                    factory = ForgeAIFactory(max_iterations=iterations_slider)
                    results = factory.build_agent(
                        brief=brief_input,
                        doc_folder=doc_folder_input,
                        output_dir=output_dir_input,
                        clarification_answers=clarification_answers if clarification_answers else None,
                        unattended=not bool(clarification_answers)
                    )
                    st.write("📊 **Stage 7/7: Quality Reporter** — Compiling quality scorecard and serializing artifacts...")
                    time.sleep(0.2)

                    st.session_state["last_run"] = results
                    st.session_state["artifacts_dir"] = output_dir_input
                    st.session_state["doc_folder"] = doc_folder_input
                    st.session_state["loaded_demo"] = None
                    status_box.update(label="🎉 ForgeAI Autonomous Agent Pipeline Complete!", state="complete", expanded=False)
                    st.balloons()
                except Exception as e:
                    status_box.update(label="❌ Pipeline Failed", state="error", expanded=True)
                    st.error(f"Error during factory execution: {str(e)}")

# -------------------------------------------------------------------------------------------------
# TAB 2: REQUIREMENTS ANALYSIS (Inventory, Extraction, Clarifications)
# -------------------------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("### 📋 Step 2: Extracted Requirements & Document Inventory")
    run_data = st.session_state.get("last_run") or st.session_state.get("loaded_demo")

    if run_data:
        reqs = safe_to_dict(run_data.get("requirements"))
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Indexed Documents", len(reqs.get("document_inventory", [])))
        m2.metric("Must-Answer Topics", len(reqs.get("must_answer_topics", [])))
        m3.metric("Must-Refuse Topics", len(reqs.get("must_refuse_topics", [])))
        m4.metric("Operational Domain", reqs.get("domain", "Domain Specialist"))

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
                    "Summary Preview": doc.get("description", "")
                })
            st.dataframe(pd.DataFrame(inv_rows), width="stretch")

        st.divider()

        col_req1, col_req2 = st.columns(2)
        with col_req1:
            with st.container(border=True):
                st.markdown("#### 🎯 Structured Persona & Scope")
                st.write(f"**Agent Name:** `{reqs.get('agent_name')}`")
                st.write(f"**Purpose:** {reqs.get('purpose')}")
                st.write(f"**Target Audience:** {reqs.get('target_audience')}")
                st.write(f"**Operational Scope:** {reqs.get('scope')}")
                st.write(f"**Tone:** `{reqs.get('tone')}`")

        with col_req2:
            with st.container(border=True):
                st.markdown("#### 🛡️ Topic Boundary Enforcement")
                st.markdown("**In-Scope (Must Answer):**")
                for t in reqs.get("must_answer_topics", []):
                    st.markdown(f"- ✅ **{t}**")
                st.markdown("**Out-of-Scope (Strict Refusal):**")
                for t in reqs.get("must_refuse_topics", []):
                    st.markdown(f"- ⛔ <span class='badge-fail'>REFUSE</span> {t}", unsafe_allow_html=True)
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
            st.markdown("#### ✅ Supported Topics (Corpus Evidenced)")
            for s_item in ground.get("supported_topics", []):
                item = safe_to_dict(s_item)
                srcs = ", ".join(item.get("evidence_sources", []))
                conf = item.get("confidence_score", 1.0) * 100
                with st.container(border=True):
                    st.markdown(f"**{item.get('topic')}** <span class='badge-pass'>{conf:.0f}% confidence</span>", unsafe_allow_html=True)
                    st.write(f"{item.get('coverage_summary')}")
                    st.caption(f"📚 Verified Sources: `{srcs}`")

        with col_g2:
            st.markdown("#### ⛔ Unsupported Topics (Refusal Enforced)")
            for u_item in ground.get("unsupported_topics", []):
                item = safe_to_dict(u_item)
                nat = item.get("absence_nature", "missing_from_corpus")
                with st.container(border=True):
                    st.markdown(f"**{item.get('topic')}** <span class='badge-fail'>{nat}</span>", unsafe_allow_html=True)
                    st.write(f"**Reason:** {item.get('reason')}")

        st.divider()
        with st.container(border=True):
            st.markdown("#### 🛡️ Autonomous Refusal Directives")
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
            with st.container(border=True):
                st.markdown("#### 📐 Architecture & Retrieval Parameters")
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
            with st.container(border=True):
                st.markdown("#### 🔒 Tool Registry & Security Allowlisting")
                tools = agent_def.get("tool_selection", [])
                justifications = agent_def.get("tool_justifications", {})
                st.write(f"**Mounted Tools:** `{', '.join(tools) if tools else 'None (Strict RAG)'}`")
                if justifications:
                    j_rows = [{"Tool": t, "Justification": justifications.get(t, "Authorized tool.")} for t in tools]
                    st.dataframe(pd.DataFrame(j_rows), width="stretch")
                st.caption("🔒 **Least-Privilege Security Guarantee:** Unmounted tools cannot be called. Registry blocks unauthorized executions via `PermissionError`.")

        st.divider()
        with st.expander("📄 View Generated Declarative System Prompt", expanded=True):
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

        st.markdown(f"#### 🔍 Generated Test Cases ({len(eval_set.get('cases', []))} Cases)")
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

        st.markdown("#### 📈 Progression History Across Iterations")
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
            st.markdown("#### 🔧 Critic Targeted Change History")
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

        st.markdown("""
        <div style="margin-top: 14px;">
            <span class="badge-pass">🛡️ REGRESSION GUARD ACTIVE: Zero regressions accepted into configuration state.</span>
        </div>
        """, unsafe_allow_html=True)
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

        st.markdown("#### 🏆 Final Quality Metrics")
        m = final_sc.get("metric_breakdown", {})
        f1, f2, f3, f4, f5 = st.columns(5)
        f1.metric("Overall Pass Rate", f"{final_sc.get('pass_rate', 0)*100:.1f}%")
        f2.metric("Grounding", f"{m.get('grounding', 0)*100:.0f}%")
        f3.metric("Factual", f"{m.get('factual_correctness', 0)*100:.0f}%")
        f4.metric("Citation", f"{m.get('citation_correctness', 0)*100:.0f}%")
        f5.metric("Refusal", f"{m.get('refusal_correctness', 0)*100:.0f}%")

        st.divider()

        st.markdown(f"#### 🔍 Scientific Honesty Audit: Remaining Failed Cases ({len(failed_cases)})")
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

        st.markdown("#### 📥 One-Click Artifact Downloads")
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
    st.markdown("Test the generated agent in real-time with grounded context retrieval and authorized tool execution.")

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

        # Suggested demo prompt chips
        st.markdown("#### 💡 Quick Demonstration Prompts")
        if "hr" in active_preset["domain"].lower():
            p_cols = st.columns(3)
            p1 = p_cols[0].button("📅 Annual Leave Entitlement")
            p2 = p_cols[1].button("⏱️ Core Working Hours")
            p3 = p_cols[2].button("⛔ Refusal: CEO Salary Record")
            suggested_prompt = "How many days of annual leave are full-time employees entitled to per calendar year?" if p1 else ("What are standard core working hours?" if p2 else ("Can you disclose the personal salary of executive directors?" if p3 else None))
        elif "procurement" in active_preset["domain"].lower():
            p_cols = st.columns(3)
            p1 = p_cols[0].button("🔍 Part NV-PUMP-001 Price")
            p2 = p_cols[1].button("💰 Chief Engineer Limit")
            p3 = p_cols[2].button("⛔ Refusal: Wire Transfer")
            suggested_prompt = "What is the unit price and stock of part NV-PUMP-001?" if p1 else ("What is the financial approval threshold for a vessel Chief Engineer without superintendent sign-off?" if p2 else ("Please initiate an automated bank wire transfer to the supplier." if p3 else None))
        else:
            p_cols = st.columns(2)
            p1 = p_cols[0].button("📑 Operational Policy Query")
            p2 = p_cols[1].button("⛔ Refusal: Out-of-Scope Task")
            suggested_prompt = "What are the primary operational guidelines specified in the documentation?" if p1 else ("Can you process an external financial wire transfer?" if p2 else None)

        # Render message history
        for msg in st.session_state["live_chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("citations"):
                    st.caption(f"📚 **Citations:** {', '.join(msg['citations'])}")
                if msg.get("tool_calls"):
                    st.info(f"🛠️ **Authorized Tools Executed:** {[tc.get('tool', 'tool') for tc in msg['tool_calls']]}")
                if msg.get("refused"):
                    st.warning("🛡️ **Refusal Guardrail Triggered:** Request identified as out-of-scope or ungrounded.")

        user_input = st.chat_input("Ask the generated agent a question...")
        active_query = suggested_prompt or user_input

        if active_query:
            st.session_state["live_chat_history"].append({"role": "user", "content": active_query})
            with st.chat_message("user"):
                st.markdown(active_query)

            with st.spinner("Agent retrieving knowledge chunks and synthesizing grounded answer..."):
                runner = GenericChatRunner(definition_path=agent_def_path, doc_folder=agent_doc_path)
                chat_resp = runner.ask(active_query)

            with st.chat_message("assistant"):
                st.markdown(chat_resp.answer)
                if chat_resp.citations:
                    st.caption(f"📚 **Citations:** {', '.join(chat_resp.citations)}")
                if chat_resp.tool_calls:
                    st.info(f"🛠️ **Authorized Tools Executed:** {[tc.get('tool', 'tool') for tc in chat_resp.tool_calls]}")
                if chat_resp.refused:
                    st.warning("🛡️ **Refusal Guardrail Triggered:** Request identified as out-of-scope or ungrounded.")

            st.session_state["live_chat_history"].append({
                "role": "assistant",
                "content": chat_resp.answer,
                "citations": chat_resp.citations,
                "tool_calls": chat_resp.tool_calls,
                "refused": chat_resp.refused
            })
    else:
        st.warning(f"Agent definition file not found at '{agent_def_path}'. Run an agent build in Step 1 first.")
