from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("B_customer")
    # logic here
    return state