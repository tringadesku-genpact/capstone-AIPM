from pathlib import Path
import json


def write_json(out_dir: str, filename: str, data):
    # Write JSON file inside the run folder
    path = Path(out_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_text(out_dir: str, filename: str, text: str):
    # Write text/markdown file inside the run folder
    path = Path(out_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)