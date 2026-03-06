# Agent F - Tech Feasibility & Delivery Agent

from typing import Any, Dict, List

from ..state import PMState
from src.pm.utils.output import write_json
from src.pm.utils.validate import validate_json


_COUNTER = 0


def _finding(
    ftype: str,
    impact: str,
    confidence: float,
    summary: str,
    recommendation: str,
    evidence: List[str],
    assumptions: List[str] | None = None,
) -> Dict[str, Any]:
    global _COUNTER
    _COUNTER += 1
    return {
        "id": f"F-{_COUNTER:03d}",
        "agent": "F_feasibility",
        "type": ftype,
        "impact": impact,
        "confidence": round(float(confidence), 2),
        "summary": summary,
        "recommendation": recommendation,
        "evidence": evidence,
        "assumptions": assumptions or [],
    }


def _evidence(ctx: Dict[str, Any]) -> List[str]:
    ev = [f"request_type={ctx.get('request_type', '')}"]

    snap = ctx.get("metrics_snapshot", {}) or {}
    for k in list(snap.keys())[:2]:
        ev.append(f"metric:{k}")

    tickets = ctx.get("normalized_tickets", []) or []
    for t in tickets[:2]:
        tid = (t or {}).get("id")
        if tid:
            ev.append(f"ticket:{tid}")

    docs = ctx.get("normalized_docs", []) or []
    if docs and (docs[0] or {}).get("id"):
        ev.append(f"doc:{docs[0]['id']}")

    return ev


