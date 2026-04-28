# src/cube_harness.py
# Cube-specific harness gates.

ALLOWED_VIEWS = {"orders_view", "products_view", "stream_events_view"}
MAX_DIMENSIONS = 5
MAX_LIMIT = 5000


def validate_cube_query(query: dict) -> dict:
    """Validate a Cube query before execution."""

    measures = query.get("measures", [])
    dimensions = query.get("dimensions", [])
    limit = query.get("limit", 1000)

    # Gate 1: must have at least one measure
    if not measures:
        return {
            "allowed": False,
            "reason":  "Query must have at least one measure",
        }

    # Gate 2: limit complexity (avoids cartesian explosion)
    if len(dimensions) > MAX_DIMENSIONS:
        return {
            "allowed": False,
            "reason":  f"Too many dimensions ({len(dimensions)}). Max {MAX_DIMENSIONS}.",
        }

    # Gate 3: limit result size
    if limit > MAX_LIMIT:
        return {
            "allowed": False,
            "reason":  f"Limit {limit} exceeds max {MAX_LIMIT}",
        }

    # Gate 4: only allow querying public views (not private cubes)
    all_members = measures + dimensions
    for member in all_members:
        view_name = member.split(".")[0]
        if view_name not in ALLOWED_VIEWS:
            return {
                "allowed": False,
                "reason":  f"View '{view_name}' not in allowed list",
            }

    return {"allowed": True}
