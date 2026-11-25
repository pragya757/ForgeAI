import os
import json
import streamlit as st
import pandas as pd
from app.factory.pipeline import ForgeAIFactory
from app.runtime.chat_runner import GenericChatRunner
from app.llm import get_llm_client
from app.tools.registry import registry

st.set_page_config(page_title="ForgeAI - Autonomous Agent Factory", page_icon="⚡", layout="wide")

st.title("⚡ ForgeAI: The Agent That Builds Agents")
st.markdown("*Autonomous AI Agent Factory: Designs, Evaluates, Diagnoses, and Delivers Domain AI Agents.*")

tabs = st.tabs(["🏭 Agent Factory", "📊 Evaluation & Scorecards", "💬 Live Agent Chat", "🛠 System Status"])

# TAB 1: FACTORY SETUP & EXECUTION
with tabs[0]:
    st.header("Create a New Agent")
    col1, col2 = st.columns([2, 1])

    with col1:
        brief_input = st.text_area(
            "Natural Language Agent Brief",
            value="Create an HR assistant that answers employee questions about leave policies, attendance, holidays and workplace guidelines using company documents.",
            height=120,
            help="Describe the persona, domain, audience, and key policies the agent should handle."
        )
        doc_folder_input = st.text_input(
            "Document Corpus Folder Path",
            value="demos/hr_assistant/documents",
            help="Relative or absolute path to directory containing PDF, TXT, CSV files."
        )
        output_dir_input = st.text_input(
            "Artifacts Output Directory",
            value="outputs/custom_agent/artifacts"
        )
        iterations_slider = st.slider("Max Optimization Iterations", min_value=1, max_value=3, value=3)

    with col2:
        st.subheader("Factory Guardrails")
        st.info("🛡 **Groundability Guard:** Prevents unsupported requirements from entering agent scope.")
        st.info("🧪 **Auto-Eval Generator:** Synthesizes >=20 test cases directly from evidence.")
        st.info("⚖️ **Hybrid Judge:** Enforces deterministic facts, citations, and refusal rules.")
        st.info("🔄 **Critic-Optimizer Loop:** Max 3 iterations with targeted parameter & prompt updates.")

    if st.button("🚀 Start ForgeAI Factory Pipeline", type="primary"):
        if not os.path.exists(doc_folder_input):
            st.error(f"Document folder not found: '{doc_folder_input}'")
        else:
            with st.spinner("Executing ForgeAI Autonomous Pipeline..."):
                status_box = st.empty()
                status_box.info("Pipeline initialized. Running Intake & Document Inspection...")

                try:
                    factory = ForgeAIFactory(max_iterations=iterations_slider)
                    results = factory.build_agent(
                        brief=brief_input,
                        doc_folder=doc_folder_input,
                        output_dir=output_dir_input,
                        unattended=True
                    )
                    st.session_state["last_run"] = results
                    st.session_state["artifacts_dir"] = output_dir_input
                    st.session_state["doc_folder"] = doc_folder_input

                    status_box.success("🎉 Agent built, tested, and optimized successfully!")
                    st.balloons()
                except Exception as e:
                    status_box.error(f"Error during factory execution: {str(e)}")

    # Show results of the last run
    if "last_run" in st.session_state:
        res = st.session_state["last_run"]
        st.divider()
        st.subheader(f"✅ Generated Agent: {res['agent_definition'].agent_name}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Indexed Documents", len(res['requirements'].document_inventory))
        c2.metric("Groundability Index", f"{res['groundability'].overall_groundability_score * 100:.0f}%")
        final_sc = res['scorecards'][-1]
        c3.metric("Final Pass Rate", f"{final_sc.pass_rate * 100:.1f}%")
        c4.metric("Iterations Run", len(res['scorecards']))

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Authorized Tools")
            st.write(res['agent_definition'].tool_selection or ["None (Strict Retrieval Only)"])
            st.markdown("#### Supported Topics")
            for t in res['groundability'].supported_topics:
                st.write(f"- **{t.topic}** ({', '.join(t.evidence_sources)})")

        with col_b:
            st.markdown("#### Unsupported Topics (Refused)")
            for ut in res['groundability'].unsupported_topics:
                st.write(f"- 🚫 **{ut.topic}**: {ut.reason}")

