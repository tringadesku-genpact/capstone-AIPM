"""
Agent E – UX & Requirements Agent

Reads the context packet from Agent A and converts tickets/notes
into requirements, acceptance criteria, edge cases, and backlog items.

Output: findings_requirements.json
"""

from ..state import PMState
from src.pm.utils.output import write_json
from src.pm.utils.validate import validate_json


# ---- User journey per request type (used for E-001 finding) ------------

_JOURNEYS = {
    "metric_drop": [
        "User opens Smart E-Wallet on mobile",
        "User attempts login (SSO or email/password)",
        "User reaches checkout or payment screen",
        "User initiates payment",
        "Payment succeeds or fails — conversion recorded",
    ],
    "competitive_parity": [
        "User discovers a feature gap vs. a competitor wallet",
        "User attempts to use the missing feature in Smart E-Wallet",
        "User abandons flow or finds a workaround",
        "User either completes payment or churns to competitor",
    ],
    "high_risk_idea": [
        "User is bucketed into experiment variant",
        "User interacts with the new feature/flow",
        "User completes or abandons the action",
        "System records outcome for statistical analysis",
    ],
    "accessibility_gap": [
        "User with assistive technology opens Smart E-Wallet",
        "User navigates to login or payment flow",
        "User encounters an accessibility barrier",
        "User succeeds, retries, or abandons the flow",
    ],
}

_DEFAULT_JOURNEY = [
    "User opens Smart E-Wallet",
    "User navigates to the relevant feature",
    "User completes or abandons the action",
]


# ---- Main ---------------------------------------------------------------

def run(state: PMState) -> PMState:
    state.setdefault("trace", []).append("E_requirements")

    cp = state.get("context_packet")
    if not cp:
        raise ValueError("context_packet missing from state — Agent A must run first.")

    tickets = cp.get("normalized_tickets", [])
    hotspots = cp.get("hotspots", [])
    rtype = cp.get("request_type", "")
    product_name = cp.get("product", {}).get("name", "Product")
    missing_info = cp.get("missing_info", [])

    # ---- Step 1: Build one requirement per ticket -----------------------
    requirements = []
    for i, t in enumerate(tickets, 1):
        req = {
            "req_id": f"REQ-{i:03d}",
            "title": t["title"],
            "priority": t.get("priority", "P2"),
            "acceptance_criteria": [
                f"The issue described in {t['id']} is resolved.",
                f"Regression test for {t['id']} passes.",
            ],
            "edge_cases": _edge_cases_for(t),
            "source_ticket": t["id"],
        }
        requirements.append(req)

    # ---- Step 1b: Gap-fix requirement from missing_info -----------------
    i = len(requirements)
    for gap in missing_info:
        i += 1
        req = {
            "req_id": f"REQ-{i:03d}",
            "title": f"Resolve missing information: {gap}",
            "priority": "P1",
            "acceptance_criteria": [
                f"The gap '{gap}' is documented and resolved before sprint start.",
            ],
            "edge_cases": ["Gap cannot be resolved — escalate to PM lead."],
            "source_ticket": None,
        }
        requirements.append(req)

    # ---- Step 2: Add non-functional reqs from hotspots ------------------
    if "privacy" in hotspots:
        requirements.append({
            "req_id": "REQ-NF-PRIV",
            "title": "PII handling must comply with privacy policy",
            "priority": "P0",
            "acceptance_criteria": [
                "PII is encrypted at rest and in transit.",
                "User consent is collected before new data processing.",
            ],
            "edge_cases": ["User revokes consent mid-session"],
            "source_ticket": None,
        })

    if "auth" in hotspots:
        requirements.append({
            "req_id": "REQ-NF-AUTH",
            "title": "Login flow must be reliable and secure",
            "priority": "P0",
            "acceptance_criteria": [
                "Login completes within 3 seconds.",
                "Failed attempts are rate-limited after 5 tries.",
            ],
            "edge_cases": ["User with MFA follows different sub-flow"],
            "source_ticket": None,
        })

    # ---- Step 3: Build backlog items from requirements ------------------
    backlog = []
    for req in requirements:
        backlog.append({
            "backlog_id": req["req_id"].replace("REQ", "BLI"),
            "title": req["title"],
            "priority": req["priority"],
            "acceptance_criteria": req["acceptance_criteria"],
            "definition_of_done": (
                f"All acceptance criteria for {req['req_id']} pass in QA. "
                f"No open P0/P1 bugs. Release notes updated."
            ),
        })

    # ---- Step 4: Create findings (matches finding.schema.json) ----------
    journey_steps = _JOURNEYS.get(rtype, _DEFAULT_JOURNEY)
    source_ticket_refs = [f"ticket:{r['source_ticket']}" for r in requirements if r["source_ticket"]]
    evidence_base = source_ticket_refs or [f"request_type={rtype}"]

    findings = [
        {
            "id": "E-001",
            "agent": "E_requirements",
            "type": "user_journey",
            "impact": "high",
            "confidence": 0.80,
            "summary": f"Primary user journey for '{rtype}': {' → '.join(journey_steps)}.",
            "recommendation": "Validate this journey with UX before sprint planning.",
            "evidence": [f"request_type={rtype}"],
            "assumptions": ["Journey derived from request type; no direct user research data in bundle."],
        },
        {
            "id": "E-002",
            "agent": "E_requirements",
            "type": "requirements_summary",
            "impact": "high",
            "confidence": 0.80,
            "summary": (
                f"Produced {len(requirements)} requirement(s) and "
                f"{len(backlog)} backlog item(s) for {product_name}."
            ),
            "recommendation": "Review acceptance criteria with engineering before sprint planning.",
            "evidence": evidence_base,
            "assumptions": [
                "Requirements are derived from tickets and hotspots, not direct user research.",
                "Story sizing is not included; estimation session still needed.",
                f"{len(missing_info)} missing-info flag(s) converted to gap-fix requirements." if missing_info else "No missing-info flags in this bundle.",
            ],
        },
    ]

    for f in findings:
        validate_json(f, "schemas/finding.schema.json")

    # ---- Step 5: Write output file --------------------------------------
    output = {
        "agent": "E_requirements",
        "requirements": requirements,
        "backlog": backlog,
        "findings": findings,
        "user_journey": journey_steps,
    }

    write_json(state["out_dir"], "findings_requirements.json", output)

    # ---- Step 6: Store in shared state ----------------------------------
    state.setdefault("findings", {})
    state["findings"]["requirements"] = output

    return state