def run(state: PMState) -> PMState:
    global _COUNTER
    _COUNTER = 0
    state.setdefault("trace", []).append("F_feasibility")

    ctx = state.get("context_packet")
    if not ctx:
        raise ValueError("context_packet missing from state — Agent A must run first.")

    tickets = ctx.get("normalized_tickets", []) or []
    notes = ctx.get("normalized_notes", []) or []
    docs = ctx.get("normalized_docs", []) or []
    hotspots = set(ctx.get("hotspots", []) or [])
    open_questions = ctx.get("missing_info", []) or []

    text_blob = " ".join(
        [
            str(ctx.get("problem_statement", "")),
            " ".join((t or {}).get("title", "") for t in tickets),
            " ".join((n or {}).get("text", "") for n in notes),
            " ".join((d or {}).get("snippet", "") for d in docs),
        ]
    ).lower()

    def has(words: List[str]) -> bool:
        return any(w in text_blob for w in words)

    # Signals
    signals = {
        "login_or_access": ("auth" in hotspots) or has(["login", "sso", "password", "mfa", "oauth"]),
        "privacy_or_tracking": ("privacy" in hotspots) or has(["pii", "gdpr", "consent", "tracking", "retarget", "identifier"]),
        "pricing_or_billing": ("pricing" in hotspots) or has(["pricing", "billing", "subscription", "tiers"]),
        "checkout_or_payment": has(["checkout", "payment", "1-click", "one-click"]),
        "tracking_events": has(["event", "instrument", "analytics", "taxonomy", "tracking"]),
        "accessibility": has(["accessibility", "a11y", "screen reader", "keyboard"]),
        "performance": has(["latency", "slow", "p95", "timeout", "performance"]),
    }

    # Complexity score
    score = (
        (2 if signals["login_or_access"] else 0)
        + (2 if signals["privacy_or_tracking"] else 0)
        + (1 if signals["checkout_or_payment"] else 0)
        + (1 if signals["tracking_events"] else 0)
        + (1 if signals["performance"] else 0)
        + (1 if signals["accessibility"] else 0)
        + (1 if open_questions else 0)
    )
    complexity_level = "high" if score >= 6 else ("medium" if score >= 3 else "low")

    # Dependencies
    dependencies: List[Dict[str, str]] = []

    if signals["tracking_events"]:
        dependencies.append(
            {"area": "data analytics", "dependency": "Tracking events + validation dashboards", "owner_hint": "Data Team"}
        )
    if signals["login_or_access"]:
        dependencies.append(
            {"area": "login system", "dependency": "Changes to login or single sign-on flow", "owner_hint": "Platform Team"}
        )
    if signals["privacy_or_tracking"]:
        dependencies.append(
            {"area": "privacy review", "dependency": "Consent requirements + privacy review/approval as needed", "owner_hint": "Privacy/Legal"}
        )
    if signals["checkout_or_payment"]:
        dependencies.append(
            {"area": "payment flow", "dependency": "Checkout/payment flow changes + provider constraints", "owner_hint": "Payments Team"}
        )
    if signals["accessibility"]:
        dependencies.append(
            {"area": "accessibility QA", "dependency": "Accessibility checks (keyboard + screen reader)", "owner_hint": "UX/QA"}
        )

    if not dependencies:
        dependencies.append({"area": "engineering", "dependency": "Confirm scope + estimate + integration points", "owner_hint": "Eng Lead"})

    # Constraints
    constraints: List[str] = []
    if signals["privacy_or_tracking"]:
        constraints.append("Must respect user consent and only collect the minimum needed data.")
    if signals["login_or_access"]:
        constraints.append("Login changes must not reduce security or lock users out.")
    if signals["checkout_or_payment"]:
        constraints.append("Payment changes must be reversible (feature flag + rollback).")
    if signals["accessibility"]:
        constraints.append("Key flows should remain usable with keyboard and screen reader.")
    if signals["performance"]:
        constraints.append("Do not worsen performance (watch p95 latency and errors).")

    # Phased delivery
    mvp: List[str] = []
    v1: List[str] = []
    v2: List[str] = []

    if signals["checkout_or_payment"]:
        mvp.append("Release a minimal version of the competitor feature behind a feature flag so it can be turned off quickly if needed.")
    if signals["login_or_access"]:
        mvp.append("Stabilize login issues affecting the core flow (add basic logging for failures).")
    if signals["performance"]:
        mvp.append("Fix the top performance regression and add monitoring for latency/errors.")
    if signals["privacy_or_tracking"]:
        mvp.append("Add consent prompt + keep tracking off unless user opts in; document what data is collected and why.")
    if signals["tracking_events"]:
        mvp.append("Ensure key tracking events exist for the flow (start/submit/success/failure) and validate them.")
    if signals["accessibility"]:
        mvp.append("Fix the most critical accessibility blockers for the flow (labels, keyboard navigation).")
    if not mvp:
        mvp.append("Deliver the smallest scoped fix behind a feature flag; confirm success metrics before expanding scope.")

    v1.append("Create dashboards that show key metrics by device, region, or login method.")
    if signals["checkout_or_payment"]:
        v1.append("Harden the flow: add end-to-end tests, better error recovery, and clear user messaging.")
    if signals["pricing_or_billing"]:
        v1.append("Clarify pricing/billing messaging and measure its impact on checkout completion.")
    if signals["privacy_or_tracking"]:
        v1.append("Write down retention/access rules and complete any required privacy review steps.")

    v2.append("Improve steps in the user flow and add 1 or 2 unique advantages once the competitor-matching feature is stable.")

    # Build vs buy triggers 
    build_vs_buy_triggers: List[str] = []
    if signals["privacy_or_tracking"]:
        build_vs_buy_triggers.append("If consent handling becomes complex (many regions/vendors), consider a dedicated consent tool.")
    if signals["login_or_access"]:
        build_vs_buy_triggers.append("If login changes become large, prefer a standard identity-provider login approach over building custom.")
    if signals["tracking_events"]:
        build_vs_buy_triggers.append("If tracking events become inconsistent, adopt a standard event tracking template + validation checks.")
    if not build_vs_buy_triggers:
        build_vs_buy_triggers.append("Build MVP using existing systems; consider external tools only if compliance or timeline risks become high.")

    evidence = _evidence(ctx)

    findings: List[Dict[str, Any]] = [
        _finding(
            "complexity_level",
            "high" if complexity_level == "high" else ("medium" if complexity_level == "medium" else "low"),
            0.75,
            f"Estimated implementation complexity: {complexity_level}.",
            "Confirm with engineering estimates; use this to plan sequencing and staffing.",
            evidence,
            assumptions=[f"Complexity inferred from hotspots/keywords; open_questions={len(open_questions)}."],
        ),
        _finding(
            "dependencies",
            "medium",
            0.70,
            f"Key dependencies: {', '.join(d['area'] for d in dependencies)}.",
            "Assign owners early and unblock MVP work with feature flags and rollback.",
            evidence,
            assumptions=["Dependencies inferred from signals; validate with engineering."],
        ),
        _finding(
            "phased_delivery",
            "high",
            0.72,
            f"Phased delivery proposed: MVP({len(mvp)}), V1({len(v1)}), V2({len(v2)}).",
            "Ship MVP fast with guardrails; expand scope after stability and metric integrity are confirmed.",
            evidence,
            assumptions=["Phase items are a playbook; tailor to your architecture and timeline."],
        ),
        _finding(
            "build_vs_buy_triggers",
            "low",
            0.65,
            f"Build-vs-buy triggers: {len(build_vs_buy_triggers)}.",
            "Build MVP using existing systems; consider external tools when risk or complexity becomes high.",
            evidence,
        ),
    ]

    for f in findings:
        validate_json(f, "schemas/finding.schema.json")

    output = {
        "agent": "F_feasibility",
        "complexity_level": complexity_level,
        "dependencies": dependencies,
        "constraints": constraints,         
        "open_questions": open_questions,    
        "phased_delivery": {"mvp": mvp, "v1": v1, "v2": v2},
        "build_vs_buy_triggers": build_vs_buy_triggers,
        "signals": signals,
        "findings": findings,
    }

    write_json(state["out_dir"], "findings_feasibility.json", output)
    state.setdefault("findings", {})["feasibility"] = output
    return state