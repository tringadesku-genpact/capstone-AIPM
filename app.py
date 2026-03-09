import json
from pathlib import Path

import streamlit as st

from src.pm.pipeline import run_pipeline


st.set_page_config(
    page_title="PM Pipeline Runner",
    page_icon="📌",
    layout="wide",
)

st.title("PM Pipeline Runner")
st.caption("Upload a bundle JSON, run the PM pipeline, and review generated artifacts.")

with st.sidebar:
    st.header("Run Configuration")
    uploaded_bundle = st.file_uploader("Upload bundle JSON", type=["json"])
    policy = st.selectbox(
        "Select policy",
        ["policies/default.yaml"]
    )
    run_clicked = st.button("Run Pipeline", use_container_width=True)

if run_clicked:
    if not uploaded_bundle:
        st.error("Upload a bundle first.")
    else:
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)

        bundle_file = uploads_dir / uploaded_bundle.name
        bundle_file.write_bytes(uploaded_bundle.read())

        try:
            with st.spinner("Running PM pipeline..."):
                final_state = run_pipeline(
                    bundle_path=str(bundle_file),
                    policy_path=policy,
                )

            st.success("Pipeline finished successfully.")

            out_dir = Path(final_state["out_dir"]) / "artifacts"

            final_plan_file = out_dir / "final_plan.json"
            prd_file = out_dir / "prd.md"
            roadmap_file = out_dir / "roadmap.json"
            decision_log_file = out_dir / "decision_log.md"
            experiment_plan_file = out_dir / "experiment_plan.md"
            backlog_csv_file = out_dir / "backlog.csv"

            final_plan_data = {}
            roadmap_data = {}

            if final_plan_file.exists():
                final_plan_data = json.loads(final_plan_file.read_text(encoding="utf-8"))

            if roadmap_file.exists():
                roadmap_data = json.loads(roadmap_file.read_text(encoding="utf-8"))

            decision = final_plan_data.get("decision", "N/A")
            findings_count = final_plan_data.get("key_findings_count", "N/A")
            run_id = final_state.get("run_id", "N/A")
            out_dir_value = final_state.get("out_dir", "N/A")

            risk_level = "N/A"
            risk_score = "N/A"
            risk_summary = final_state.get("risk_summary", {}) or {}
            if risk_summary:
                risk_level = risk_summary.get("level", "N/A")
                risk_score = risk_summary.get("score", "N/A")

            st.subheader("Overview")
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Decision", decision)
            col2.metric("Risk Level", risk_level)
            col3.metric("Risk Score", risk_score)
            col4.metric("Findings", findings_count)

            st.markdown("### Run Details")
            details_col1, details_col2 = st.columns(2)
            details_col1.write(f"**Run ID:** `{run_id}`")
            details_col2.write(f"**Output Directory:** `{out_dir_value}`")

            next_steps = final_plan_data.get("next_steps", []) or []
            open_questions = final_plan_data.get("open_questions", []) or []
            contradictions = final_plan_data.get("contradictions", []) or []
            trace = final_state.get("trace", []) or []

            left_col, right_col = st.columns(2)

            with left_col:
                st.markdown("### Next Steps")
                if next_steps:
                    for step in next_steps:
                        st.markdown(f"- {step}")
                else:
                    st.info("No next steps found.")

                st.markdown("### Open Questions")
                if open_questions:
                    for question in open_questions:
                        st.markdown(f"- {question}")
                else:
                    st.info("No open questions found.")

            with right_col:
                st.markdown("### Contradictions / Tradeoffs")
                if contradictions:
                    for item in contradictions:
                        st.markdown(f"- {item}")
                else:
                    st.info("No contradictions detected.")

                st.markdown("### Execution Trace")
                if trace:
                    st.code(" -> ".join(trace))
                else:
                    st.info("No execution trace found.")

            st.markdown("### Generated Artifacts")
            artifact_col1, artifact_col2, artifact_col3 = st.columns(3)

            with artifact_col1:
                st.write(f"PRD: {'✅' if prd_file.exists() else '❌'}")
                st.write(f"Decision Log: {'✅' if decision_log_file.exists() else '❌'}")

            with artifact_col2:
                st.write(f"Roadmap: {'✅' if roadmap_file.exists() else '❌'}")
                st.write(f"Final Plan: {'✅' if final_plan_file.exists() else '❌'}")

            with artifact_col3:
                st.write(f"Experiment Plan: {'✅' if experiment_plan_file.exists() else '❌'}")
                st.write(f"Backlog CSV: {'✅' if backlog_csv_file.exists() else '❌'}")

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
                ["Final Plan", "PRD", "Decision Log", "Roadmap", "Experiment Plan", "Backlog"]
            )

            with tab1:
                st.subheader("Final Plan")
                if final_plan_file.exists():
                    st.json(final_plan_data)
                    st.download_button(
                        label="Download final_plan.json",
                        data=final_plan_file.read_bytes(),
                        file_name="final_plan.json",
                        mime="application/json",
                    )
                else:
                    st.warning("final_plan.json not found.")

            with tab2:
                st.subheader("PRD")
                if prd_file.exists():
                    prd_text = prd_file.read_text(encoding="utf-8")
                    st.markdown(prd_text)
                    st.download_button(
                        label="Download prd.md",
                        data=prd_file.read_bytes(),
                        file_name="prd.md",
                        mime="text/markdown",
                    )
                else:
                    st.warning("prd.md not found.")

            with tab3:
                st.subheader("Decision Log")
                if decision_log_file.exists():
                    decision_log_text = decision_log_file.read_text(encoding="utf-8")
                    st.text(decision_log_text)
                    st.download_button(
                        label="Download decision_log.md",
                        data=decision_log_file.read_bytes(),
                        file_name="decision_log.md",
                        mime="text/markdown",
                    )
                else:
                    st.warning("decision_log.md not found.")

            with tab4:
                st.subheader("Roadmap")
                if roadmap_file.exists():
                    st.json(roadmap_data)
                    st.download_button(
                        label="Download roadmap.json",
                        data=roadmap_file.read_bytes(),
                        file_name="roadmap.json",
                        mime="application/json",
                    )
                else:
                    st.warning("roadmap.json not found.")

            with tab5:
                st.subheader("Experiment Plan")
                if experiment_plan_file.exists():
                    experiment_text = experiment_plan_file.read_text(encoding="utf-8")
                    st.markdown(experiment_text)
                    st.download_button(
                        label="Download experiment_plan.md",
                        data=experiment_plan_file.read_bytes(),
                        file_name="experiment_plan.md",
                        mime="text/markdown",
                    )
                else:
                    st.warning("experiment_plan.md not found.")

            with tab6:
                st.subheader("Backlog")
                if backlog_csv_file.exists():
                    backlog_text = backlog_csv_file.read_text(encoding="utf-8")
                    st.code(backlog_text)
                    st.download_button(
                        label="Download backlog.csv",
                        data=backlog_csv_file.read_bytes(),
                        file_name="backlog.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("backlog.csv not found.")

        except Exception as e:
            st.error(f"Pipeline failed: {e}")
else:
    st.info("Upload a bundle and click 'Run Pipeline' from the sidebar.")