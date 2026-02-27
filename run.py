import argparse
from pathlib import Path
from datetime import datetime, timezone
import random
import string

from src.pm.graph import build_graph
from src.pm.state import create_initial_state
from src.pm.utils.io import load_json, load_yaml
from src.pm.utils.validate import validate_json


def make_run_id():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(4))
    return f"run_{ts}_{suffix}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--policy", required=True)
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

    print(f"Run complete: {out_dir}")

    # debug trace faza e pare
    if "trace" in final_state:
        print("Execution trace:", final_state["trace"])


if __name__ == "__main__":
    main()