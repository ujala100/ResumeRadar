"""
Automated test suite. Run with: python -m pytest tests/ -v
Or standalone: python tests/test_pipeline.py

Covers:
  - Schema validation (valid + invalid cases)
  - Output sanitizer (markdown fences, trailing commas, preamble text)
  - Full pipeline in MOCK_MODE against all adversarial sample files
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["MOCK_MODE"] = "1"

from pydantic import ValidationError
from schema import MatchResult
from output_sanitizer import sanitize_and_parse, strip_markdown_fences, fix_trailing_commas
from input_handler import load_resume_text
from llm_client import get_match_result

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


def test_schema_valid():
    print("\n== Schema: valid input ==")
    result = MatchResult(
        match_score=80,
        top_strengths=["Python", "Django"],
        missing_skills=["AWS"],
        two_line_summary="Good match overall.",
    )
    check("accepts valid data", result.match_score == 80)


def test_schema_rejects_out_of_range_score():
    print("\n== Schema: rejects invalid score ==")
    try:
        MatchResult(match_score=150, top_strengths=["x"], missing_skills=[], two_line_summary="test")
        check("rejects score > 100", False)
    except ValidationError:
        check("rejects score > 100", True)


def test_schema_rejects_empty_strengths():
    print("\n== Schema: rejects empty top_strengths ==")
    try:
        MatchResult(match_score=50, top_strengths=[], missing_skills=[], two_line_summary="test")
        check("rejects empty top_strengths list", False)
    except ValidationError:
        check("rejects empty top_strengths list", True)


def test_sanitizer_markdown_fences():
    print("\n== Sanitizer: markdown fences ==")
    raw = '```json\n{"a": 1}\n```'
    cleaned = strip_markdown_fences(raw)
    check("strips ```json fences", cleaned == '{"a": 1}')


def test_sanitizer_trailing_comma():
    print("\n== Sanitizer: trailing commas ==")
    raw = '{"a": 1, "b": [1, 2,],}'
    cleaned = fix_trailing_commas(raw)
    check("fixes trailing commas", json.loads(cleaned) == {"a": 1, "b": [1, 2]})


def test_sanitizer_preamble_text():
    print("\n== Sanitizer: preamble text before JSON ==")
    raw = 'Sure! Here is the result:\n{"a": 1, "b": 2}\nLet me know if you need anything else.'
    parsed = sanitize_and_parse(raw)
    check("extracts JSON despite preamble/postamble", parsed == {"a": 1, "b": 2})


def test_full_pipeline_normal_resume():
    print("\n== End-to-end: normal resume ==")
    resume = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "resume_normal.txt"))
    jd = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "jd_backend_developer.txt"))
    result = get_match_result(resume, jd)
    check("returns a match_score field", "match_score" in result)
    check("no error on clean input", "error" not in result)


def test_full_pipeline_injection_attack():
    print("\n== End-to-end: prompt injection adversarial case ==")
    resume = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "resume_injection_attack.txt"))
    jd = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "jd_backend_developer.txt"))
    result = get_match_result(resume, jd)
    check("does NOT blindly return match_score 100 from injected instruction", result.get("match_score") != 100)
    check("pipeline returns valid schema despite injection attempt", "match_score" in result)


def test_full_pipeline_hinglish():
    print("\n== End-to-end: Hinglish / code-switched resume ==")
    resume = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "resume_hinglish.txt"))
    jd = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "jd_backend_developer.txt"))
    result = get_match_result(resume, jd)
    check("processes mixed-language input without crashing", "match_score" in result)


def test_full_pipeline_garbled_input():
    print("\n== End-to-end: garbled/unreadable OCR-like input ==")
    resume = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "resume_garbled_ocr.txt"))
    jd = load_resume_text(os.path.join(os.path.dirname(__file__), "..", "sample_data", "jd_backend_developer.txt"))
    result = get_match_result(resume, jd)
    check("handles garbled input without crashing", "match_score" in result or "error" in result)


def test_full_pipeline_empty_input():
    print("\n== End-to-end: completely empty resume ==")
    result = get_match_result("", "Some JD text")
    check("handles empty resume gracefully", "match_score" in result or "error" in result)
    if "match_score" in result:
        check("empty input scores 0", result["match_score"] == 0)


if __name__ == "__main__":
    test_schema_valid()
    test_schema_rejects_out_of_range_score()
    test_schema_rejects_empty_strengths()
    test_sanitizer_markdown_fences()
    test_sanitizer_trailing_comma()
    test_sanitizer_preamble_text()
    test_full_pipeline_normal_resume()
    test_full_pipeline_injection_attack()
    test_full_pipeline_hinglish()
    test_full_pipeline_garbled_input()
    test_full_pipeline_empty_input()

    print(f"\n{'='*50}")
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    print(f"{'='*50}")
    sys.exit(1 if FAIL > 0 else 0)
