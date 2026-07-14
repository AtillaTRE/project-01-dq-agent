# tests/test_harness.py

import json

import pytest

from src.harness import MAX_SUMMARY_LENGTH, DQReport, sql_safety_gate, validate_output


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

    def test_blocks_statement_appended_after_select(self):
        # "SELECT ... ; DELETE" must not slip through
        result = sql_safety_gate(
            "SELECT 1 LIMIT 1; DELETE FROM t"
        )
        assert result["allowed"] is False

    def test_blocks_multiple_statements(self):
        # Batched statements are rejected even when every statement is a SELECT
        result = sql_safety_gate(
            "SELECT 1 LIMIT 1; SELECT 2 LIMIT 1"
        )
        assert result["allowed"] is False
        assert "Multiple statements" in result["reason"]

    def test_allows_trailing_semicolon(self):
        result = sql_safety_gate("SELECT * FROM t LIMIT 10;")
        assert result["allowed"] is True

    def test_allows_column_named_created(self):
        # "CREATED_AT" must NOT trigger the "CREATE" gate
        result = sql_safety_gate(
            "SELECT created_at FROM t LIMIT 10"
        )
        assert result["allowed"] is True

    def test_blocks_non_select_statement(self):
        # No forbidden keyword, but still not a read query
        result = sql_safety_gate("EXPLAIN SELECT 1 LIMIT 1")
        assert result["allowed"] is False
        assert "Only SELECT" in result["reason"]

    def test_allows_cte(self):
        # A WITH ... SELECT is still read-only and must be allowed
        result = sql_safety_gate(
            "WITH nulls AS (SELECT city FROM t WHERE city IS NULL) "
            "SELECT COUNT(*) FROM nulls LIMIT 10"
        )
        assert result["allowed"] is True

    def test_blocks_cte_wrapping_a_write(self):
        result = sql_safety_gate(
            "WITH x AS (SELECT 1) DELETE FROM t LIMIT 1"
        )
        assert result["allowed"] is False


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

    def test_long_summary_is_truncated_not_rejected(self):
        raw = json.dumps({
            "table":      "orders",
            "total_rows": 100,
            "issues":     [],
            "summary":    "x" * (MAX_SUMMARY_LENGTH + 200),
        })
        report = validate_output(raw)
        assert len(report.summary) == MAX_SUMMARY_LENGTH
        assert report.summary.endswith("...")

    def test_json_wrapped_in_markdown_fences_is_accepted(self):
        raw = (
            "Here is the report:\n```json\n"
            + json.dumps({
                "table":      "orders",
                "total_rows": 10,
                "issues":     [],
                "summary":    "No issues found in this table",
            })
            + "\n```\n"
        )
        report = validate_output(raw)
        assert isinstance(report, DQReport)
        assert report.total_rows == 10
