"""
Agent H - Lead PM (Orchestrator + Judge)

Reads:   state["context_packet"],state["findings"], state["risk_summary"]
Writes: final_plan.json, prd.md, roadmap.json, decision_log.md
Stores: state["final_plan"]
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Any, Dict, List

from ..state import PMState
from ..agents.agent_d import build_experiment_plan_md
from ..agents.agent_e import build_prd_requirements_section
from src.pm.utils.output import write_json


def _collect_findings(state: PMState) -> List[Dict[str, Any]]:
    all_items: List[Dict[str, Any]] = []
    findings = state.get("findings", {}) or {}

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
    text = " ".join(
        f"{f.get('type', '')} {f.get('summary', '')} {f.get('recommendation', '')}".lower()
        for f in findings
    )

    contradictions: List[str] = []

    if ("privacy" in text or "compliance" in text) and (
        "growth" in text or "lift" in text or "adoption" in text
    ):
        contradictions.append(
            "Growth upside vs privacy/compliance cost (needs explicit tradeoff + mitigations)."
        )

    if ("latency" in text or "performance" in text) and (
        "more checks" in text or "additional step" in text
    ):
        contradictions.append(
            "Performance risk vs added workflow complexity (may require phased rollout)."
        )

    return contradictions


def _write_md(out_dir: str, filename: str, content: str) -> None:
    path = Path(out_dir) / filename
    path.write_text(content, encoding="utf-8")


def _write_backlog_csv(out_dir: str, backlog: List[Dict[str, Any]]) -> None:
    path = Path(out_dir) / "backlog.csv"

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "backlog_id",
            "title",
            "priority",
            "acceptance_criteria",
            "definition_of_done",
        ])

        for item in backlog:
            writer.writerow([
                item.get("backlog_id", ""),
                item.get("title", ""),
                " / ".join(item.get("acceptance_criteria", [])),
                item.get("priority", ""),
                item.get("definition_of_done", ""),
            ])


def _build_prd(
    ctx: Dict[str, Any],
    risk: Dict[str, Any],
    final_plan: Dict[str, Any],
    req_output: Dict[str, Any],
    feasibility_output: Dict[str, Any],
) -> str:
    product = ctx.get("product", {}) or {}
    bundle_id = ctx.get("bundle_id", "")
    product_name = product.get("name", "Product")
    problem = ctx.get("problem_statement", "") or "_Not provided in bundle._"
    request_type = ctx.get("request_type", "")
    missing_info = ctx.get("missing_info", []) or []

    requirements = req_output.get("requirements", []) or []
    journey = req_output.get("user_journey", []) or []

    risk_level = risk.get("level", "low")
    risk_score = risk.get("score", 0)
    risk_reasons = risk.get("reasons", []) or []

    phased = feasibility_output.get("phased_delivery", {}) or {}
    mvp = phased.get("mvp", []) or []
    v1 = phased.get("v1", []) or []
    v2 = phased.get("v2", []) or []

    lines: List[str] = []

    lines.append(f"# PRD — {product_name} ({bundle_id})\n")
    lines.append("## Problem\n")
    lines.append(problem + "\n")

    lines.append("## Request Type\n")
    lines.append(f"- {request_type}\n")

    lines.append("## Goals\n")
    lines.append(f"- Support the final decision: **{final_plan.get('decision', 'UNKNOWN')}**")
    lines.append("- Improve customer experience and measurable product outcomes.")
    lines.append("- Keep scope controlled for MVP.\n")

    lines.append("## Non-Goals\n")
    lines.append("- Anything not required to validate MVP success.")
    lines.append("- Broader platform redesign unless explicitly required.\n")

    if journey:
        lines.append("## User Journey\n")
        for step in journey:
            lines.append(f"- {step}")
        lines.append("")

    lines.append("## Scope\n")
    lines.append("### MVP")
    for item in mvp or ["Deliver the minimum viable change that addresses the problem statement."]:
        lines.append(f"- {item}")
    lines.append("")

    if v1:
        lines.append("### V1")
        for item in v1:
            lines.append(f"- {item}")
        lines.append("")

    if v2:
        lines.append("### V2")
        for item in v2:
            lines.append(f"- {item}")
        lines.append("")

    lines.append(build_prd_requirements_section(requirements))

    lines.append("## Rollout Plan\n")
    lines.append("- Feature flag + staged rollout")
    lines.append("- Monitor key metrics and rollback if guardrails fail")
    lines.append("- Start with limited exposure before wider launch\n")

    lines.append("## Risks\n")
    lines.append(f"- Risk level: **{risk_level}** (score={risk_score})")

    if risk_reasons:
        lines.append("\n### Risk Drivers")
        for reason in risk_reasons:
            lines.append(f"- {reason}")

    if missing_info:
        lines.append("\n### Open Questions")
        for q in missing_info:
            lines.append(f"- {q}")

    return "\n".join(lines).strip() + "\n"


def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("H_lead_pm")

    ctx = state.get("context_packet", {}) or {}
    risk = state.get("risk_summary", {}) or {}
    findings = _collect_findings(state)

    findings_map = state.get("findings", {}) or {}
    metrics_output = findings_map.get("metrics", {}) or {}
    req_output = findings_map.get("requirements", {}) or {}
    feasibility_output = findings_map.get("feasibility", {}) or {}

    bundle_id = ctx.get("bundle_id", "")
    request_type = ctx.get("request_type", "")
    problem = ctx.get("problem_statement", "")
    product = ctx.get("product", {}) or {}
    product_name = product.get("name", "Product")
    missing_info = ctx.get("missing_info", []) or []
    hotspots = ctx.get("hotspots", []) or []

    risk_level = str(risk.get("level", "low"))
    risk_score = int(risk.get("score", 0))
    decision = _decision(risk_level, risk_score, missing_info)

    contradictions = _detect_contradictions(findings)
    open_questions = list(missing_info)

    rationale_lines = [
        f"Problem: {problem}" if problem else "Problem: (not provided)",
        f"Request type: {request_type}",
        f"Risk: {risk_level} (score={risk_score})",
        f"Total findings considered: {len(findings)}",
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
            "Review backlog priorities before sprint start.",
        ]
    elif decision == "PROCEED_WITH_MITIGATIONS":
        next_steps = [
            "Implement behind a feature flag and staged rollout plan.",
            "Define monitoring, alert thresholds, and rollback steps.",
            "Complete privacy/security review if PII is involved.",
            "Confirm feasibility dependencies and ownership.",
        ]
    elif decision == "VALIDATE_FIRST":
        next_steps = [
            "Collect missing information and attach supporting evidence.",
            "Run a small validation before committing to full build.",
            "Re-run the pipeline after missing items are resolved.",
        ]
    elif decision == "DO_NOT_PURSUE":
        next_steps = [
            "Do not proceed until risks are reduced or scope changes.",
            "Consider alternative approaches with lower operational or compliance risk.",
        ]

    final_plan = {
        "bundle_id": bundle_id,
        "product_name": product_name,
        "decision": decision,
        "rationale": "\n".join(rationale_lines),
        "key_findings_count": len(findings),
        "next_steps": next_steps,
        "open_questions": open_questions,
        "contradictions": contradictions,
    }

    write_json(state["out_dir"], "final_plan.json", final_plan)

    # decision_log.md
    decision_log_lines: List[str] = []
    decision_log_lines.append(f"# Decision Log — {bundle_id}\n")
    decision_log_lines.append(f"## Decision\n**{decision}**\n")
    decision_log_lines.append("## Rationale\n")
    decision_log_lines.extend([f"- {line}" for line in rationale_lines])
    decision_log_lines.append("")

    if contradictions:
        decision_log_lines.append("## Tradeoffs / Contradictions\n")
        decision_log_lines.extend([f"- {c}" for c in contradictions])
        decision_log_lines.append("")

    if open_questions:
        decision_log_lines.append("## Open Questions\n")
        decision_log_lines.extend([f"- {q}" for q in open_questions])
        decision_log_lines.append("")

    decision_log_lines.append("## Next Steps\n")
    decision_log_lines.extend([f"- {s}" for s in next_steps])
    decision_log_lines.append("")

    _write_md(state["out_dir"], "decision_log.md", "\n".join(decision_log_lines))

    # prd.md
    prd_md = _build_prd(ctx, risk, final_plan, req_output, feasibility_output)
    _write_md(state["out_dir"], "prd.md", prd_md)

    # roadmap.json
    phased = feasibility_output.get("phased_delivery", {}) or {}
    dependencies = feasibility_output.get("dependencies", []) or []

    roadmap = {
        "bundle_id": bundle_id,
        "assumptions": [
            "Milestones are based on Agent F phased delivery and Agent E requirements."
        ],
        "milestones": [
            {
                "name": "MVP",
                "description": "Deliver the minimum viable scope to address the core problem.",
                "items": phased.get("mvp", []),
                "dependencies": [d.get("dependency", "") for d in dependencies],
            },
            {
                "name": "V1",
                "description": "Expand with guardrails, monitoring, and UX hardening.",
                "items": phased.get("v1", []),
                "dependencies": [d.get("dependency", "") for d in dependencies],
            },
            {
                "name": "V2",
                "description": "Optimize and extend once the solution is stable.",
                "items": phased.get("v2", []),
                "dependencies": [d.get("dependency", "") for d in dependencies],
            },
        ],
    }
    write_json(state["out_dir"], "roadmap.json", roadmap)

    # experiment_plan.md
    framework = metrics_output.get("metric_framework", {})
    events = metrics_output.get("event_taxonomy", [])

    if framework and events:
        experiment_md = build_experiment_plan_md(
            framework=framework,
            events=events,
            product_name=product_name,
            rtype=request_type,
        )
    else:
        experiment_md = f"""# Experiment Plan — {product_name} ({request_type})

## Status
No experiment plan could be generated because Agent D metrics output is incomplete.

## Required Inputs
- metric_framework
- event_taxonomy
"""

    _write_md(state["out_dir"], "experiment_plan.md", experiment_md)

    # backlog.csv
    backlog = req_output.get("backlog", []) or []
    _write_backlog_csv(state["out_dir"], backlog)

    state["final_plan"] = {
        "final_plan": final_plan,
        "roadmap": roadmap,
        "decision": decision,
        "prd_generated": True,
        "experiment_plan_generated": True,
        "backlog_csv_generated": True,
    }

    return state