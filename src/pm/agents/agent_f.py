from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("F_feasibility")
    # logic here
    return state