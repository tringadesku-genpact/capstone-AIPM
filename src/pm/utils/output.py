from pathlib import Path
import csv
import json


def write_json(out_dir: str, filename: str, data):
    # Write JSON file inside the run folder
    path = Path(out_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(out_dir: str, filename: str, text: str):
    # Write text/markdown file inside the run folder
    path = Path(out_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_csv(out_dir: str, filename: str, rows: list):
    # Write a list of dicts as a CSV file inside the run folder
    path = Path(out_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)