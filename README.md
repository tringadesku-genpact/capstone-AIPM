# capstone-AIPM
Genpact Capstone Project - Autonomous AI Product Manager


# Setup & Run (Demo)

This project uses a **virtual environment** and a **CLI runner** to execute a demo Product Bundle through the LangGraph pipeline.

---

## 1) Create a virtual environment

### Windows (PowerShell)
```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

---

## 2) Install dependencies

From the project root (where `requirements.txt` is):

```bash
pip install -r requirements.txt
```

---

## 3) (Optional) Environment variables

If you use GitHub later, set your token in a `.env` file (never commit this):

```env
GITHUB_TOKEN=your_key_here
```

We also keep a `.env.example` as a template.

---

## 4) Run the demo

Your demo bundles live in the `demo/` folder. Example:

```bash
python run.py --bundle demo/metric_drop.json --policy policies/default.yaml
```

Expected output:
- A new folder is created under `runs/` (example: `runs/run_YYYYMMDD_HHMMSS_abcd/`)
- Console prints `Run complete: ...`

---

## 5) Run the Streamlit UI (Optional)

Instead of running the pipeline through the CLI, you can use a simple **Streamlit interface** to upload bundles and view generated artifacts.

Start the UI from the project root:

```bash
streamlit run app.py
```

Once started, your browser will open automatically (usually at `http://localhost:8501`).

From the UI you can:

- Upload a **bundle JSON**
- Run the **PM pipeline**
- View generated outputs:
  - Final Plan
  - PRD
  - Roadmap
  - Decision Log
  - Experiment Plan
  - Backlog CSV

This provides a quick way to **demonstrate the full pipeline without using CLI commands**.

---

## 6) GitHub Issue Integration (Optional)

The pipeline can automatically create a **GitHub Issue summarizing the analysis** after a run.

This requires a **GitHub Personal Access Token**.

---

## 7) Where outputs go

Each run is isolated in its own directory:

```
runs/
  run_.../
    (artifacts will be written here by agents)
```