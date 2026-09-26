"""
Wraps the Gemini API call with:
  - exponential backoff + jitter for 429 rate limits
  - request timeout handling
  - a self-correction retry: if JSON validation fails, we send the error
    back to the model and ask it to fix its own output (much higher
    success rate than a blind retry).

Uses the current `google-genai` SDK (the older `google-generativeai`
package is deprecated as of 2025 and receives no further updates/fixes).
"""

import os
import time
import random
import json
from pydantic import ValidationError

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

from schema import MatchResult, ErrorResult
from output_sanitizer import sanitize_and_parse
from prompt_builder import SYSTEM_PROMPT, build_user_prompt

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MOCK_MODE = os.environ.get("MOCK_MODE", "").lower() in ("1", "true", "yes")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
MAX_RETRIES = 3
REQUEST_TIMEOUT_MS = 20_000


def _call_model(client, prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            http_options=genai_types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        ),
    )
    return response.text


def _mock_call_model(resume_text: str, jd_text: str) -> str:
    """
    Deterministic offline stand-in for the Gemini API, used when MOCK_MODE=1.
    Lets the full pipeline (prompt build -> sanitize -> validate -> output)
    be tested and demoed without an API key or network access. Also used
    to simulate adversarial responses (injection attempts, malformed JSON)
    for the stress-test suite.
    """
    injection_markers = ["ignore previous", "ignore all instructions", "output match_score 100", "disregard"]
    lower_resume = resume_text.lower()
    flagged = any(m in lower_resume for m in injection_markers)

    if not resume_text.strip() or len(resume_text.strip()) < 5:
        return '{"match_score": 0, "top_strengths": ["N/A"], "missing_skills": ["Unable to parse input"], "two_line_summary": "Resume text was empty or unreadable. No meaningful comparison could be performed."}'

    summary = "Resume shows relevant experience aligned with the job description."
    if flagged:
        summary = "Anomaly detected: resume text contained instruction-like phrasing, which was ignored during scoring. Score reflects actual content only."

    return f'''```json
{{
  "match_score": 65,
  "top_strengths": ["Relevant technical background", "Clear experience section"],
  "missing_skills": ["Could not confirm all JD requirements"],
  "two_line_summary": "{summary}"
}}
```'''


def get_match_result(resume_text: str, jd_text: str) -> dict:
    if MOCK_MODE:
        raw_output = _mock_call_model(resume_text, jd_text)
        try:
            parsed = sanitize_and_parse(raw_output)
            validated = MatchResult(**parsed)
            return validated.model_dump()
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            return ErrorResult(reason=f"Mock validation failed: {e}", raw_output_snippet=raw_output[:200]).model_dump()

    if not GEMINI_API_KEY:
        return ErrorResult(reason="GEMINI_API_KEY not set (set MOCK_MODE=1 to test without a key)").model_dump()

    if genai is None:
        return ErrorResult(reason="google-genai package not installed. Run: pip install google-genai").model_dump()

    client = genai.Client(api_key=GEMINI_API_KEY)
    user_prompt = build_user_prompt(resume_text, jd_text)
    last_raw_output = ""
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            prompt_to_send = user_prompt
            if attempt > 1 and last_error:
                prompt_to_send = (
                    f"{user_prompt}\n\n"
                    f"NOTE: Your previous response failed validation with error: "
                    f"'{last_error}'. Your previous output was:\n{last_raw_output}\n"
                    f"Fix it and return ONLY corrected valid JSON."
                )

            raw_output = _call_model(client, prompt_to_send)
            last_raw_output = raw_output

            parsed = sanitize_and_parse(raw_output)
            validated = MatchResult(**parsed)
            return validated.model_dump()

        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_error = str(e)
            continue  # retry with self-correction prompt

        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate" in err_str.lower()
            is_timeout = "timeout" in err_str.lower() or "deadline" in err_str.lower()
            is_overloaded = "503" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower()

            if (is_rate_limit or is_timeout or is_overloaded) and attempt < MAX_RETRIES:
                backoff = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(backoff)
                continue
            else:
                return ErrorResult(
                    reason=f"API error after {attempt} attempt(s): {err_str}",
                    raw_output_snippet=last_raw_output[:200],
                ).model_dump()

    return ErrorResult(
        reason=f"Failed schema validation after {MAX_RETRIES} attempts: {last_error}",
        raw_output_snippet=last_raw_output[:200],
    ).model_dump()
