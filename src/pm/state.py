from typing import Dict, Any


PMState = Dict[str, Any]

def create_initial_state(
    bundle_path: str,
    policy_path: str,
    bundle: Dict[str, Any],
    policy: Dict[str, Any],
    run_id: str,
    out_dir: str,
) -> PMState:

    return {
        # metadata
        "bundle_path": bundle_path,
        "policy_path": policy_path,
        "run_id": run_id,
        "out_dir": out_dir,

        # loaded input
        "bundle": bundle,
        "policy": policy,

        "context_packet": None,
        "findings": {},
        "final_plan": None,
    }