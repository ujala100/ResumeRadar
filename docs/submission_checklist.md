# Submission Checklist

Matches the brief's "Scoring Rubric & 48-Hour Submission Protocol" exactly.

## Before you submit

- [ ] **Get a Gemini API key** at https://ai.google.dev (free tier is enough)
- [ ] Run `pip install -r requirements.txt`
- [ ] Run the test suite to confirm everything works on your machine:
      `python3 tests/test_pipeline.py` (expect 14/14 passed)
- [ ] Run the CLI against a real resume with your API key set (unset `MOCK_MODE`):
      `python3 main.py --resume your_resume.pdf --jd "paste JD text"`
- [ ] **Complete Part A of `docs/adversarial_stress_test_report.md`** — this
      requires you to actually test the two live portals
      (campus.aivilabs.com and hackmywebsite.io) yourself; I can't do this
      part for you since it needs a live account/session on those sites.
- [ ] Review `docs/system_prompt_architecture.md` — add your name/date

## Deliverable mapping (per brief)

| Brief requirement | File(s) in this project |
|---|---|
| Deliverable 01: Adversarial Stress Test | `docs/adversarial_stress_test_report.md` |
| Deliverable 02: System Prompt Architecture | `docs/system_prompt_architecture.md`, `prompt_builder.py` |
| Deliverable 03: Working Python AI Script | `main.py` + all supporting modules |
| Input: raw resume text + JD | `input_handler.py` (handles text, .txt, .pdf, scanned/OCR) |
| Output: strict JSON schema | `schema.py` (Pydantic) |
| Robust error handling / try-except / JSON sanitizing | `output_sanitizer.py`, `llm_client.py` |

## Submission steps

1. `git init && git add . && git commit -m "Resume-JD Match Engine"`
2. Push to a **public** GitHub repo (or Colab if you prefer — brief accepts either)
3. Convert `docs/adversarial_stress_test_report.md` and
   `docs/system_prompt_architecture.md` to PDF or Google Doc if the brief's
   "Format: Google Doc / PDF + GitHub / Colab Link" line requires it —
   Markdown alone may not satisfy "PDF" strictly; check with your recruiter
   if unsure.
4. Email/reply with subject line exactly as specified:
   `[AI Task Submission] - <Your Full Name> - <Phone>`
5. Include: GitHub repo link + your name + confirmation the repo is public

## Time budget suggestion (within the 48h SLA)

- Hour 0-1: Get API key, run test suite, confirm it works on your machine
- Hour 1-3: Test the two live portals manually, fill in Part A of the stress
  test report with real screenshots/outputs
- Hour 3-4: Polish docs, push to GitHub, make repo public
- Hour 4-5: Final review, submit
