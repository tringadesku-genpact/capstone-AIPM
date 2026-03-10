from pathlib import Path
from datetime import datetime, timezone
import random
import string

from src.pm.graph import build_graph
from src.pm.state import create_initial_state
from src.pm.utils.io import load_json, load_yaml
from src.pm.utils.validate import validate_json


def make_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(4))
    return f"run_{ts}_{suffix}"


def run_pipeline(bundle_path: str, policy_path: str = "policies/default.yaml"):
    run_id = make_run_id()
    out_dir = Path("runs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_json(bundle_path)
    policy = load_yaml(policy_path)

    schema_path = Path("schemas") / "bundle.schema.json"
    validate_json(bundle, str(schema_path))

    state = create_initial_state(
        bundle_path=bundle_path,
        policy_path=policy_path,
        bundle=bundle,
        policy=policy,
        run_id=run_id,
        out_dir=str(out_dir),
    )

    graph = build_graph().compile()
    final_state = graph.invoke(state)

    return final_state