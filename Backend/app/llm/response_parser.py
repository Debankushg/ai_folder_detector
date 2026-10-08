"""Pull the JSON object out of an LLM text reply."""
import json
import re


def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON in model reply")
    return json.loads(m.group(0))