# ---- PRD section template (called by Agent H) ---------------------------

def build_prd_requirements_section(requirements: list) -> str:
    """
    Format Agent E's requirements + acceptance criteria into a PRD markdown section.
    Agent H splices the returned string into prd.md.
    """
    if not requirements:
        return "## Requirements\n\n_No requirements generated._\n"

    lines = ["## Requirements\n"]
    for req in requirements:
        priority = req.get("priority", "P2")
        lines.append(f"### {req['req_id']} — {req['title']} `[{priority}]`\n")

        acs = req.get("acceptance_criteria", [])
        if acs:
            lines.append("**Acceptance Criteria**\n")
            lines.extend(f"- {ac}" for ac in acs)
            lines.append("")

        edges = req.get("edge_cases", [])
        if edges:
            lines.append("**Edge Cases**\n")
            lines.extend(f"- {e}" for e in edges)
            lines.append("")

        source = req.get("source_ticket")
        if source:
            lines.append(f"_Source: `{source}`_\n")

    return "\n".join(lines)


# ---- Helper: pick edge cases based on ticket labels ---------------------

def _edge_cases_for(ticket):
    """Return edge cases based on the ticket's labels."""
    labels = set(ticket.get("labels", []))
    edges = []

    if labels & {"accessibility", "a11y"}:
        edges.append("Screen reader announces all interactive elements")
        edges.append("Keyboard-only user can complete the full flow")

    if labels & {"auth", "login"}:
        edges.append("Expired credentials show a clear recovery path")

    if labels & {"checkout", "payment"}:
        edges.append("Payment timeout leaves no orphan charges")

    if labels & {"pii", "gdpr", "tracking", "privacy"}:
        edges.append("GDPR user triggers consent collection first")

    if not edges:
        edges.append("Unexpected input returns a user-friendly error")

    return edges
