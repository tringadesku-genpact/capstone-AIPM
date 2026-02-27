from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("G_risk")
    # logic here
    return state