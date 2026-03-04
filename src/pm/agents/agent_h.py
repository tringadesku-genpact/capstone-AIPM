"""
Agent H - Lead PM

Reads:  state["findings"], state["risk_summary"], state["context_packet"]
Writes: final_plan.json
Stores: state["final_plan"]
"""

from __future__ import annotations
from typing import Any, Dict, List

from ..state import PMState
from src.pm.utils.output import write_json


def _collect_findings(state: PMState) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    findings = state.get("findings", {}) or {}

    # metrics/risk payloads have shape {"agent":..., "findings":[...]}
    for _, payload in findings.items():
        if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
            all_items.extend(payload["findings"])
        elif isinstance(payload, list):
            all_items.extend(payload)
    return all_items


def _decision(risk_level: str, risk_score: int, missing_info: List[str]) -> str:
    if missing_info:
        return "NEEDS_INFO"
    if risk_level == "high" or risk_score >= 70:
        return "NO_GO"
    if risk_level == "medium" or risk_score >= 40:
        return "GO_WITH_GUARDRAILS"
    return "GO"


def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("H_lead_pm")

    ctx = state.get("context_packet", {}) or {}
    risk = state.get("risk_summary", {}) or {}

    bundle_id = ctx.get("bundle_id", "")
    request_type = ctx.get("request_type", "")
    problem = ctx.get("problem_statement", "")
    missing_info = ctx.get("missing_info", []) or []
    hotspots = ctx.get("hotspots", []) or []

    risk_level = risk.get("level", "low")
    risk_score = int(risk.get("score", 0))

    decision = _decision(risk_level, risk_score, missing_info)
    all_findings = _collect_findings(state)

    rationale = [
        f"Request type: {request_type}",
        f"Risk: {risk_level} (score={risk_score})",
    ]
    if problem:
        rationale.insert(0, f"Problem: {problem}")
    if hotspots:
        rationale.append(f"Hotspots: {hotspots}")
    if missing_info:
        rationale.append(f"Missing info: {missing_info}")

    next_steps: List[str] = []
    if decision == "GO":
        next_steps = [
            "Proceed with implementation using a small canary rollout.",
            "Track north-star and guardrail metrics post-release.",
        ]
    elif decision == "GO_WITH_GUARDRAILS":
        next_steps = [
            "Implement behind a feature flag and staged rollout plan.",
            "Define monitoring metrics + alert thresholds + rollback steps.",
            "Complete privacy/security review if PII is involved.",
        ]
    elif decision == "NO_GO":
        next_steps = [
            "Do not proceed to launch until risk is reduced.",
            "Propose mitigations and re-run after changes.",
        ]
    elif decision == "NEEDS_INFO":
        next_steps = [
            "Collect missing information and attach supporting evidence.",
            "Re-run the pipeline after missing items are provided.",
        ]

    final_plan = {
        "bundle_id": bundle_id,
        "decision": decision,
        "rationale": "\n".join(rationale),
        "key_findings_count": len(all_findings),
        "next_steps": next_steps,
        "open_questions": missing_info,
    }

    write_json(state["out_dir"], "final_plan.json", final_plan)
    state["final_plan"] = final_plan
    return state    