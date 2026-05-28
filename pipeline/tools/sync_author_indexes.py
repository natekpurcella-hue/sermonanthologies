#!/usr/bin/env python3
"""Generate author INDEX.md files from catalog/sermons.jsonl.

By default this is a dry run: it prints diffs and does not write files. Pass
--write to update author indexes.
"""

from __future__ import annotations

import argparse
import difflib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTHORS_PATH = ROOT / "pipeline" / "authors.json"
DEFAULT_CATALOG_PATH = ROOT / "catalog" / "sermons.jsonl"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL row") from exc
    return records


def table_escape(value: str) -> str:
    return value.replace("|", "\\|").strip()


def author_filename(record: dict, author_dir: str) -> str:
    filename = record["filename"]
    prefix = f"{author_dir}/"
    if filename.startswith(prefix):
        return filename[len(prefix) :]
    return filename


def anthology_cell(record: dict) -> str:
    anthologies = record.get("anthologies") or []
    if not anthologies:
        return "No"
    return ", ".join(table_escape(str(item)) for item in anthologies)


def sort_key(record: dict) -> tuple[int, str]:
    index_order = record.get("index_order")
    if isinstance(index_order, int):
        return index_order, record["filename"]
    return 999_999, record["filename"]


def render_index(author: dict, records: list[dict]) -> str:
    author_dir = author["directory"]
    lines = [
        f"# Index of {author_dir}",
        "",
        "| Filename | Title | Themes | Used in Anthology |",
        "|----------|-------|--------|-------------------|",
    ]
    current_section: str | None = None
    for record in sorted(records, key=sort_key):
        section = record.get("index_section")
        if section and section != current_section:
            lines.append(f"| **{table_escape(section)}** | | | |")
            current_section = section
        elif section is None:
            current_section = None

        filename = table_escape(author_filename(record, author_dir))
        title = table_escape(record["title"])
        themes = ", ".join(table_escape(str(theme)) for theme in record.get("themes", []))
        anthologies = anthology_cell(record)
        lines.append(f"| {filename} | {title} | {themes} | {anthologies} |")
    lines.append("")
    return "\n".join(lines)


def diff_text(path: Path, old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def sync(args: argparse.Namespace) -> int:
    authors = load_json(args.authors_path)["authors"]
    author_by_id = {author["author_id"]: author for author in authors}
    records_by_author: dict[str, list[dict]] = defaultdict(list)
    for record in load_jsonl(args.catalog_path):
        records_by_author[record["author_id"]].append(record)

    changed = 0
    missing_authors = sorted(set(records_by_author) - set(author_by_id))
    if missing_authors:
        raise ValueError(f"Catalog references unknown authors: {', '.join(missing_authors)}")

    for author in sorted(authors, key=lambda item: item.get("pipeline_priority", 999)):
        records = records_by_author.get(author["author_id"], [])
        if not records:
            continue
        index_path = ROOT / author["directory"] / "INDEX.md"
        old = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
        new = render_index(author, records)
        if old == new:
            continue
        changed += 1
        if args.write:
            index_path.write_text(new, encoding="utf-8")
            print(f"Updated {index_path.relative_to(ROOT)}")
        else:
            print(diff_text(index_path.relative_to(ROOT), old, new))

    if changed == 0:
        print("All author indexes are already in sync.")
    elif not args.write:
        print(f"{changed} index file(s) would change. Re-run with --write to update.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-path", type=Path, default=DEFAULT_AUTHORS_PATH)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--write", action="store_true", help="write index files")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(sync(parse_args()))

