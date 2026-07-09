#!/usr/bin/env python3
"""Scan a lakehouse folder and print a catalog of every asset found.

Delta tables (folders containing _delta_log) show their current schema and
full commit history; plain csv/json/parquet files show a pandas-inferred
schema. Paths are shown relative to the data root.

Usage: python scanner.py [data_root] [--json]   (default root: sample_lakehouse)
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from deltalake import DeltaTable

DATA_EXTS = {".csv", ".json", ".parquet"}


def find_assets(root: Path) -> list[tuple[Path, str]]:
    """List every Delta table dir or plain data file under root as (path, kind)."""
    assets = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        if "_delta_log" in dirnames:
            assets.append((d, "delta"))
            dirnames.clear()  # a Delta table's part-files and logs are one asset
            continue
        dirnames.sort()  # deterministic walk order
        for name in sorted(filenames):
            if Path(name).suffix.lower() in DATA_EXTS:
                assets.append((d / name, "file"))
    return assets


def file_schema(path: Path) -> dict:
    """Infer column -> dtype for a plain file via pandas."""
    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:  # .json
        try:
            df = pd.read_json(path)
        except ValueError:
            df = pd.read_json(path, lines=True)
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def describe(path: Path, kind: str, root: Path) -> dict:
    asset = {"path": str(path.relative_to(root)), "kind": kind}
    try:
        if kind == "delta":
            dt = DeltaTable(str(path))
            asset["format"] = "delta"
            asset["schema"] = {
                f.name: getattr(f.type, "type", str(f.type)) for f in dt.schema().fields
            }
            asset["history"] = [
                {
                    "version": h.get("version"),
                    "operation": h.get("operation"),
                    "timestamp": datetime.fromtimestamp(
                        h["timestamp"] / 1000, tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                }
                for h in dt.history()
            ]
        else:
            asset["format"] = path.suffix.lstrip(".").lower()
            asset["schema"] = file_schema(path)
    except Exception as e:  # keep cataloging even if one asset is unreadable
        asset["error"] = str(e)
    return asset


def scan(root: Path) -> list[dict]:
    return [describe(path, kind, root) for path, kind in find_assets(root)]


def print_catalog(assets: list[dict]) -> None:
    for a in assets:
        label = "delta table" if a["kind"] == "delta" else f"{a['format']} file"
        print(f"\n{a['path']}  [{label}]")
        if "error" in a:
            print(f"  ! could not read: {a['error']}")
            continue
        print("  schema:")
        for col, typ in a["schema"].items():
            print(f"    {col}: {typ}")
        if a["kind"] == "delta":
            print("  history:")
            for h in a["history"]:
                print(f"    v{h['version']}  {h['timestamp']}  {h['operation']}")
    n_delta = sum(a["kind"] == "delta" for a in assets)
    print(f"\n{len(assets)} assets ({n_delta} delta tables, {len(assets) - n_delta} plain files)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    root = Path(args[0] if args else "sample_lakehouse")
    if not root.is_dir():
        sys.exit(f"data root not found: {root}")
    assets = scan(root)
    if "--json" in sys.argv:
        print(json.dumps(assets, indent=2))
    else:
        print_catalog(assets)
