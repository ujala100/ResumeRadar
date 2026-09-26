"""
Strict output schema for resume-JD matching.
Every LLM response must validate against this before we accept it.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List


class MatchResult(BaseModel):
    match_score: int = Field(..., ge=0, le=100, description="Overall match score 0-100")
    top_strengths: List[str] = Field(..., min_length=1, max_length=5)
    missing_skills: List[str] = Field(default_factory=list, max_length=10)
    two_line_summary: str = Field(..., min_length=1)

    @field_validator("two_line_summary")
    @classmethod
    def summary_not_too_long(cls, v: str) -> str:
        # Enforce "two-line" loosely: cap length so it can't turn into a paragraph
        if len(v) > 400:
            raise ValueError("Summary too long - must be ~2 lines")
        return v.strip()

    @field_validator("top_strengths", "missing_skills")
    @classmethod
    def no_empty_strings(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned and v:
            raise ValueError("List items cannot be empty strings")
        return cleaned


class ErrorResult(BaseModel):
    """Returned when the pipeline fails gracefully instead of crashing."""
    error: bool = True
    reason: str
    raw_output_snippet: str = ""
