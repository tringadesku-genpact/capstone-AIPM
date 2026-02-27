from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("A_intake")
    # logic here
    return state