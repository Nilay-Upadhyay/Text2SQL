import json
from pathlib import Path
BASE = Path("src/metadata/generated")

def load_metadata() -> tuple[str, str]:
    """Reads the raw text content of the .toon files."""
    schema_text = (BASE / "schema.toon").read_text()
    biz_dict_text = (BASE / "business_dictionary.toon").read_text()
    
    return schema_text, biz_dict_text