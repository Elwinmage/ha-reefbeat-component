#!/usr/bin/env python3
"""Remove one or more entity translation keys from strings.json and every
translations/*.json file.

Usage:
    ./scripts/remove_translation.py button.port_install_other button.port_install_ato

Each argument is "<domain>.<key>" (matching what `check_translation.py`
reports under "Entity keys no more needed in ..."), e.g. the entity
description ``ReefBeatButtonEntityDescription(key="port_install_other", ...)``
in ``button.py`` corresponds to ``button.port_install_other``.

Add --dry-run to see what would change without writing anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
base_path = os.path.join(repo_root, "custom_components", "redsea")
strings_file = os.path.join(base_path, "strings.json")
translations_path = os.path.join(base_path, "translations")


def target_files() -> list[str]:
    files = [strings_file]
    for name in sorted(os.listdir(translations_path)):
        if name.endswith(".json"):
            files.append(os.path.join(translations_path, name))
    return files


def remove_keys(path: str, tokens: list[tuple[str, str]], dry_run: bool) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    removed: list[str] = []
    missing: list[str] = []
    entities = data.get("entity", {})
    for domain, key in tokens:
        bucket = entities.get(domain)
        if isinstance(bucket, dict) and key in bucket:
            del bucket[key]
            removed.append(f"{domain}.{key}")
        else:
            missing.append(f"{domain}.{key}")

    label = os.path.relpath(path, repo_root)
    if removed:
        print(f"{label}: removed {removed}")
    if missing:
        print(f"{label}: not found (skipped) {missing}")

    if removed and not dry_run:
        out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "keys",
        nargs="+",
        help='Entity keys to remove, as "<domain>.<key>" (e.g. button.port_install_other)',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without writing any file",
    )
    args = parser.parse_args()

    tokens: list[tuple[str, str]] = []
    for raw in args.keys:
        if "." not in raw:
            print(f"error: {raw!r} is not in the form <domain>.<key>", file=sys.stderr)
            sys.exit(1)
        domain, key = raw.split(".", 1)
        tokens.append((domain, key))

    for path in target_files():
        remove_keys(path, tokens, args.dry_run)


if __name__ == "__main__":
    main()
