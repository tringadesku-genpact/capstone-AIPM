from ..state import PMState

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("H_lead_pm")
    # logic here
    return state