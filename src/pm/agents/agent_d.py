from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("D_metrics")
    # logic here
    return state