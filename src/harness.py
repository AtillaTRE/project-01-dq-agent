# src/harness.py

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from src.logging_config import setup_logging

logger = setup_logging(service_name="dq-harness")

# Single source of truth for the summary limit. AGENTS.md and AGENTS_cube.md
# state the same number to the model; the harness enforces it.
MAX_SUMMARY_LENGTH = 500


class DQIssue(BaseModel):
    """A single detected data quality problem."""
    severity: Literal["low", "medium", "high", "critical"]
    field:    str
    issue:    str
    count:    int = Field(..., ge=0)


class DQReport(BaseModel):
    """Required output schema of the agent."""
    table:        str
    total_rows:   int = Field(..., ge=0)
    issues:       list[DQIssue]
    summary:      str = Field(..., min_length=10, max_length=MAX_SUMMARY_LENGTH)


FORBIDDEN_KEYWORDS = [
    "DELETE", "UPDATE", "INSERT", "DROP",
    "CREATE", "ALTER", "TRUNCATE", "MERGE",
]


def sql_safety_gate(sql: str) -> dict:
    """Harness gate: block SQL that is not a read-only, bounded query.

    This is a lexical gate, not a SQL parser. See "Known limitations" in
    README.md — it is a guardrail against agent mistakes, not a substitute
    for read-only IAM credentials.
    """
    sql_upper = sql.upper().strip()

    for kw in FORBIDDEN_KEYWORDS:
        # \b matches whole words only, so a column like CREATED_AT is not a CREATE.
        if re.search(rf"\b{kw}\b", sql_upper):
            return {"allowed": False, "reason": f"{kw} not allowed"}

    # Reject statement batches: one trailing semicolon is fine, anything after it is not.
    if ";" in sql_upper.rstrip(";").rstrip():
        return {"allowed": False, "reason": "Multiple statements are not allowed"}

    # A CTE is still a read-only query, so WITH ... SELECT is accepted.
    if not sql_upper.startswith(("SELECT", "WITH")):
        return {"allowed": False, "reason": "Only SELECT (or WITH ... SELECT) is allowed"}

    if not re.search(r"\bLIMIT\s+\d+", sql_upper):
        return {"allowed": False, "reason": "LIMIT clause is required"}

    return {"allowed": True}


def _extract_json(text: str) -> str:
    """Extract the first JSON object from a text, even when surrounded by prose."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)

    # Find the first { and the last matching }
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in output")

    return text[start: end + 1]


def validate_output(raw: str) -> DQReport:
    """Parse the agent's final message and validate it against DQReport.

    An over-long summary is truncated rather than rejected: the analysis behind
    it is still sound, and rejecting would discard a complete report over prose.
    """
    try:
        json_str = _extract_json(raw)
        data = json.loads(json_str)

        summary = data.get("summary", "")
        if len(summary) > MAX_SUMMARY_LENGTH:
            logger.warning(
                "Summary truncated by harness",
                extra={
                    "original_length":  len(summary),
                    "truncated_length": MAX_SUMMARY_LENGTH,
                },
            )
            data["summary"] = summary[: MAX_SUMMARY_LENGTH - 3] + "..."

        return DQReport(**data)
    except Exception as e:
        logger.error(
            "Harness rejected output",
            extra={"raw_preview": raw[:500], "error": str(e)},
        )
        raise ValueError(f"Harness rejected output: {e}") from e
