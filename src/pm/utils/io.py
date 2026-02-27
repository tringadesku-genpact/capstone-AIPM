import json
from pathlib import Path
import yaml

def load_json(path):
    return json.loads(Path(path).read_text())

def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2))

def load_yaml(path):
    return yaml.safe_load(Path(path).read_text())