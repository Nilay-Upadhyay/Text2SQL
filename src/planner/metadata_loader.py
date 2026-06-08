import json
from pathlib import Path

BASE = Path("src/metadata/generated")


def load_metadata():
    return {
        "schema": json.loads(
            (BASE / "schema.json").read_text()
        ),
        "business_dictionary": json.loads(
            (BASE / "business_dictionary.json").read_text()
        ),
        "joins": json.loads(
            (BASE / "join_dictionary.json").read_text()
        ),
        "patterns": json.loads(
            (BASE / "query_patterns.json").read_text()
        ),
    }