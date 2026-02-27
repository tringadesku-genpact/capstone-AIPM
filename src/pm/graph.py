from langgraph.graph import StateGraph, END
from .agents.agent_a import run as run_a
from .agents.agent_b import run as run_b
from .agents.agent_c import run as run_c
from .agents.agent_d import run as run_d
from .agents.agent_e import run as run_e
from .agents.agent_f import run as run_f
from .agents.agent_g import run as run_g
from .agents.agent_h import run as run_h


def build_graph():
    g = StateGraph(dict)

    g.add_node("A_intake", run_a)
    g.add_node("B_customer", run_b)
    g.add_node("C_competition", run_c)
    g.add_node("D_metrics", run_d)
    g.add_node("E_requirements", run_e)
    g.add_node("F_feasibility", run_f)
    g.add_node("G_risk", run_g)
    g.add_node("H_lead_pm", run_h)

    g.set_entry_point("A_intake")
    g.add_edge("A_intake", "B_customer")
    g.add_edge("B_customer", "C_competition")
    g.add_edge("C_competition", "D_metrics")
    g.add_edge("D_metrics", "E_requirements")
    g.add_edge("E_requirements", "F_feasibility")
    g.add_edge("F_feasibility", "G_risk")
    g.add_edge("G_risk", "H_lead_pm")
    g.add_edge("H_lead_pm", END)

    return g