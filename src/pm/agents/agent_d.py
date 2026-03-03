"""
Agent D - Metrics & Analytics Agent

Reads:  state["context_packet"]
Writes: findings_metrics.json
Stores: state["findings"]["metrics"]
"""

from ..state import PMState
from src.pm.utils.output import write_json
from src.pm.utils.validate import validate_json


# ---- Finding helper ----

_COUNTER = 0

def _finding(ftype, impact, confidence, summary, recommendation, evidence):
    global _COUNTER
    _COUNTER += 1
    return {
        "id": f"D-{_COUNTER:03d}",
        "agent": "D_metrics",
        "type": ftype,
        "impact": impact,
        "confidence": round(confidence, 2),
        "summary": summary,
        "recommendation": recommendation,
        "evidence": evidence,
        "assumptions": [],
    }


# ---- 1. North Star lookup (Smart E-Wallet) ----
#   North Star: Weekly Active Paying Users
#   Key Metrics: transaction success rate, conversion rate,
#                retention/churn, fraud rate, payment latency, crash rate

_FRAMEWORKS = {
    "metric_drop": {
        "north_star": "Restore Weekly Active Paying Users to pre-regression baseline",
        "input_metrics": ["transaction_success_rate", "payment_latency_p95", "crash_rate", "conversion_rate"],
        "guardrails": ["Fraud rate must not increase during fix rollout", "Churn rate stays below threshold"],
    },
    "competitive_parity": {
        "north_star": "Grow Weekly Active Paying Users by matching competitor feature adoption",
        "input_metrics": ["conversion_rate", "transaction_success_rate", "retention_rate", "payment_latency_p95"],
        "guardrails": ["Fraud rate must not increase", "Churn rate must not increase during rollout"],
    },
    "high_risk_idea": {
        "north_star": "Validate lift in Weekly Active Paying Users with statistical significance",
        "input_metrics": ["conversion_rate", "fraud_rate", "transaction_success_rate", "retention_rate"],
        "guardrails": ["PII/KYC compliance gate must pass before launch", "Fraud rate stays within SLO"],
    },
    "accessibility_gap": {
        "north_star": "Close WCAG 2.1 AA compliance gap across payment and login flows",
        "input_metrics": ["a11y_audit_score", "assistive_tech_payment_success_rate", "crash_rate"],
        "guardrails": ["No new WCAG violations in payment flows", "Transaction success rate must not regress"],
    },
}

_DEFAULT = {
    "north_star": "Improve Weekly Active Paying Users for Smart E-Wallet",
    "input_metrics": ["transaction_success_rate", "conversion_rate", "retention_rate", "payment_latency_p95"],
    "guardrails": ["Fraud rate must not regress", "Crash rate stays within SLO"],
}


# ---- 2. Event taxonomy (Smart E-Wallet) ----

def _build_events(ctx):
    events = [
        {"event_name": "payment_initiated", "trigger": "User starts a payment (P2P, merchant, or online)", "properties_hint": "payment_type, amount, currency, method"},
        {"event_name": "transaction_completed", "trigger": "Payment is successfully processed", "properties_hint": "transaction_id, amount, duration_ms, method"},
    ]
    rtype = ctx.get("request_type", "")
    problem = ctx.get("problem_statement", "").lower()

    if rtype == "metric_drop" or "error" in problem or "fail" in problem or "drop" in problem:
        events.append({"event_name": "payment_failed", "trigger": "Transaction fails or is declined", "properties_hint": "error_code, payment_method, decline_reason"})
    if rtype == "high_risk_idea":
        events.append({"event_name": "experiment_exposure", "trigger": "User bucketed into experiment variant", "properties_hint": "experiment_id, variant, user_segment"})
    if rtype == "accessibility_gap" or "accessibility" in problem or "screen reader" in problem:
        events.append({"event_name": "assistive_tech_interaction", "trigger": "Assistive tech used during payment or login flow", "properties_hint": "tech_type, flow_step, success"})
    if "checkout" in problem or "1-click" in problem or rtype == "competitive_parity":
        events.append({"event_name": "checkout_abandoned", "trigger": "User exits payment flow without completing", "properties_hint": "exit_step, payment_method, time_spent_ms"})
    if "login" in problem or "sso" in problem or "kyc" in problem:
        events.append({"event_name": "auth_failed", "trigger": "User login or KYC verification fails", "properties_hint": "auth_method, error_type, device_type"})

    return events


