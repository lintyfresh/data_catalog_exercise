# data_catalog_exercise

Lakehouse catalog scanner (Part 1) with a local React UI for browsing
Delta table schemas/history and plain-file schemas in `sample_lakehouse/`.

## Setup

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Scan

```
.venv/bin/python scanner.py                                  # terminal catalog
.venv/bin/python scanner.py --json > web/public/catalog.json # regenerate for the UI
.venv/bin/python test_scanner.py                             # verify
```

## Web UI

```
cd web && npm install && npm run dev   # http://localhost:5173
```
