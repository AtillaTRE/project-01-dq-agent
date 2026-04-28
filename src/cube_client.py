# src/cube_client.py
# Client HTTP for Cube Cloud with JWT auth.

import requests
import time
from src.config import settings
from src.logging_config import setup_logging

logger = setup_logging(service_name="cube-client")


class CubeClient:
    """HTTP client for the Cube Cloud REST API."""

    def __init__(self):
        self.base_url = settings.cube_api_url.rstrip("/")
        self.token = settings.cube_api_token

    def _headers(self) -> dict:
        return {
            "Authorization": self.token,
            "Content-Type":  "application/json",
        }

    def meta(self) -> dict:
        """List available cubes, views, measures and dimensions."""
        url = f"{self.base_url}/meta"
        response = requests.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def load(self, query: dict) -> dict:
        """Run a query and return the data."""
        url = f"{self.base_url}/load"
        start = time.time()
        response = requests.post(
            url, headers=self._headers(),
            json={"query": query}, timeout=60,
        )
        duration_ms = int((time.time() - start) * 1000)

        if response.status_code != 200:
            logger.error(
                "Cube query failed",
                extra={
                    "status":   response.status_code,
                    "response": response.text[:500],
                    "query":    query,
                },
            )
            response.raise_for_status()

        result = response.json()
        logger.info(
            "Cube query executed",
            extra={
                "duration_ms":  duration_ms,
                "rows_returned": len(result.get("data", [])),
                "measures":      query.get("measures", []),
                "dimensions":    query.get("dimensions", []),
            },
        )
        return result


cube_client = CubeClient()
