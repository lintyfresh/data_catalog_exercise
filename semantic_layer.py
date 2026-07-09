#!/usr/bin/env python3
"""Semantic layer for the data catalog (Part 2 goal: semantic layer for AI agents).

Merges human-authored, plain-English descriptions (catalog_config.yaml) onto the
physical asset records produced by scanner.scan(). The scanner stays untouched;
this module layers on top of its output, keyed by each asset's relative `path`.

Consumers:
  - the catalog app renders `description` / `column_descriptions` per asset
  - export_dictionary() emits an agent-consumable data dictionary (added next)
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "catalog_config.yaml"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    """Load and validate the semantic-layer config.

    Boundary validation (data enters the system here): the file must parse to a
    mapping with a `tables` mapping of {asset_path: {description?, columns?}}.
    Fails loudly on anything malformed rather than silently degrading -- a typo
    in the config should be obvious, not swallowed.

    Returns the `tables` mapping: {path: {"description": str, "columns": {col: str}}}.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"semantic config not found: {path}")

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict) or not isinstance(raw.get("tables"), dict):
        raise ValueError(
            f"{path}: expected a mapping with a top-level 'tables:' mapping"
        )

    tables = raw["tables"]
    for key, entry in tables.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry for {key!r} must be a mapping")
        cols = entry.get("columns", {})
        if not isinstance(cols, dict):
            raise ValueError(f"{path}: 'columns' for {key!r} must be a mapping")
    return tables


def enrich(assets: list[dict], config: dict) -> list[dict]:
    """Attach semantic descriptions to scanned assets. Non-mutating.

    Returns a new list of shallow-copied asset dicts, each gaining:
      - `description`: str | None  (table-level, None if undocumented)
      - `column_descriptions`: dict[str, str]  (only for columns that actually
        exist in this asset's scanned `schema`; empty if none documented)

    We copy rather than mutate because the scanner's output is shared with other
    catalog consumers (the app, the scanner's own tests) -- enriching in place
    would let this module silently reshape data other code already holds.

    Emits WARNINGs for config drift so stale metadata surfaces loudly:
      - config entries whose path was not found in the scan
      - documented columns absent from a table's actual schema
    """
    config = dict(config)  # local copy so we can pop matched entries to find drift
    enriched: list[dict] = []

    for asset in assets:
        out = dict(asset)  # shallow copy: don't mutate the caller's asset
        entry = config.pop(asset["path"], None) or {}

        out["description"] = entry.get("description")

        schema_cols = set(asset.get("schema", {}))
        documented = entry.get("columns", {})
        # keep only descriptions for columns that really exist in this schema
        out["column_descriptions"] = {
            col: desc for col, desc in documented.items() if col in schema_cols
        }
        for col in documented.keys() - schema_cols:
            logger.warning(
                "config documents column %r not in schema of %s", col, asset["path"]
            )

        enriched.append(out)

    for stale_path in config:
        logger.warning(
            "config describes %r but the scanner found no such asset", stale_path
        )

    return enriched


def coverage(enriched: list[dict]) -> dict:
    """Report documentation coverage over enriched assets.

    A quality signal (and a nice demo number): how much of the catalog actually
    carries semantics. Column counts are taken from each asset's scanned schema,
    so `documented <= total` holds by construction.
    """
    total_tables = len(enriched)
    documented_tables = sum(1 for a in enriched if a.get("description"))
    total_columns = sum(len(a.get("schema", {})) for a in enriched)
    documented_columns = sum(len(a.get("column_descriptions", {})) for a in enriched)
    return {
        "tables": {"documented": documented_tables, "total": total_tables},
        "columns": {"documented": documented_columns, "total": total_columns},
    }


def _asset_dictionary(asset: dict) -> dict:
    """Shape one enriched asset into the agent-facing record.

    Pairs each column's type (from the scanner) with its description (from the
    semantic layer) in schema order -- the type+meaning pairing is exactly what
    an LLM needs to reason about a column it has never seen.
    """
    path = asset["path"]
    parts = Path(path).parts
    return {
        "name": Path(path).name,          # leaf label, e.g. "orders"
        "path": path,                     # unique key back to the scanner
        "layer": parts[0] if parts else None,  # bronze / silver, from the path
        "format": asset.get("format"),
        "description": asset.get("description"),
        "columns": [
            {"name": col, "type": typ, "description": asset.get("column_descriptions", {}).get(col)}
            for col, typ in asset.get("schema", {}).items()
        ],
    }


def export_dictionary(enriched: list[dict], fmt: str = "json") -> str:
    """Render an agent-consumable data dictionary from enriched assets.

    fmt="json": a JSON array of asset records (machine-readable context to hand
    an LLM). fmt="markdown": the same content as a human/agent-readable doc.
    Every scanned asset appears, documented or not, so the export never hides
    gaps in the semantic layer.
    """
    records = [_asset_dictionary(a) for a in enriched]

    if fmt == "json":
        return json.dumps(records, indent=2)

    if fmt == "markdown":
        lines = ["# Data dictionary", ""]
        for r in records:
            lines.append(f"## {r['name']}  (`{r['path']}`)")
            lines.append(f"- **layer:** {r['layer']} · **format:** {r['format']}")
            lines.append(f"- {r['description'] or '_no description_'}")
            lines.append("")
            lines.append("| column | type | description |")
            lines.append("| --- | --- | --- |")
            for c in r["columns"]:
                lines.append(f"| {c['name']} | {c['type']} | {c['description'] or ''} |")
            lines.append("")
        return "\n".join(lines)

    raise ValueError(f"unknown export format: {fmt!r} (use 'json' or 'markdown')")


def main() -> None:
    """CLI: scan a data root, merge the semantic layer, report coverage, export.

    Example:
        python semantic_layer.py sample_lakehouse --export json -o data_dictionary.json
    """
    parser = argparse.ArgumentParser(description="Semantic layer over the lakehouse scanner.")
    parser.add_argument("root", nargs="?", default="sample_lakehouse", help="data root to scan")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="semantic config YAML")
    parser.add_argument("--export", choices=["json", "markdown"], help="write a data dictionary")
    parser.add_argument("-o", "--out", help="output file for --export (default: stdout)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    root = Path(args.root)
    if not root.is_dir():
        sys.exit(f"data root not found: {root}")

    # scan() is the classmate's Part-1 foundation; we only layer on top of it.
    from scanner import scan

    assets = enrich(scan(root), load_config(args.config))
    cov = coverage(assets)
    logger.info(
        "coverage: %d/%d tables, %d/%d columns documented",
        cov["tables"]["documented"], cov["tables"]["total"],
        cov["columns"]["documented"], cov["columns"]["total"],
    )

    if args.export:
        doc = export_dictionary(assets, args.export)
        if args.out:
            Path(args.out).write_text(doc, encoding="utf-8")
            logger.info("wrote %s data dictionary to %s", args.export, args.out)
        else:
            print(doc)


if __name__ == "__main__":
    main()
