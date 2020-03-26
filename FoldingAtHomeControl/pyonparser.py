"""Parse pyonmessages."""

import re
import json
from typing import Any


def convert_pyon_to_json(message: str) -> Any:
    """Converts PyON to JSON."""
    # Convert False to false
    pattern = re.compile(r"\:\s*False")
    message = re.sub(pattern, ":false", message)

    # Convert False to false
    pattern = re.compile(r"\:\s*True")
    message = re.sub(pattern, ":true", message)

    return json.loads(message)
