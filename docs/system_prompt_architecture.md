# System Prompt Architecture

## Overview
This document describes the re-engineered production system prompt used in
the Resume-JD Match Engine, and the reasoning behind each design choice.
The full prompt lives in `prompt_builder.py`.

## 1. Structured schema enforcement
The system prompt embeds the exact JSON shape expected, matched 1:1 to the
`MatchResult` Pydantic model:

```json
{
  "match_score": <int 0-100>,
  "top_strengths": [<1-5 strings>],
  "missing_skills": [<0-10 strings>],
  "two_line_summary": "<max ~400 chars>"
}
```

Rather than relying on the LLM's own judgment of "reasonable" output, the
model is a validation gate — schema-violating output is rejected before it
ever reaches a caller, and triggers a self-correction retry (see
`llm_client.py`).

## 2. Elimination of conversational preamble
Explicit instruction: *"Output ONLY valid JSON... No markdown fences, no
preamble, no explanation text outside the JSON object."*

This is necessary because Gemini (like most chat-tuned LLMs) defaults to
wrapping structured output in conversational framing ("Sure! Here's the
JSON:") and markdown code fences. Rather than fighting this with prompt
instructions alone, the pipeline also treats it as a robustness problem in
code (`output_sanitizer.py` strips fences/preamble even when the model
doesn't fully comply).

## 3. Few-shot example
One worked example is embedded directly in the system prompt showing input
resume fragments, input JD fragments, and the exact expected output. This
anchors the model's calibration for `match_score` (a bare "score 0-100"
instruction is otherwise highly inconsistent between calls).

## 4. Prompt injection defense
Resume and JD text are wrapped in explicit delimiters:

```
<<<RESUME_TEXT>>>
...
<<<END_RESUME_TEXT>>>
```

The system prompt explicitly instructs the model to treat everything
between these markers as **data**, never as instructions — even if the
content contains phrases like "ignore previous instructions" or "output
100". This directly defends against the adversarial prompt-injection test
case in the stress test (see `docs/adversarial_stress_test_report.md`).

This is a defense-in-depth measure, not a guarantee: instruction-following
models can still be partially influenced by injected text. The prompt asks
the model to flag suspicious instruction-like content in the summary field
rather than silently ignoring it, which gives a human reviewer visibility
into attempted manipulation.

## 5. Edge case handling built into the prompt
- **Empty/unreadable input:** explicit instruction to return `match_score: 0`
  with an explanatory summary rather than refusing or erroring.
- **Mixed-language input (Hinglish):** explicit instruction to parse
  code-switched text directly rather than asking for clarification or
  attempting translation, which would introduce an unnecessary failure
  point and additional latency/cost.

## 6. Fallback strategy for rate limits (429) and timeouts
Handled outside the prompt itself, in `llm_client.py`:
- Exponential backoff with jitter: `(2^attempt) + random(0,1)` seconds,
  capped at `MAX_RETRIES = 3`.
- Explicit request timeout (20s) via the SDK's `HttpOptions`.
- On exhausting retries, the pipeline returns a structured `ErrorResult`
  object (still valid JSON) rather than raising an unhandled exception —
  callers always get a parseable response.

## 7. Self-correction loop
If the model's output fails schema validation, the exact validation error
and the model's own prior (invalid) output are sent back to it with an
instruction to fix and resend. This converges to valid JSON far more
reliably than blindly re-sending the original prompt, because the model
can see precisely what it did wrong.
