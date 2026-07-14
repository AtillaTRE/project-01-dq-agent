#!/usr/bin/env python
"""Manual smoke check against a live Cube deployment.

This is not a pytest test: it needs real Cube credentials and network access,
so it lives outside tests/ and is never collected by CI.

    python -m scripts.cube_smoke
"""

from src.cube_client import cube_client

VIEW = "orders_view"


def main() -> None:
    print("=== META ===")
    meta = cube_client.meta()
    print(f"Cubes: {[c['name'] for c in meta.get('cubes', [])]}")

    for cube_obj in meta.get("cubes", []):
        if cube_obj["name"] != VIEW:
            continue
        print(f"\n=== Measures in {VIEW} ===")
        for m in cube_obj.get("measures", []):
            print(f"  - {m['name']}: {m.get('type', '')}")
        print(f"\n=== Dimensions in {VIEW} ===")
        for d in cube_obj.get("dimensions", []):
            print(f"  - {d['name']}: {d.get('type', '')}")

    print("\n=== QUERY ===")
    result = cube_client.load({
        "measures":   [f"{VIEW}.count"],
        "dimensions": [f"{VIEW}.channel"],
        "limit":      10,
    })
    rows = result.get("data", [])
    print(f"Rows: {len(rows)}")
    print(rows[:3])


if __name__ == "__main__":
    main()
