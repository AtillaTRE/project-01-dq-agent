# tests/test_harness.py

import pytest
from src.harness import sql_safety_gate, validate_output, DQReport
import json


class TestSqlSafetyGate:
    def test_allows_select_with_limit(self):
        result = sql_safety_gate("SELECT * FROM t LIMIT 100")
        assert result["allowed"] is True

    def test_blocks_delete(self):
        result = sql_safety_gate("DELETE FROM t WHERE id=1")
        assert result["allowed"] is False
        assert "DELETE" in result["reason"]

    def test_blocks_update(self):
        result = sql_safety_gate("UPDATE t SET x=1 WHERE id=2")
        assert result["allowed"] is False

    def test_blocks_drop(self):
        result = sql_safety_gate("DROP TABLE t")
        assert result["allowed"] is False

    def test_requires_limit(self):
        result = sql_safety_gate("SELECT * FROM t")
        assert result["allowed"] is False
        assert "LIMIT" in result["reason"]

    def test_blocks_delete_disguised_in_comment(self):
        # Importante: garantir que nem "SELECT ... ; DELETE" passa
        result = sql_safety_gate(
            "SELECT 1 LIMIT 1; DELETE FROM t"
        )
        assert result["allowed"] is False

    def test_allows_column_named_created(self):
        # "CREATED_AT" NÃO deve disparar o gate de "CREATE"
        result = sql_safety_gate(
            "SELECT created_at FROM t LIMIT 10"
        )
        assert result["allowed"] is True


class TestValidateOutput:
    def test_valid_report_passes(self):
        raw = json.dumps({
            "table":      "orders",
            "total_rows": 500,
            "issues": [{
                "severity": "high",
                "field":    "city",
                "issue":    "50 null values",
                "count":    50,
            }],
            "summary": "Found nulls in city field",
        })
        report = validate_output(raw)
        assert isinstance(report, DQReport)
        assert report.total_rows == 500

    def test_invalid_json_rejected(self):
        with pytest.raises(ValueError, match="rejected"):
            validate_output("not valid json {")

    def test_missing_fields_rejected(self):
        raw = json.dumps({"table": "orders"})
        with pytest.raises(ValueError, match="rejected"):
            validate_output(raw)

    def test_invalid_severity_rejected(self):
        raw = json.dumps({
            "table":      "orders",
            "total_rows": 100,
            "issues": [{
                "severity": "invalid_severity",
                "field":    "x",
                "issue":    "y",
                "count":    1,
            }],
            "summary": "test summary",
        })
        with pytest.raises(ValueError, match="rejected"):
            validate_output(raw)
