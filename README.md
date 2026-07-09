# data_catalog_exercise

A small data catalog over a sample e-commerce lakehouse (MSDS 681, Day 2).

## Part 1 — scanner (foundation)

`scanner.py` walks a data root and emits one record per asset: Delta tables
(schema + full version history) and plain files (pandas-inferred schema).

```bash
python scanner.py sample_lakehouse   # print the catalog
python test_scanner.py               # verify against the sample data
```

## Part 2 — semantic layer (for AI agents)

`semantic_layer.py` merges human-authored, plain-English descriptions
(`catalog_config.yaml`) onto the scanner's output, and exports an
agent-consumable data dictionary. The scanner is untouched; the layer keys off
each asset's relative `path`.

```bash
# scan + merge descriptions, report coverage, write the agent data dictionary
python semantic_layer.py sample_lakehouse --export json -o data_dictionary.json
python semantic_layer.py sample_lakehouse --export markdown   # human-readable to stdout
python test_semantic_layer.py                                 # verify against sample data
```

In code (e.g. from the catalog app):

```python
from scanner import scan
from semantic_layer import load_config, enrich

assets = enrich(scan("sample_lakehouse"), load_config())
# each asset now has `description` and `column_descriptions`
```

`catalog_config.yaml` is keyed by asset path; edit it to document tables/columns.
Undocumented assets are fine — they get a null description, not an error.

## Web UI

A local React app (Vite) for browsing the catalog: asset list with filter,
schema tables, and full Delta commit history. It reads a static
`web/public/catalog.json` produced by the scanner — no backend.

```bash
cd web && npm install && npm run dev                        # http://localhost:5173
python scanner.py --json > web/public/catalog.json          # regenerate after a rescan
```

## Setup

```bash
pip install -r requirements.txt   # deltalake, pandas, pyarrow, pyyaml
python ../sync_sample_lakehouse.py   # if sample_lakehouse/ is missing
```
