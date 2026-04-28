# src/cube_tools.py
# Agent tools that talk to Cube.

from langchain_core.tools import tool
from src.cube_client import cube_client
from src.cube_harness import validate_cube_query
from src.logging_config import setup_logging
import json

logger = setup_logging(service_name="cube-tools")


@tool
def list_cube_metrics() -> str:
    """List all measures, dimensions and views available in the
    Cube semantic layer. ALWAYS use this before running queries to
    discover which metrics exist and their descriptions."""
    try:
        meta = cube_client.meta()
    except Exception as e:
        logger.error("Failed to fetch meta", extra={"error": str(e)})
        return f"ERROR: {e}"

    summary = []

    for cube_obj in meta.get("cubes", []):
        if not cube_obj.get("public", True):
            continue  # skip private cubes

        item = {
            "name":        cube_obj["name"],
            "type":        cube_obj.get("type", "cube"),
            "description": cube_obj.get("description", ""),
            "measures": [
                {
                    "name":        m["name"],
                    "title":       m.get("title", ""),
                    "description": m.get("description", ""),
                    "type":        m.get("type", ""),
                }
                for m in cube_obj.get("measures", [])
            ],
            "dimensions": [
                {
                    "name":        d["name"],
                    "title":       d.get("title", ""),
                    "description": d.get("description", ""),
                    "type":        d.get("type", ""),
                }
                for d in cube_obj.get("dimensions", [])
            ],
        }
        summary.append(item)

    return json.dumps(summary, indent=2, ensure_ascii=False)


@tool
def query_cube(
    measures: list[str],
    dimensions: list[str] | None = None,
    filters: list[dict] | None = None,
    time_dimensions: list[dict] | None = None,
    limit: int = 1000,
) -> str:
    """Run a query against the Cube semantic layer.

    Args:
        measures: list of measures (e.g. ["ecommerce_analytics.revenue"])
        dimensions: list of dimensions to group by
        filters: list of filters [{"member": "...", "operator": "...", "values": [...]}]
        time_dimensions: time filters and granularity
        limit: maximum number of rows (default 1000, max 5000)

    Use list_cube_metrics first to find out what is available.
    """
    query = {
        "measures":   measures,
        "dimensions": dimensions or [],
        "limit":      min(limit, 5000),
    }
    if filters:
        query["filters"] = filters
    if time_dimensions:
        query["timeDimensions"] = time_dimensions

    # Harness gate before execution
    gate = validate_cube_query(query)
    if not gate["allowed"]:
        return f"BLOCKED BY HARNESS: {gate['reason']}"

    try:
        result = cube_client.load(query)
    except Exception as e:
        logger.error("Cube query failed", extra={"error": str(e)})
        return f"ERROR: {e}"

    rows = result.get("data", [])
    return json.dumps({
        "rows":  rows[:limit],
        "count": len(rows),
    }, ensure_ascii=False, default=str)