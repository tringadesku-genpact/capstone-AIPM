"""
Agent C - Competitive & Positioning Agent

Reads:  state["context_packet"], state["bundle"]["competitor_info"], state["bundle"]["documents_raw"]
Writes: findings_competition.json
Stores: state["findings"]["competition"]
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..state import PMState
from src.pm.utils.output import write_json
from src.pm.utils.validate import validate_json


_COUNTER = 0


def _finding(ftype: str, impact: str, confidence: float, summary: str, recommendation: str, evidence: List[str]):
    global _COUNTER
    _COUNTER += 1
    return {
        "id": f"C-{_COUNTER:03d}",
        "agent": "C_competition",
        "type": ftype,
        "impact": impact,
        "confidence": round(float(confidence), 2),
        "summary": summary,
        "recommendation": recommendation,
        "evidence": evidence,
        "assumptions": [],
    }


def _extract_competitors(bundle: Dict[str, Any]) -> List[Dict[str, str]]:
    """Normalize competitor info into [{name, notes}] list."""
    raw = bundle.get("competitor_info", []) or []
    competitors: List[Dict[str, str]] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip() or "Unknown competitor"
        notes = str(c.get("notes", "")).strip()
        competitors.append({"name": name, "notes": notes})
    return competitors


def _extract_competitor_mentions_from_docs(ctx: Dict[str, Any], bundle: Dict[str, Any]) -> List[str]:
    snippets: List[str] = []

    docs_norm = ctx.get("normalized_docs", []) or []
    for d in docs_norm:
        if not isinstance(d, dict):
            continue
        doc_id = str(d.get("id", "")).strip()
        title = str(d.get("title", "")).strip()
        snip = str(d.get("snippet", "")).strip()
        if not snip and not title and not doc_id:
            continue
        shown = (snip[:180] + "...") if len(snip) > 180 else snip
        label = doc_id or "DOC"
        if title:
            snippets.append(f"doc:{label} — {title}: {shown}" if shown else f"doc:{label} — {title}")
        else:
            snippets.append(f"doc:{label} — {shown}" if shown else f"doc:{label}")
        if len(snippets) >= 5:
            return snippets

    #Fallback to raw bundle docs
    docs_raw = bundle.get("documents_raw", []) or []
    for d in docs_raw:
        if not isinstance(d, dict):
            continue
        doc_id = str(d.get("id", "")).strip()
        title = str(d.get("title", "")).strip()
        raw = str(d.get("text", "")).strip()
        if not raw and not title and not doc_id:
            continue
        shown = (raw[:180] + "...") if len(raw) > 180 else raw
        label = doc_id or "DOC"
        if title:
            snippets.append(f"doc:{label} — {title}: {shown}" if shown else f"doc:{label} — {title}")
        else:
            snippets.append(f"doc:{label} — {shown}" if shown else f"doc:{label}")
        if len(snippets) >= 5:
            break

    return snippets


def _infer_feature_gap(ctx: Dict[str, Any], competitors: List[Dict[str, str]]) -> str:
    """Simple heuristic for the main parity gap."""
    problem = str(ctx.get("problem_statement", "")).lower()
    joined = " ".join([c["notes"].lower() for c in competitors])
    if "1-click" in problem or "1 click" in problem or "one-click" in problem or "one click" in problem:
        return "1-click checkout parity"
    if "checkout" in problem:
        return "Checkout flow parity"
    if "speed" in joined:
        return "Performance + speed positioning parity"
    return "Competitive parity gap (unspecified)"


def run(state: PMState) -> PMState:
    global _COUNTER
    _COUNTER = 0

    state.setdefault("trace", []).append("C_competition")

    ctx = state["context_packet"]
    bundle = state.get("bundle", {}) or {}

    request_type = str(ctx.get("request_type", "")).strip()
    product = ctx.get("product", {}) or {}
    product_name = product.get("name", "Product")

    competitors = _extract_competitors(bundle)
    doc_snippets = _extract_competitor_mentions_from_docs(ctx, bundle)
    doc_snippets = list(dict.fromkeys(doc_snippets)) #dedupe

    findings: List[Dict[str, Any]] = []

    # ---- C-001: Competitive snapshot ----
    if competitors:
        comp_names = ", ".join(c["name"] for c in competitors)
        key_notes = "; ".join(
            f"{c['name']}: {c['notes']}" for c in competitors if c.get("notes")
        )
        summary = f"Identified {len(competitors)} competitor(s): {comp_names}."
        if key_notes:
            summary += f" Notes: {key_notes}"
        findings.append(_finding(
            "competitive_snapshot",
            "medium",
            0.75,
            summary,
            "Confirm the competitor claims with a quick source check and align on what 'parity' means (feature vs UX vs speed).",
            [f"request_type={request_type}"] + ([doc_snippets[0]] if doc_snippets else []),
        ))
        findings[-1]["assumptions"] = ["Competitor claims are based on bundle inputs and are not independently verified."]
    else:
        findings.append(_finding(
            "competitive_snapshot",
            "high",
            0.55,
            "No competitor_info provided in the bundle, so competitive analysis is low-confidence.",
            "Add at least 1 competitor entry (name + notes + link/source) to enable parity/differentiation analysis.",
            [f"request_type={request_type}"],
        ))

    # ---- C-002: Parity gap ----
    gap = _infer_feature_gap(ctx, competitors)
    findings.append(_finding(
        "parity_gap",
        "high" if request_type == "competitive_parity" else "medium",
        0.7,
        f"Primary parity gap for {product_name}: {gap}.",
        "Define the minimum parity scope (MVP) and success criteria (adoption + checkout completion), then implement behind a feature flag.",
        [f"problem_statement={str(ctx.get('problem_statement',''))[:120]}"],
    ))
    findings[-1]["assumptions"] = ["Parity gap inferred from keywords in the problem statement and competitor notes; validate scope with stakeholders."]

    # ---- C-003: Differentiation opportunities ----
    # Heuristic: if competitor messaging is "speed", suggest trust + control + accessibility differentiation.
    comp_text = " ".join(c["notes"].lower() for c in competitors)
    diffs = []
    if "speed" in comp_text or "fast" in comp_text:
        diffs.append("Differentiate on trust: clearer receipts, dispute flow, and transparency on fees.")
        diffs.append("Differentiate on control: easy management of saved payment methods and limits.")
    diffs.append("Differentiate on reliability: fewer checkout failures and better error recovery.")
    diffs.append("Differentiate on accessibility: ensure checkout meets a11y standards (screen reader + keyboard).")

    findings.append(_finding(
        "differentiation",
        "medium",
        0.65,
        f"Suggested differentiation angles: " + " ".join(diffs),
        "Pick 1–2 differentiation pillars to ship alongside parity (or immediately after MVP) to avoid a pure copycat release.",
        [c["name"] for c in competitors[:3]] if competitors else ["no_competitors"],
    ))
    findings[-1]["assumptions"] = ["Differentiation angles are heuristic suggestions; validate with customer research and product strategy."]

    # ---- C-004: Positioning recommendation ----
    positioning = [
        "Speed (reduced steps to complete checkout)",
        "Reliability (higher completion rate, fewer failures)",
        "Trust (transparent fees + easy dispute/refund path)",
    ]
    findings.append(_finding(
        "positioning",
        "medium",
        0.6,
        f"Positioning pillars for {product_name}: " + "; ".join(positioning) + ".",
        "Align product marketing copy and in-app messaging to these pillars; measure lift on checkout completion and churn to competitor.",
        doc_snippets if doc_snippets else [f"request_type={request_type}"],
    ))
    findings[-1]["assumptions"] = ["Positioning pillars are proposed heuristically; validate with marketing and customer insights."]

    # Validate each finding against schema
    for f in findings:
        validate_json(f, "schemas/finding.schema.json")

    output = {
        "agent": "C_competition",
        "competitors": competitors,
        "doc_snippets": doc_snippets,
        "findings": findings,
        "parity_gap": gap,
    }

    write_json(state["out_dir"], "findings_competition.json", output)

    state.setdefault("findings", {})
    state["findings"]["competition"] = output

    return state