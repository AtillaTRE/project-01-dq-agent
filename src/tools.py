# src/tools.py

import time

from google.cloud import bigquery
from langchain_core.tools import tool

from src.config import settings
from src.harness import sql_safety_gate
from src.logging_config import setup_logging

logger = setup_logging(service_name="dq-agent-tools")
bq_client = bigquery.Client(project=settings.google_cloud_project)


@tool
def get_table_schema(dataset: str, table: str) -> str:
    """Returns the schema of a BigQuery table."""
    start = time.time()
    try:
        ref = bq_client.get_table(f"{dataset}.{table}")
        result = str([
            {"name": f.name, "type": f.field_type, "mode": f.mode}
            for f in ref.schema
        ])
        logger.info(
            "Schema fetched",
            extra={
                "table":       f"{dataset}.{table}",
                "columns":     len(ref.schema),
                "duration_ms": int((time.time() - start) * 1000),
            },
        )
        return result
    except Exception as e:
        logger.error(
            "Schema fetch failed",
            extra={"table": f"{dataset}.{table}", "error": str(e)},
        )
        return f"ERROR: {e}"


@tool
def run_bq_query(sql: str) -> str:
    """Executes a SELECT query on BigQuery. Harness enforces safety."""
    gate_result = sql_safety_gate(sql)
    if not gate_result["allowed"]:
        logger.warning(
            "Query blocked by harness",
            extra={"reason": gate_result["reason"], "sql": sql[:200]},
        )
        return f"BLOCKED BY HARNESS: {gate_result['reason']}"

    start = time.time()
    try:
        job = bq_client.query(sql)
        rows = list(job.result())[:settings.max_query_rows]

        logger.info(
            "Query executed",
            extra={
                "rows_returned":   len(rows),
                "bytes_processed": job.total_bytes_processed,
                "duration_ms":     int((time.time() - start) * 1000),
            },
        )
        return str([dict(r) for r in rows])
    except Exception as e:
        logger.error("Query failed", extra={"sql": sql[:200], "error": str(e)})
        return f"ERROR: {e}"
