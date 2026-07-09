# Changelog

## [2026-07-09] — Semantic layer for AI agents (Part 2 goal)

**What:** Added a semantic layer over the Part-1 scanner: a YAML config of
plain-English table/column descriptions, a module that merges them onto scanned
assets, and an agent-consumable data-dictionary export.

**Why:** Part 2 "Semantic layer (for AI agents)" goal. Descriptions capture what
column names and dtypes can't — notably disambiguating traps (`orders.state` is a
US state, *not* an order status) and cross-table concepts hidden behind different
names (`returns.cust_id` == `customer_id`; `reviews.product_sku` == `product_id`).

**Files:**
- `catalog_config.yaml` (new) — descriptions for all 10 assets, keyed by the
  scanner's relative `path`.
- `semantic_layer.py` (new) — `load_config`, `enrich` (non-mutating merge),
  `coverage`, `export_dictionary` (json/markdown), and a `main()` CLI.
- `test_semantic_layer.py` (new) — real-data verification, incl. the shared
  `customer_id` concept documented across orders/customers and its aliases.
- `requirements.txt` — added `pyyaml`.
- `README.md` — usage notes.

**Notes:** Deliberately did NOT touch `scanner.py`/`test_scanner.py` (classmate's
Part-1 foundation); the layer keys off the existing `path` field and merges at
integration time via `enrich(scan(root), load_config())`. `data_dictionary.json`
is a generated artifact (regenerate with the CLI), not source.
Retrospective: the scan surfaced that "the same thing" wears three different
column names across tables — the single most useful thing the descriptions
encode, and exactly what an AI agent would otherwise get wrong.
