from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("C_competition")
    # logic here
    return state