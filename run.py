import argparse
from pathlib import Path
from datetime import datetime, timezone
import random
import string

from src.pm.graph import build_graph
from src.pm.state import create_initial_state
from src.pm.utils.io import load_json, load_yaml
from src.pm.utils.validate import validate_json

import os
from src.pm.utils.github_issue import create_issue


def make_run_id():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(4))
    return f"run_{ts}_{suffix}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--repo", required=False, help="GitHub repo in owner/name format")
    args = parser.parse_args()

    # Create run folder
    run_id = make_run_id()
    out_dir = Path("runs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load input
    bundle = load_json(args.bundle)
    policy = load_yaml(args.policy)

    # Validate bundle against schema
    schema_path = Path("schemas") / "bundle.schema.json"
    validate_json(bundle, str(schema_path))

    # Create initial state
    state = create_initial_state(
        bundle_path=args.bundle,
        policy_path=args.policy,
        bundle=bundle,
        policy=policy,
        run_id=run_id,
        out_dir=str(out_dir),
    )

    # Build and run graph
    graph = build_graph().compile()
    final_state = graph.invoke(state)


    if args.repo:
        github_token = os.getenv("GITHUB_TOKEN")

        if not github_token:
            print("Skipping GitHub issue creation: GITHUB_TOKEN not set.")
        else:
            final_plan_wrapper = final_state.get("final_plan", {}) or {}
            final_plan = final_plan_wrapper.get("final_plan", {}) or {}

            decision = final_plan.get("decision", "UNKNOWN")
            next_steps = final_plan.get("next_steps", []) or []

            bundle_id = (
                final_state.get("context_packet", {}).get("bundle_id")
                or final_state.get("bundle", {}).get("bundle_id")
                or "unknown_bundle"
            )

            artifacts_dir = Path(final_state.get("out_dir", "")) / "artifacts"

            body_lines = [
                "## PM Pipeline Analysis",
                "",
                f"**Bundle:** {bundle_id}",
                "",
                f"**Decision:** {decision}",
                "",
                "### Next Steps",
            ]

            if next_steps:
                body_lines.extend([f"- {step}" for step in next_steps])
            else:
                body_lines.append("- None")

            body_lines.extend([
                "",
                "### Artifacts Generated",
                f"- PRD: `{artifacts_dir / 'prd.md'}`",
                f"- Roadmap: `{artifacts_dir / 'roadmap.json'}`",
                f"- Decision Log: `{artifacts_dir / 'decision_log.md'}`",
                f"- Experiment Plan: `{artifacts_dir / 'experiment_plan.md'}`",
                f"- Backlog: `{artifacts_dir / 'backlog.csv'}`",
            ])

            body = "\n".join(body_lines)

            issue_url = create_issue(
                github_token=github_token,
                repo_name=args.repo,
                title=f"PM Pipeline Analysis – {bundle_id}",
                body=body,
            )

            print(f"GitHub Issue created: {issue_url}")

    print(f"Run complete: {out_dir}")

    # debug trace faza e pare
    if "trace" in final_state:
        print("Execution trace:", final_state["trace"])


if __name__ == "__main__":
    main()