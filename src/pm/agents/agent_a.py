import re
from typing import List

from ..state import PMState
from src.pm.utils.output import write_json
from src.pm.utils.validate import validate_json


def _normalize_priority(p: str) -> str:
    p = str(p or "").lower().strip()
    if p in {"sev1", "critical", "p0"}:
        return "P0"
    if p in {"high", "p1"}:
        return "P1"
    if p in {"medium", "p2"}:
        return "P2"
    if p in {"low", "p3"}:
        return "P3"
    if p in {"p4"}:
        return "P4"
    return "P3"


def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("A_intake")

    bundle = state["bundle"]
    policy = state["policy"]

    ignore_labels = set(policy.get("ignore_rules", {}).get("ignore_labels", []))
    ignore_priorities = set(policy.get("ignore_rules", {}).get("ignore_priorities", []))
    hotspot_keywords = policy.get("hotspot_keywords", {})

    raw_tickets = bundle.get("tickets_raw", [])
    raw_notes = bundle.get("customer_notes_raw", [])
    raw_docs = bundle.get("documents_raw", [])
    metrics_snapshot = bundle.get("metrics_snapshot", {})

    normalized_tickets = []
    ignore_rules_applied = []
    seen_titles = set()

    # Normalize, ignore, remove duplicates
    for t in raw_tickets:
        ticket_id = str(t.get("id", "")).strip()
        title = str(t.get("title", "")).strip()
        priority = _normalize_priority(t.get("priority"))
        labels = t.get("labels") or []

        if isinstance(labels, str):
            labels = [x.strip() for x in labels.split(",") if x.strip()]

        if priority in ignore_priorities:
            ignore_rules_applied.append(f"ignored_ticket:{ticket_id}:priority")
            continue

        if any(l in ignore_labels for l in labels):
            ignore_rules_applied.append(f"ignored_ticket:{ticket_id}:label")
            continue

        title_key = re.sub(r"\s+", " ", title.lower())
        if title_key in seen_titles:
            ignore_rules_applied.append(f"deduped_ticket:{ticket_id}")
            continue
        seen_titles.add(title_key)

        normalized_tickets.append({
            "id": ticket_id,
            "type": str(t.get("type", "")).lower(),
            "priority": priority,
            "title": title,
            "labels": labels
        })

    # Normalize notes
    normalized_notes = [
        {
            "source": n.get("source", "unknown"),
            "text": str(n.get("text", "")).strip()
        }
        for n in raw_notes
    ]

    # Normalize docs
    normalized_docs = [
        {
            "id": d.get("id", ""),
            "title": d.get("title", ""),
            "snippet": str(d.get("text", ""))[:500]
        }
        for d in raw_docs
    ]

    # Hotspot detection
    combined_text = (
        bundle.get("problem_statement", "") + " " +
        " ".join(t.get("title", "") for t in raw_tickets) + " " +
        " ".join(n.get("text", "") for n in raw_notes) + " " +
        " ".join(d.get("text", "") for d in raw_docs)
    ).lower()

    hotspots: List[str] = []
    for tag, keywords in hotspot_keywords.items():
        if any(k.lower() in combined_text for k in keywords):
            hotspots.append(tag)

    # Missing info detection (simple rules)
    missing_info = []

    if bundle.get("request_type") == "metric_drop":
        if metrics_snapshot.get("baseline_by_device") is None:
            missing_info.append("Missing device baseline for metric drop.")

    if bundle.get("request_type") == "high_risk_idea":
        if not bundle.get("proposal_details", {}).get("data_items"):
            missing_info.append("Missing data_items for high-risk idea.")

    # Evidence index
    evidence_index = {
        "tickets": {t["id"]: t for t in normalized_tickets if t["id"]},
        "notes": {str(i): n for i, n in enumerate(normalized_notes, 1)},
        "docs": {str(i): d for i, d in enumerate(normalized_docs, 1)},
        "metrics_keys": list(metrics_snapshot.keys())
    }

    context_packet = {
        "bundle_id": bundle.get("bundle_id", ""),
        "product": bundle.get("product", {}),
        "request_type": bundle.get("request_type", ""),
        "problem_statement": bundle.get("problem_statement", ""),
        "normalized_tickets": normalized_tickets,
        "normalized_notes": normalized_notes,
        "normalized_docs": normalized_docs,
        "metrics_snapshot": metrics_snapshot,
        "hotspots": hotspots,
        "missing_info": missing_info,
        "ignore_rules_applied": ignore_rules_applied,
        "evidence_index": evidence_index
    }

    validate_json(context_packet, "schemas/context_packet.schema.json")

    write_json(state["out_dir"], "context_packet.json", context_packet)
    write_json(state["out_dir"], "evidence_index.json", evidence_index)

    state["context_packet"] = context_packet
    return state