# TAB 2: EVALUATION & SCORECARDS
with tabs[1]:
    st.header("Evaluation Results & Diagnostics")
    if "last_run" in st.session_state:
        res = st.session_state["last_run"]
        scorecards = res["scorecards"]

        st.subheader("Optimization Progression")
        iter_data = []
        for sc in scorecards:
            iter_data.append({
                "Iteration": f"Iter {sc.iteration}",
                "Pass Rate (%)": round(sc.pass_rate * 100, 1),
                "Passed": sc.passed_tests,
                "Failed": sc.failed_tests,
                "Grounding (%)": round(sc.metric_breakdown.get("grounding", 0) * 100, 1),
                "Factual (%)": round(sc.metric_breakdown.get("factual_correctness", 0) * 100, 1),
                "Citations (%)": round(sc.metric_breakdown.get("citation_correctness", 0) * 100, 1),
                "Refusals (%)": round(sc.metric_breakdown.get("refusal_correctness", 0) * 100, 1)
            })
        st.dataframe(pd.DataFrame(iter_data), use_container_width=True)

        st.subheader(f"Individual Case Results ({scorecards[-1].total_tests} Tests)")
        case_rows = []
        for cr in scorecards[-1].case_results:
            case_rows.append({
                "ID": cr.test_id,
                "Passed": "✅" if cr.passed else "❌",
                "Question": cr.question,
                "Factual": cr.factual_correctness,
                "Citation": cr.citation_correctness,
                "Refusal": cr.refusal_correctness,
                "Failures": ", ".join(cr.failure_reasons) if cr.failure_reasons else "None"
            })
        st.dataframe(pd.DataFrame(case_rows), use_container_width=True)

        st.subheader("Final Honest Report")
        st.markdown(res["report_md"])
    else:
        st.info("Run an agent build in the 'Agent Factory' tab to view evaluation scorecards and logs.")

# TAB 3: LIVE AGENT CHAT
with tabs[2]:
    st.header("Interactive Agent Chat")
    default_def = "demos/hr_assistant/artifacts/agent_definition.json"
    if "artifacts_dir" in st.session_state:
        default_def = os.path.join(st.session_state["artifacts_dir"], "agent_definition.json")

    agent_path_input = st.text_input("Agent Definition Path", value=default_def)
    agent_docs_input = st.text_input("Document Directory", value=st.session_state.get("doc_folder", "demos/hr_assistant/documents"))

    if os.path.exists(agent_path_input):
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # Display conversation history
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "citations" in msg and msg["citations"]:
                    st.caption(f"Sources: {', '.join(msg['citations'])}")

        user_q = st.chat_input("Ask a question about verified company policies or spare parts...")
        if user_q:
            st.session_state["chat_history"].append({"role": "user", "content": user_q})
            with st.chat_message("user"):
                st.markdown(user_q)

            runner = GenericChatRunner(definition_path=agent_path_input, doc_folder=agent_docs_input)
            response = runner.ask(user_q)

            with st.chat_message("assistant"):
                st.markdown(response.answer)
                if response.citations:
                    st.caption(f"Citations: {', '.join(response.citations)}")
                if response.tool_calls:
                    st.info(f"Tool Executed: {[tc['tool'] for tc in response.tool_calls]}")

            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": response.answer,
                "citations": response.citations
            })
    else:
        st.warning(f"Agent definition not found at '{agent_path_input}'. Run a factory build or provide a valid path.")

# TAB 4: SYSTEM & LLM STATUS
with tabs[3]:
    st.header("System & Health Diagnostics")
    llm = get_llm_client()
    avail, msg = llm.is_available()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### LLM Backend")
        st.write(f"**Selected Provider:** `{st.secrets.get('LLM_PROVIDER', os.getenv('LLM_PROVIDER', 'ollama'))}`")
        st.write(f"**Availability:** {'🟢 Online' if avail else '🟡 Fallback/Offline'}")
        st.code(msg)

    with c2:
        st.markdown("### Registered Tools")
        for tool_name in registry.list_tools():
            t = registry.get_tool(tool_name)
            st.write(f"- **`{tool_name}`**: {t.description}")
