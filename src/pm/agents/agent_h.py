"""
Agent H - Lead PM (Orchestrator + Judge)

Reads:   state["context_packet"],state["findings"], state["risk_summary"]
Writes: final_plan.json, prd.md, roadmap.json, decision_log.md
Stores: state["final_plan"]
"""

from __future__ import annotations
from typing import Any, Dict, List
from pathlib import Path
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
        return "VALIDATE_FIRST"
    if risk_level == "high" or risk_score >= 70:
        return "DO_NOT_PURSUE"
    if risk_level == "medium" or risk_score >= 40:
        return "PROCEED_WITH_MITIGATIONS"
    return "PROCEED"

def _detect_contradictions(findings: List[Dict[str, Any]]) -> List[str]:
    """
    Simple contradiction heuristics:
    - if any 'privacy' / 'compliance' high AND any 'growth' / 'upside' high, flag a tradeoff.
    """
    text = " ".join(
        f"{f.get('type','')} {f.get('summary','')} {f.get('recommendation','')}".lower()
        for f in findings
    )
    contradictions = []
    if ("privacy" in text or "compliance" in text) and ("growth" in text or "lift" in text or "adoption" in text):
        contradictions.append("Growth upside vs privacy/compliance cost (needs explicit tradeoff + mitigations).")
    if ("latency" in text or "performance" in text) and ("more checks" in text or "additional step" in text):
        contradictions.append("Performance risk vs added workflow complexity (may require phased rollout).")
    return contradictions


def _write_md(out_dir: str, filename: str, content: str) -> None:
    p = Path(out_dir) / filename
    p.write_text(content, encoding="utf-8")

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("H_lead_pm")

    ctx = state.get("context_packet", {}) or {}
    risk = state.get("risk_summary", {}) or {}
    findings = _collect_findings(state)

    bundle_id = ctx.get("bundle_id", "")
    request_type = ctx.get("request_type", "")
    problem = ctx.get("problem_statement", "")
    product = ctx.get("product", {}) or {}
    missing_info = ctx.get("missing_info", []) or []
    hotspots = ctx.get("hotspots", []) or []

    risk_level = risk.get("level", "low")
    risk_score = int(risk.get("score", 0))
    decision = _decision(risk_level, risk_score, missing_info)

    contradictions = _detect_contradictions(findings)
    open_questions = list(missing_info)

    # ---- Final plan (JSON) ----
    rationale_lines = [
        f"Problem: {problem}" if problem else "Problem: (not provided)",
        f"Request type: {request_type}",
        f"Risk: {risk_level} (score={risk_score})",
    ]
    if hotspots:
        rationale_lines.append(f"Hotspots: {hotspots}")
    if contradictions:
        rationale_lines.append(f"Contradictions: {contradictions}")
    if open_questions:
        rationale_lines.append(f"Open questions: {open_questions}")

    next_steps: List[str] = []
    if decision == "PROCEED":
        next_steps = [
            "Proceed with implementation using a small canary rollout.",
            "Track North Star and guardrail metrics post-release.",
        ]
    elif decision == "PROCEED_WITH_MITIGATIONS":
        next_steps = [
            "Implement behind a feature flag and staged rollout plan.",
            "Define monitoring + alert thresholds + rollback steps.",
            "Complete privacy/security review if PII is involved.",
        ]
    elif decision == "VALIDATE_FIRST":
        next_steps = [
            "Collect missing information and attach supporting evidence.",
            "Run a small validation (prototype/usability test/limited pilot) before full build.",
            "Re-run the pipeline after missing items are provided.",
        ]
    elif decision == "DO_NOT_PURSUE":
        next_steps = [
            "Do not proceed until risks are reduced or scope changes.",
            "Consider alternative approaches that reduce privacy/compliance exposure.",
        ]

    final_plan = {
        "bundle_id": bundle_id,
        "decision": decision,
        "rationale": "\n".join(rationale_lines),
        "key_findings_count": len(findings),
        "next_steps": next_steps,
        "open_questions": open_questions,
        "contradictions": contradictions,
    }

    write_json(state["out_dir"], "final_plan.json", final_plan)
    state["final_plan"] = final_plan

    # ---- decision_log.md ----
    decision_log = []
    decision_log.append(f"# Decision Log — {bundle_id}\n")
    decision_log.append(f"## Decision\n**{decision}**\n")
    decision_log.append("## Rationale\n")
    decision_log.append("\n".join([f"- {line}" for line in rationale_lines]) + "\n")
    if contradictions:
        decision_log.append("## Tradeoffs / Contradictions\n")
        decision_log.append("\n".join([f"- {c}" for c in contradictions]) + "\n")
    if open_questions:
        decision_log.append("## Open Questions\n")
        decision_log.append("\n".join([f"- {q}" for q in open_questions]) + "\n")
    decision_log.append("## Next Steps\n")
    decision_log.append("\n".join([f"- {s}" for s in next_steps]) + "\n")

    _write_md(state["out_dir"], "decision_log.md", "\n".join(decision_log))

    # ---- prd.md (minimal, placeholders allowed) ----
    prd = []
    prd.append(f"# PRD — {product.get('name','Product')} ({bundle_id})\n")
    prd.append("## Problem\n")
    prd.append(problem or "_Not provided in bundle._")
    prd.append("\n\n## Goals\n")
    prd.append("- Improve customer experience and measurable outcomes aligned to the request.\n")
    prd.append("## Non-Goals\n")
    prd.append("- Anything not explicitly required for MVP (keep scope controlled).\n")
    prd.append("## Scope\n")
    prd.append("- MVP: Address the core problem statement with the minimum viable changes.\n")
    prd.append("## Requirements (Draft)\n")
    prd.append("- _Placeholder_: Requirements will be refined by Agent E when available.\n")
    prd.append("## Acceptance Criteria (Draft)\n")
    prd.append("- _Placeholder_: Add crisp 'done' checks once requirements are finalized.\n")
    prd.append("## Rollout Plan\n")
    prd.append("- Feature flag + staged rollout\n- Monitoring + rollback plan\n")
    prd.append("## Risks\n")
    prd.append(f"- Risk level: **{risk_level}** (score={risk_score})\n")
    if risk.get("reasons"):
        prd.append("### Risk Drivers\n")
        prd.append("\n".join([f"- {r}" for r in risk["reasons"]]) + "\n")
    if open_questions:
        prd.append("### Open Questions\n")
        prd.append("\n".join([f"- {q}" for q in open_questions]) + "\n")

    _write_md(state["out_dir"], "prd.md", "\n".join(prd))

    # ---- roadmap.json (minimal) ----
    roadmap = {
        "bundle_id": bundle_id,
        "assumptions": [
            "Milestones are draft until feasibility (Agent F) and requirements (Agent E) finalize scope."
        ],
        "milestones": [
            {"name": "MVP", "description": "Deliver core functionality to address the problem statement.", "dependencies": ["Requirements draft", "Basic instrumentation"]},
            {"name": "V1", "description": "Add guardrails, monitoring, and refine UX based on early feedback.", "dependencies": ["Risk mitigations", "Alerting dashboards"]},
            {"name": "V2", "description": "Optimization and scaling, plus any advanced features.", "dependencies": ["Feasibility confirmation", "Performance tuning"]},
        ],
    }
    write_json(state["out_dir"], "roadmap.json", roadmap)
    return state