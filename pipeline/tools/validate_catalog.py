#!/usr/bin/env python3
"""Validate catalog/sermons.jsonl for pipeline readiness.

This is not a full JSON Schema implementation. It performs the checks that
matter most for local automation without adding a dependency.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTHORS_PATH = ROOT / "pipeline" / "authors.json"
DEFAULT_CATALOG_PATH = ROOT / "catalog" / "sermons.jsonl"
DEFAULT_SCHEMA_PATH = ROOT / "pipeline" / "sermon_record.schema.json"
DEFAULT_THEMES_PATH = ROOT / "pipeline" / "theme_vocabulary.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[tuple[int, dict]]:
    rows: list[tuple[int, dict]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append((line_number, json.loads(line)))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL row") from exc
    return rows


def expect_type(value: object, allowed: tuple[type, ...]) -> bool:
    return isinstance(value, allowed)


def validate(args: argparse.Namespace) -> int:
    authors = load_json(args.authors_path)["authors"]
    schema = load_json(args.schema_path)
    themes = set(load_json(args.themes_path)["themes"])
    rows = load_jsonl(args.catalog_path)

    author_by_id = {author["author_id"]: author for author in authors}
    required = schema["required"]
    rights_values = set(schema["properties"]["rights_status"]["enum"])
    status_values = set(schema["properties"]["status"]["enum"])
    errors: list[str] = []
    warnings: list[str] = []

    ids = Counter(record.get("sermon_id") for _, record in rows)
    filenames = Counter(record.get("filename") for _, record in rows)

    for line_number, record in rows:
        prefix = f"{args.catalog_path}:{line_number}"
        for field in required:
            if field not in record:
                errors.append(f"{prefix}: missing required field `{field}`")

        sermon_id = record.get("sermon_id")
        if sermon_id and ids[sermon_id] > 1:
            errors.append(f"{prefix}: duplicate sermon_id `{sermon_id}`")

        filename = record.get("filename")
        if filename and filenames[filename] > 1:
            errors.append(f"{prefix}: duplicate filename `{filename}`")
        if filename and not (ROOT / filename).exists():
            errors.append(f"{prefix}: filename does not exist on disk: {filename}")

        author_id = record.get("author_id")
        author = author_by_id.get(author_id)
        if author is None:
            errors.append(f"{prefix}: unknown author_id `{author_id}`")
        elif filename and not filename.startswith(f"{author['directory']}/"):
            warnings.append(
                f"{prefix}: filename is outside expected author directory "
                f"`{author['directory']}/`: {filename}"
            )

        rights_status = record.get("rights_status")
        if rights_status not in rights_values:
            errors.append(f"{prefix}: invalid rights_status `{rights_status}`")

        status = record.get("status")
        if status not in status_values:
            errors.append(f"{prefix}: invalid status `{status}`")

        title = record.get("title")
        if not expect_type(title, (str,)) or not str(title).strip():
            errors.append(f"{prefix}: title must be a non-empty string")

        word_count = record.get("word_count")
        if not isinstance(word_count, int) or word_count < 0:
            errors.append(f"{prefix}: word_count must be a non-negative integer")
        elif word_count < args.min_words:
            warnings.append(f"{prefix}: low word_count `{word_count}`")

        record_themes = record.get("themes")
        if not isinstance(record_themes, list):
            errors.append(f"{prefix}: themes must be a list")
        else:
            duplicates = sorted(
                theme for theme, count in Counter(record_themes).items() if count > 1
            )
            if duplicates:
                errors.append(f"{prefix}: duplicate themes: {', '.join(duplicates)}")
            unknown_themes = sorted(theme for theme in record_themes if theme not in themes)
            if unknown_themes:
                errors.append(
                    f"{prefix}: themes not in vocabulary: {', '.join(unknown_themes)}"
                )

        if status == "published":
            review = record.get("review") or {}
            if not review.get("publication_approved"):
                errors.append(f"{prefix}: published record lacks publication approval")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")
        print(f"Catalog validation failed: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    print(f"Catalog validation passed: {len(rows)} record(s), {len(warnings)} warning(s)")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-path", type=Path, default=DEFAULT_AUTHORS_PATH)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--schema-path", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--themes-path", type=Path, default=DEFAULT_THEMES_PATH)
    parser.add_argument(
        "--min-words",
        type=int,
        default=500,
        help="warn when a sermon record has fewer words than this threshold",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(validate(parse_args()))