# ---- 3. Integrity checks ----

def _check_integrity(ctx):
    issues = []
    snapshot = ctx.get("metrics_snapshot", {})

    if not snapshot:
        issues.append({"issue": "no_metrics_snapshot", "severity": "high", "detail": "No metrics provided. Cannot set baselines for E-Wallet KPIs."})

    keys = [k.lower() for k in snapshot.keys()]
    if not any("device" in k for k in keys):
        issues.append({"issue": "missing_device_segmentation", "severity": "medium", "detail": "No device-level breakdown. Payment issues are often device-specific."})

    return issues


# ---- Main ----

def run(state):
    global _COUNTER
    _COUNTER = 0

    state.setdefault("trace", []).append("D_metrics")
    ctx = state["context_packet"]

    findings = []

    # --- snapshot/ticket/doc references for evidence + missing-metric assumptions ---
    snapshot = ctx.get("metrics_snapshot", {}) or {}
    snapshot_keys = list(snapshot.keys())

    tickets = ctx.get("normalized_tickets", []) or []
    docs = ctx.get("normalized_docs", []) or []

    ticket_id = tickets[0].get("id") if tickets else None
    doc_id = docs[0].get("id") if docs else None

    # Base evidence references (keep short and deterministic)
    evidence = [f"metric:{k}" for k in snapshot_keys[:2]]
    if ticket_id:
        evidence.append(f"ticket:{ticket_id}")
    if doc_id:
        evidence.append(f"doc:{doc_id}")
    evidence.append(f"request_type={ctx.get('request_type', '')}")

    # 1 - North Star
    rtype = ctx.get("request_type", "").lower().strip()
    framework = _FRAMEWORKS.get(rtype, _DEFAULT)

    # assumptions for framework metrics missing from snapshot
    assumptions_missing = []
    for m in framework.get("input_metrics", []):
        if m not in snapshot:
            assumptions_missing.append(
                f"Assumption: '{m}' baseline not provided in metrics_snapshot; needs instrumentation or data pull."
            )

    findings.append(_finding(
        "north_star_proposal", "high", 0.75,
        f"North Star: {framework['north_star']}. Inputs: {', '.join(framework['input_metrics'])}.",
        f"Guardrails: {'; '.join(framework['guardrails'])}.",
        evidence,
    ))
    findings[-1]["assumptions"] = assumptions_missing

    # 2 - Event taxonomy
    events = _build_events(ctx)
    findings.append(_finding(
        "event_taxonomy", "medium", 0.65,
        f"Proposed {len(events)} events: {', '.join(e['event_name'] for e in events)}.",
        "Review with eng before sprint.",
        evidence,
    ))

    # 3 - Integrity
    for issue in _check_integrity(ctx):
        findings.append(_finding(
            "metric_integrity", issue["severity"], 0.85,
            f"Integrity: {issue['issue']}",
            issue["detail"],
            [f"snapshot_keys={list(ctx.get('metrics_snapshot', {}).keys())}"],
        ))

    # Save
    payload = {
        "agent": "D_metrics",
        "findings": findings,
        "metric_framework": framework,
        "event_taxonomy": events,
        "integrity_issues": _check_integrity(ctx),
    }

    for f in findings:
        validate_json(f, "schemas/finding.schema.json")

    write_json(state["out_dir"], "findings_metrics.json", payload)
    state.setdefault("findings", {})["metrics"] = payload
    return state