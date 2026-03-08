import json
from pathlib import Path

import streamlit as st

from src.pm.pipeline import run_pipeline


st.set_page_config(page_title="PM Pipeline Runner", layout="wide")
st.title("PM Pipeline Runner")
st.write("Upload a bundle JSON, run the PM pipeline, and review generated artifacts.")

uploaded_bundle = st.file_uploader("Upload bundle JSON", type=["json"])

policy = st.selectbox(
    "Select policy",
    ["policies/default.yaml"]
)

if st.button("Run Pipeline"):
    if not uploaded_bundle:
        st.error("Upload a bundle first.")
    else:
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)

        bundle_file = uploads_dir / uploaded_bundle.name
        bundle_file.write_bytes(uploaded_bundle.read())

        try:
            final_state = run_pipeline(
                bundle_path=str(bundle_file),
                policy_path=policy,
            )

            st.success("Pipeline finished successfully.")

            out_dir = Path(final_state["out_dir"])

            final_plan_file = out_dir / "final_plan.json"
            prd_file = out_dir / "prd.md"
            roadmap_file = out_dir / "roadmap.json"
            decision_log_file = out_dir / "decision_log.md"
            experiment_plan_file = out_dir / "experiment_plan.md"
            backlog_csv_file = out_dir / "backlog.csv"

            col1, col2 = st.columns(2)

            with col1:
                if final_plan_file.exists():
                    st.subheader("Final Plan")
                    st.json(json.loads(final_plan_file.read_text(encoding="utf-8")))

                if roadmap_file.exists():
                    st.subheader("Roadmap")
                    st.json(json.loads(roadmap_file.read_text(encoding="utf-8")))

            with col2:
                if prd_file.exists():
                    st.subheader("PRD")
                    st.markdown(prd_file.read_text(encoding="utf-8"))

                if decision_log_file.exists():
                    st.subheader("Decision Log")
                    st.text(decision_log_file.read_text(encoding="utf-8"))

            if experiment_plan_file.exists():
                st.subheader("Experiment Plan")
                st.markdown(experiment_plan_file.read_text(encoding="utf-8"))

            if backlog_csv_file.exists():
                st.subheader("Backlog CSV")
                st.download_button(
                    label="Download backlog.csv",
                    data=backlog_csv_file.read_bytes(),
                    file_name="backlog.csv",
                    mime="text/csv",
                )

            st.subheader("Run Metadata")
            st.write(f"**Run ID:** {final_state.get('run_id', 'N/A')}")
            st.write(f"**Output Directory:** `{final_state.get('out_dir', 'N/A')}`")

            trace = final_state.get("trace", [])
            if trace:
                st.subheader("Execution Trace")
                st.write(" → ".join(trace))

        except Exception as e:
            st.error(f"Pipeline failed: {e}")