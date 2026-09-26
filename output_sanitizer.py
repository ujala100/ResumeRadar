"""
LLMs often wrap JSON in markdown fences, add a preamble sentence, or
produce near-valid JSON with trailing commas. This module cleans that up
before we attempt strict parsing.
"""

import re
import json


def strip_markdown_fences(text: str) -> str:
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` wrappers
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_json_object(text: str) -> str:
    """
    If the model added preamble/postamble text around the JSON,
    grab the first {...} block via brace matching.
    """
    start = text.find("{")
    if start == -1:
        return text  # nothing to extract, let json.loads fail naturally

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text[start:]  # unbalanced, return what we have


def fix_trailing_commas(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)


def sanitize_and_parse(raw_text: str) -> dict:
    """
    Runs the full cleanup pipeline and returns a parsed dict.
    Raises json.JSONDecodeError if unrecoverable.
    """
    cleaned = strip_markdown_fences(raw_text)
    cleaned = extract_json_object(cleaned)
    cleaned = fix_trailing_commas(cleaned)
    return json.loads(cleaned)  # raises if still broken
