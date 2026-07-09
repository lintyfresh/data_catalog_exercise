"""Verify the semantic layer against sample_lakehouse. Run: python test_semantic_layer.py

Mirrors test_scanner.py's style (plain asserts, real data). Checks that the
descriptions actually merge onto the right tables/columns and that the
agent-facing export is well-formed.
"""
import json
from pathlib import Path

from scanner import scan
from semantic_layer import load_config, enrich, coverage, export_dictionary

config = load_config()
raw = scan(Path("sample_lakehouse"))
assets = enrich(raw, config)
by_path = {a["path"]: a for a in assets}

# enrich adds a non-empty table description to a known table
orders = by_path["silver/sales/orders"]
assert orders["description"], "orders table has no description"

# shared column CONCEPT is documented everywhere it appears -- under its own
# name (customer_id) in orders and customers, and under aliases elsewhere.
assert by_path["silver/sales/orders"]["column_descriptions"].get("customer_id")
assert by_path["silver/sales/customers"]["column_descriptions"].get("customer_id")
assert by_path["silver/ops/returns"]["column_descriptions"].get("cust_id"), \
    "returns.cust_id (a customer_id alias) is undocumented"
assert by_path["silver/marketing/reviews"]["column_descriptions"].get("product_sku"), \
    "reviews.product_sku (a product_id alias) is undocumented"

# enrich never invents a column that isn't in the table's actual schema
for a in assets:
    schema_cols = set(a["schema"])
    extra = set(a["column_descriptions"]) - schema_cols
    assert not extra, f"{a['path']}: column_descriptions has non-schema cols {extra}"

# enrich is non-mutating: the scanner's own records gain no new keys
assert all("description" not in a for a in raw), "enrich mutated the scanner output"

# coverage is internally consistent (documented never exceeds total)
cov = coverage(assets)
assert cov["tables"]["documented"] <= cov["tables"]["total"]
assert cov["columns"]["documented"] <= cov["columns"]["total"]

# the agent-facing JSON export is valid and carries the semantics
records = json.loads(export_dictionary(assets, "json"))
assert len(records) == len(assets), "export dropped or added assets"
orders_rec = next(r for r in records if r["path"] == "silver/sales/orders")
assert orders_rec["description"] == orders["description"]
state_col = next(c for c in orders_rec["columns"] if c["name"] == "state")
assert "NOT an order status" in (state_col["description"] or ""), \
    "orders.state is missing its disambiguating description in the export"

# markdown export is non-empty and mentions a known table
md = export_dictionary(assets, "markdown")
assert md.strip() and "silver/sales/orders" in md

print(f"all checks passed  (coverage: {cov})")
