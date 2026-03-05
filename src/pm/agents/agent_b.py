from __future__ import annotations

from typing import Any, Dict, List, Tuple

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
        "id": f"B-{_COUNTER:03d}",
        "agent": "B_customer",
        "type": ftype,
        "impact": impact,
        "confidence": round(float(confidence), 2),
        "summary": summary,
        "recommendation": recommendation,
        "evidence": evidence,
        "assumptions": assumptions or [],
    }


def _note_refs(notes: List[Dict[str, Any]]) -> List[str]:
    return [f"note:{i}" for i in range(1, len(notes) + 1)]


def _ticket_refs(tickets: List[Dict[str, Any]]) -> List[str]:
    refs = []
    for t in tickets:
        tid = str(t.get("id", "")).strip()
        if tid:
            refs.append(f"ticket:{tid}")
    return refs


def _classify_strength(evidence_count: int, missing_info: List[str]) -> Tuple[str, float]:
    if evidence_count >= 4 and not missing_info:
        return "Validated", 0.85
    if evidence_count >= 2:
        return "Directional", 0.70 if not missing_info else 0.65
    return "Speculative", 0.55


def _segments_from_signals(notes: List[Dict[str, Any]], tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    segments: Dict[str, Dict[str, Any]] = {}

    for n in notes:
        src = str(n.get("source", "")).strip().lower()
        if "support" in src:
            segments.setdefault("Support users", {"segment": "Support users", "signals": []})["signals"].append("support note")
        if "nps" in src:
            segments.setdefault("NPS respondents", {"segment": "NPS respondents", "signals": []})["signals"].append("nps comment")
        if "sales" in src:
            segments.setdefault("Enterprise prospects", {"segment": "Enterprise prospects", "signals": []})["signals"].append("sales input")
        if "interview" in src:
            segments.setdefault("Interview participants", {"segment": "Interview participants", "signals": []})["signals"].append("interview note")
        if "exec" in src:
            segments.setdefault("Leadership stakeholders", {"segment": "Leadership stakeholders", "signals": []})["signals"].append("exec note")

    for t in tickets:
        labels = t.get("labels", []) or []
        labels = [str(x).strip().lower() for x in labels if x is not None]
        if "mobile" in labels:
            segments.setdefault("Mobile users", {"segment": "Mobile users", "signals": []})["signals"].append("mobile-labeled ticket")
        if "accessibility" in labels or "a11y" in labels:
            segments.setdefault("Assistive-tech users", {"segment": "Assistive-tech users", "signals": []})["signals"].append("a11y-labeled ticket")
        if "pricing" in labels or "billing" in labels:
            segments.setdefault("Pricing-sensitive users", {"segment": "Pricing-sensitive users", "signals": []})["signals"].append("pricing/billing ticket")
        if "auth" in labels or "login" in labels:
            segments.setdefault("Login/SSO users", {"segment": "Login/SSO users", "signals": []})["signals"].append("auth-labeled ticket")

    if not segments:
        segments["General users"] = {"segment": "General users", "signals": ["no segment signals provided"]}

    return [segments[k] for k in sorted(segments.keys())]


def _jtbd_from_context(rtype: str, problem: str) -> List[Dict[str, str]]:
    r = (rtype or "").strip().lower()
    p = (problem or "").strip()

    if r == "metric_drop":
        return [
            {"job": "complete checkout successfully", "so_that": "I can finish my purchase without friction"},
            {"job": "log in quickly", "so_that": "I can access my account and pay without getting stuck"},
        ]
    if r == "competitive_parity":
        return [
            {"job": "pay faster with fewer steps", "so_that": "I don't switch to a competitor for convenience"},
            {"job": "trust the flow", "so_that": "I feel safe saving payment methods and completing checkout"},
        ]
    if r == "high_risk_idea":
        return [
            {"job": "control my data and consent", "so_that": "I understand and agree to tracking/personalization"},
            {"job": "get relevant offers", "so_that": "the product feels personalized without being creepy"},
        ]
    if r == "accessibility_gap":
        return [
            {"job": "use the product with assistive tech", "so_that": "I can complete the same tasks as other users"},
        ]

    return [
        {"job": "use the feature described", "so_that": f"the problem ('{p[:60]}...') is resolved" if len(p) > 60 else f"the problem ('{p}') is resolved"},
    ]


def _research_gaps(missing_info: List[str], notes: List[Dict[str, Any]], tickets: List[Dict[str, Any]]) -> List[str]:
    gaps = []
    if missing_info:
        gaps.extend(missing_info)
    if not notes:
        gaps.append("No customer notes/interviews/NPS snippets provided.")
    if not tickets:
        gaps.append("No tickets/work items provided to understand reported issues.")
    return gaps


def _minimal_validation_plan(rtype: str, gaps: List[str]) -> List[str]:
    plan = [
        "Review 5–10 recent support tickets for the same theme and tag root causes.",
        "Run 3 quick user interviews (15 min) with the affected segment(s).",
        "Confirm baseline metrics + segmentation (device, region, auth method) before making decisions.",
    ]
    if any("data_items" in g.lower() for g in gaps):
        plan.append("Define data_items (fields/purpose/retention) and consent flow with legal/privacy review.")
    if (rtype or "").lower() == "competitive_parity":
        plan.append("Collect 3 competitor examples (screenshots/links) and confirm parity scope with stakeholders.")
    return plan


def run(state: PMState) -> PMState:
    global _COUNTER
    _COUNTER = 0

    state.setdefault("trace", []).append("B_customer")

    ctx = state.get("context_packet") or {}
    notes = ctx.get("normalized_notes", []) or []
    tickets = ctx.get("normalized_tickets", []) or []
    missing_info = ctx.get("missing_info", []) or []
    rtype = str(ctx.get("request_type", "")).strip()
    problem = str(ctx.get("problem_statement", "")).strip()

    note_evs = _note_refs(notes)
    ticket_evs = _ticket_refs(tickets)
    total_evidence = len(note_evs) + len(ticket_evs)

    strength_label, base_conf = _classify_strength(total_evidence, missing_info)

    segments = _segments_from_signals(notes, tickets)
    jtbd = _jtbd_from_context(rtype, problem)

    gaps = _research_gaps(missing_info, notes, tickets)
    plan = _minimal_validation_plan(rtype, gaps)

    insights = []
    if notes:
        joined = " ".join(str(n.get("text", "")).lower() for n in notes)
        themes = []
        if any(k in joined for k in ["login", "sso", "password"]):
            themes.append("Users report login/auth friction impacting completion.")
        if any(k in joined for k in ["slow", "latency", "timeout"]):
            themes.append("Users mention slowness/latency affecting the flow.")
        if any(k in joined for k in ["privacy", "gdpr", "consent", "tracking"]):
            themes.append("Users express privacy/consent concerns about tracking.")
        if any(k in joined for k in ["pricing", "billing", "subscription"]):
            themes.append("Users are confused by pricing/subscription information.")
        if not themes:
            themes.append("Customer notes indicate friction in the described area.")
        insights.extend(themes[:2])
    elif tickets:
        insights.append("Tickets suggest work is needed in the described area, but customer notes are missing.")
    else:
        insights.append("Insufficient customer evidence provided; treat insights as speculative.")

    findings: List[Dict[str, Any]] = []

    f1_evidence = [f"request_type={rtype}"] + (note_evs[:3] + ticket_evs[:3])
    f1_assumptions = []
    if strength_label != "Validated":
        f1_assumptions.append("Limited evidence in bundle; confidence should increase after validation.")
    if missing_info:
        f1_assumptions.append("Missing-info flags may change prioritization after discovery.")

    findings.append(
        _finding(
            "customer_needs",
            "high",
            base_conf,
            f"{strength_label} insights from bundle. Key needs: " + " ".join(insights),
            "Use these needs to prioritize requirements; fill gaps with the minimal validation plan before committing to scope.",
            f1_evidence,
            f1_assumptions,
        )
    )

    seg_names = ", ".join(s["segment"] for s in segments[:5])
    jtbd_jobs = "; ".join(
        f"When I need to {j['job']}, I want to..., so that {j['so_that']}." for j in jtbd[:3]
    )
    findings.append(
        _finding(
            "segmentation_jtbd",
            "medium",
            min(base_conf, 0.8),
            f"Segments suggested from signals: {seg_names}. JTBD framing: {jtbd_jobs}",
            "Pick 1–2 primary segments and validate JTBD language with quick interviews before writing final PRD wording.",
            [f"request_type={rtype}"] + note_evs[:2] + ticket_evs[:2],
            ["Segmentation is inferred from sources/labels; validate with real user data."]
            if segments and segments[0]["signals"][0] != "no segment signals provided"
            else ["No strong segmentation signals present; treat segments as placeholders."],
        )
    )

    gap_text = "; ".join(gaps[:6]) if gaps else "No obvious research gaps detected from bundle."
    plan_text = " | ".join(plan[:6])
    findings.append(
        _finding(
            "research_gaps",
            "high" if gaps else "low",
            0.75 if gaps else 0.8,
            f"Research gaps: {gap_text}",
            f"Minimal validation plan: {plan_text}",
            [f"missing_info_count={len(missing_info)}", f"notes_count={len(notes)}", f"tickets_count={len(tickets)}"],
            [],
        )
    )

    for f in findings:
        validate_json(f, "schemas/finding.schema.json")

    output = {
        "agent": "B_customer",
        "insight_strength": strength_label,
        "segments": segments,
        "jtbd": jtbd,
        "research_gaps": gaps,
        "minimal_validation_plan": plan,
        "findings": findings,
    }

    write_json(state["out_dir"], "findings_customer.json", output)
    state.setdefault("findings", {})["customer"] = output
    return state