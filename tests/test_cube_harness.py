# tests/test_cube_harness.py

from src.cube_harness import ALLOWED_VIEWS, MAX_DIMENSIONS, MAX_LIMIT, validate_cube_query


class TestValidateCubeQuery:
    def test_allows_query_on_allow_listed_view(self):
        result = validate_cube_query({
            "measures":   ["orders_view.count"],
            "dimensions": ["orders_view.channel"],
            "limit":      100,
        })
        assert result["allowed"] is True

    def test_requires_at_least_one_measure(self):
        result = validate_cube_query({
            "measures":   [],
            "dimensions": ["orders_view.channel"],
        })
        assert result["allowed"] is False
        assert "measure" in result["reason"]

    def test_blocks_view_outside_allow_list(self):
        result = validate_cube_query({
            "measures": ["ecommerce_analytics.revenue"],
        })
        assert result["allowed"] is False
        assert "not in allowed list" in result["reason"]

    def test_blocks_too_many_dimensions(self):
        result = validate_cube_query({
            "measures":   ["orders_view.count"],
            "dimensions": [f"orders_view.d{i}" for i in range(MAX_DIMENSIONS + 1)],
        })
        assert result["allowed"] is False

    def test_blocks_limit_above_max(self):
        result = validate_cube_query({
            "measures": ["orders_view.count"],
            "limit":    MAX_LIMIT + 1,
        })
        assert result["allowed"] is False

    def test_allow_list_matches_documented_views(self):
        # Guards against the README/prompt drifting from the enforced allow-list
        assert ALLOWED_VIEWS == {"orders_view", "products_view", "stream_events_view"}
