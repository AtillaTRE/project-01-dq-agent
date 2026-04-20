# src/harness.py

import json
import re
from typing import Literal

from pydantic import BaseModel, Field


class DQIssue(BaseModel):
    """Um problema de qualidade detectado."""
    severity: Literal["low", "medium", "high", "critical"]
    field:    str
    issue:    str
    count:    int = Field(..., ge=0)


class DQReport(BaseModel):
    """Output schema obrigatório do agente."""
    table:        str
    total_rows:   int = Field(..., ge=0)
    issues:       list[DQIssue]
    summary:      str = Field(..., min_length=10, max_length=500)


FORBIDDEN_KEYWORDS = [
    "DELETE", "UPDATE", "INSERT", "DROP",
    "CREATE", "ALTER", "TRUNCATE", "MERGE",
]


def sql_safety_gate(sql: str) -> dict:
    """Harness gate: bloqueia SQL perigoso."""
    sql_upper = sql.upper()

    for kw in FORBIDDEN_KEYWORDS:
        # \b garante match de palavra inteira (não match "CREATED_AT")
        if re.search(rf"\b{kw}\b", sql_upper):
            return {"allowed": False, "reason": f"{kw} not allowed"}

    if not sql_upper.strip().startswith("SELECT"):
        return {"allowed": False, "reason": "Only SELECT is allowed"}

    if not re.search(r"\bLIMIT\s+\d+", sql_upper):
        return {"allowed": False, "reason": "LIMIT clause is required"}

    return {"allowed": True}


def _extract_json(text: str) -> str:
    """Extrai o primeiro objeto JSON de um texto, mesmo cercado de prose."""
    # Remove markdown code fences se existirem
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)

    # Acha o primeiro { e o último } correspondente
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in output")

    return text[start: end + 1]


def validate_output(raw: str) -> DQReport:
    """Harness gate: valida schema da saída final do agente."""
    try:
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        return DQReport(**data)
    except Exception as e:
        raise ValueError(f"Harness rejected output: {e}") from e
