import json
from pathlib import Path
BASE = Path("src/metadata/generated")

def load_metadata() -> tuple[str | dict, str | dict]:
    """Reads the raw text content of the .toon files, with fallback to JSON.
    
    Returns:
        Tuple of (schema, business_dictionary) - each can be string or dict
    """
    schema_text = None
    biz_dict_text = None
    
    # Try loading .toon files first
    try:
        schema_path = BASE / "schema.toon"
        if schema_path.exists():
            schema_text = schema_path.read_text()
    except Exception:
        pass
    
    try:
        biz_dict_path = BASE / "business_dictionary.toon"
        if biz_dict_path.exists():
            biz_dict_text = biz_dict_path.read_text()
    except Exception:
        pass
    
    # Fall back to JSON if toon files not available or read fails
    if not schema_text:
        try:
            schema_path = BASE / "schema.json"
            if schema_path.exists():
                with open(schema_path) as f:
                    schema_text = json.dumps(json.load(f), indent=2)
        except Exception:
            schema_text = "{}"
    
    if not biz_dict_text:
        try:
            dict_path = BASE / "business_dictionary.json"
            if dict_path.exists():
                with open(dict_path) as f:
                    biz_dict_text = json.dumps(json.load(f), indent=2)
        except Exception:
            biz_dict_text = "{}"
    
    return schema_text or "{}", biz_dict_text or "{}"


def load_metadata_dict() -> tuple[dict, dict]:
    """Load schema and business dictionary as parsed dictionaries from JSON."""
    schema_dict: dict = {}
    biz_dict: dict = {}

    schema_path = BASE / "schema.json"
    if schema_path.exists():
        with open(schema_path) as f:
            schema_dict = json.load(f)

    dict_path = BASE / "business_dictionary.json"
    if dict_path.exists():
        with open(dict_path) as f:
            biz_dict = json.load(f)

    return schema_dict, biz_dict


def filter_business_dictionary(biz_dict: dict, tables: list[str]) -> dict:
    """Keep only business dictionary entries for the given tables."""
    table_set = set(tables)
    return {
        key: value
        for key, value in biz_dict.items()
        if key.split(".", 1)[0] in table_set
    }