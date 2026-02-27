# CONTRACTS.md — Team Working Agreements
These rules prevent merge conflicts and keep the pipeline **deterministic, auditable, and consistent** across all agents.

---

## 1) “Do not change” files without team agreement

These files are shared contracts. If you must change them, agree as a team first:

- `schemas/bundle.schema.json`
- `schemas/context_packet.schema.json`
- `schemas/finding.schema.json`

Reason: if one person changes schemas, everyone else breaks.

---

## 2) Output filenames (must match)

Each agent writes **exactly** one primary file into the run folder (`state["out_dir"]`):

- Agent A → `context_packet.json` (and optionally `evidence_index.json`)
- Agent B → `findings_customer.json`
- Agent C → `findings_competition.json`
- Agent D → `findings_metrics.json`
- Agent E → `findings_requirements.json`
- Agent F → `findings_feasibility.json`
- Agent G → `findings_risk.json`

Agent H outputs:
- `final_plan.json`
- `prd.md`
- `roadmap.json`
- `experiment_plan.md`
- `decision_log.md`
- `backlog.csv`

---

## 3) State mutation rules (dict-state)

✅ Allowed:
- Read from `state["context_packet"]`
- Read policy from `state["policy"]`
- Store your results under `state["findings"][<agent_name>]`

❌ Not allowed:
- Returning a new dict that drops keys
- Overwriting other agent outputs
- Writing outside `state["out_dir"]`

Correct pattern:
```python
def run(state):
    state.setdefault("findings", {})
    state["findings"]["customer"] = {...}
    return state
```

---

## 4) Always write artifacts using shared output helpers

Use `src/pm/utils/output.py`:
- `write_json(state["out_dir"], "file.json", data)`
- `write_text(state["out_dir"], "file.md", text)`

---

## 5) Determinism rules (when LLM is added)

- Use `temperature=0`
- Label assumptions explicitly
- Provide evidence pointers (ticket IDs, doc IDs, metric keys)

---

## 6) Git hygiene

Do not commit:
- `.env`
- `.venv/`
- `runs/`


