"""
Agent G - Risk Agent

Reads:  state["context_packet"], state["bundle"], state["policy"]
Writes: findings_risk.json
Stores: state["findings"]["risk"], state["risk_summary"]
"""

from __future__ import annotations
from typing import Any, Dict, List

from ..state import PMState
from src.pm.utils.output import write_json
from src.pm.utils.validate import validate_json


_COUNTER = 0


def _finding(ftype: str, impact: str, confidence: float, summary: str,
             recommendation: str, evidence: List[str], assumptions: List[str] | None = None) -> Dict[str, Any]:
    global _COUNTER
    _COUNTER += 1
    return {
        "id": f"G-{_COUNTER:03d}",
        "agent": "G_risk",
        "type": ftype,
        "impact": impact,
        "confidence": round(float(confidence), 2),
        "summary": summary,
        "recommendation": recommendation,
        "evidence": evidence,
        "assumptions": assumptions or [],
    }


def _risk_score(handles_pii: bool, request_type: str, missing_info: List[str], policy: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []

    if handles_pii:
        score += 35
        reasons.append("Handles PII → privacy/compliance exposure.")

    rt = (request_type or "").lower().strip()
    if rt == "high_risk_idea":
        score += 30
        reasons.append("High-risk idea request type.")
    elif rt == "metric_drop":
        score += 15
        reasons.append("Metric drop → reliability/quality risk.")
    elif rt == "competitive_parity":
        score += 10
        reasons.append("Competitive parity → medium product risk.")

    strict = bool(policy.get("risk", {}).get("strict_mode", False))
    if strict:
        score += 10
        reasons.append("Policy strict_mode enabled.")

    if missing_info:
        bump = min(20, 5 * len(missing_info))
        score += bump
        reasons.append(f"Missing info increases uncertainty (+{bump}).")

    score = max(0, min(100, score))
    level = "low"
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"

    return {"score": score, "level": level, "reasons": reasons}


def run(state: PMState) -> PMState:
    global _COUNTER
    _COUNTER = 0

    state.setdefault("trace", []).append("G_risk")

    bundle = state.get("bundle", {}) or {}
    policy = state.get("policy", {}) or {}
    ctx = state.get("context_packet", {}) or {}

    bundle_id = ctx.get("bundle_id") or bundle.get("bundle_id", "")
    request_type = ctx.get("request_type") or bundle.get("request_type", "")
    product = ctx.get("product") or bundle.get("product", {})
    handles_pii = bool(product.get("handles_pii", False))

    missing_info = ctx.get("missing_info", []) or []
    hotspots = ctx.get("hotspots", []) or []

    risk = _risk_score(handles_pii, request_type, missing_info, policy)

    findings: List[Dict[str, Any]] = []

    # Privacy / compliance risk
    if handles_pii:
        findings.append(_finding(
            "privacy_compliance",
            "high" if risk["level"] == "high" else "medium",
            0.75 if not missing_info else 0.6,
            "Product handles PII which increases privacy and compliance risk for this change.",
            "Add privacy review, minimize data collection, document retention/access controls, and ensure auditability.",
            [f"handles_pii={handles_pii}", f"request_type={request_type}"],
            ["Assumes PII is in the impacted flow unless proven otherwise."]
        ))

    # Hotspots → operational risk
    if hotspots:
        findings.append(_finding(
            "operational_reliability",
            "high" if risk["level"] == "high" else "medium",
            0.65,
            f"Hotspots detected ({len(hotspots)}): {hotspots}. These areas may carry elevated operational risk.",
            "Use staged rollout, monitoring/alerts, and a rollback plan focused on hotspot flows.",
            [f"hotspots={hotspots}"],
        ))

    # Missing info → decision uncertainty
    if missing_info:
        findings.append(_finding(
            "unknowns",
            "high" if risk["level"] == "high" else "medium",
            0.7,
            "Key information is missing, increasing decision risk and lowering confidence.",
            "Block full rollout until missing items are provided and validated; re-run pipeline afterwards.",
            [f"missing_info={missing_info}"],
        ))

    # Validate findings
    for f in findings:
        validate_json(f, "schemas/finding.schema.json")

    payload = {
        "agent": "G_risk",
        "risk_summary": risk,
        "findings": findings,
    }

    write_json(state["out_dir"], "findings_risk.json", payload)

    state.setdefault("findings", {})["risk"] = payload
    state["risk_summary"] = risk
    return state