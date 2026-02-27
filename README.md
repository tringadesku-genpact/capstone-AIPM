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

If you use OpenAI later, set your key in a `.env` file (never commit this):

```env
OPENAI_API_KEY=your_key_here
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

## 5) Where outputs go

Each run is isolated in its own directory:

```
runs/
  run_.../
    (artifacts will be written here by agents)
```