import json
from pathlib import Path
import jsonschema

def validate_json(obj, schema_path):
    schema = json.loads(Path(schema_path).read_text())
    jsonschema.validate(instance=obj, schema=schema)