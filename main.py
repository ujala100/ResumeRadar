"""
Usage:
    export GEMINI_API_KEY="your-key-here"
    python main.py --resume resume.pdf --jd jd.txt
    python main.py --resume "raw resume text..." --jd "raw jd text..."
"""

import argparse
import json
import sys

from input_handler import load_resume_text
from llm_client import get_match_result


def main():
    parser = argparse.ArgumentParser(description="Resume-JD Match Engine")
    parser.add_argument("--resume", required=True, help="Path to resume file or raw text")
    parser.add_argument("--jd", required=True, help="Path to JD file or raw text")
    args = parser.parse_args()

    try:
        resume_text = load_resume_text(args.resume)
        jd_text = load_resume_text(args.jd)  # same loader works for JD text/files

        if not resume_text.strip():
            print(json.dumps({
                "error": True,
                "reason": "Empty resume text after extraction (possible OCR/parsing failure)"
            }, indent=2))
            sys.exit(1)

        result = get_match_result(resume_text, jd_text)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": True, "reason": f"Unhandled exception: {e}"}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
