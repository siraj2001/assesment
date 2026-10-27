import json
from pathlib import Path
from typing import List, Dict, Any, Union

def read_json_redemption_file(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Reads JSON file containing daily partner airline mileage redemptions.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON feed not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    return []
