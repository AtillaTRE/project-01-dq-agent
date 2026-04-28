from src.cube_client import cube_client

if __name__ == "__main__":
    print("=== META ===")
    meta = cube_client.meta()
    print(f"Cubes: {[c['name'] for c in meta.get('cubes', [])]}")

    for c in meta.get("cubes", []):
        if c["name"] == "orders_view":
            print(f"\n=== Measures em orders_view ===")
            for m in c.get("measures", []):
                print(f"  - {m['name']}: {m.get('type', '')}")
            print(f"\n=== Dimensions em orders_view ===")
            for d in c.get("dimensions", []):
                print(f"  - {d['name']}: {d.get('type', '')}")

    print("\n=== QUERY ===")
    result = cube_client.load({
        "measures":   ["orders_view.count"],
        "dimensions": ["orders_view.channel"],
        "limit":      10,
    })
    print(f"Rows: {len(result['data'])}")
    print(result["data"][:3])