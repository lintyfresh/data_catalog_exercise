"""Verify the scanner against sample_lakehouse. Run: python test_scanner.py"""
from pathlib import Path

from scanner import scan

assets = scan(Path("sample_lakehouse"))
by_path = {a["path"]: a for a in assets}

# finds everything, including nested subfolders
assert len(assets) == 10, f"expected 10 assets, got {len(assets)}: {sorted(by_path)}"
assert "bronze/orders_raw/orders_bronze.csv" in by_path
assert "silver/sales/orders" in by_path
assert not any("error" in a for a in assets), [a for a in assets if "error" in a]

# every delta table has a schema and its FULL history (v0 .. current)
deltas = [a for a in assets if a["kind"] == "delta"]
assert len(deltas) == 9
for a in deltas:
    assert a["schema"], f"{a['path']}: empty schema"
    versions = sorted(h["version"] for h in a["history"])
    assert versions == list(range(versions[-1] + 1)), f"{a['path']}: gaps in history {versions}"

# plain files get a schema but no version history
csv = by_path["bronze/orders_raw/orders_bronze.csv"]
assert csv["schema"] and "history" not in csv

print("all checks passed")
