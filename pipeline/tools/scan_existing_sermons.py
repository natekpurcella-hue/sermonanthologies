#!/usr/bin/env python3
"""Import the existing Markdown corpus into catalog records.

The script is intentionally dependency-free so it can run in the base project
environment. It reads author metadata from pipeline/authors.json, parses each
author INDEX.md, scans Markdown sermon files, and writes:

- catalog/sermons.jsonl
- catalog/scan_report.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTHORS_PATH = ROOT / "pipeline" / "authors.json"
DEFAULT_THEMES_PATH = ROOT / "pipeline" / "theme_vocabulary.json"
DEFAULT_CATALOG_PATH = ROOT / "catalog" / "sermons.jsonl"
DEFAULT_REPORT_PATH = ROOT / "catalog" / "scan_report.md"


@dataclass(frozen=True)
class IndexEntry:
    filename: str
    title: str
    themes: list[str]
    anthologies: list[str]
    index_section: str | None
    index_order: int


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"['\"]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def strip_markdown(value: str) -> str:
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"^#+\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"[*_>#|]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def split_table_row(line: str) -> list[str]:
    row = line.strip()
    if not row.startswith("|") or not row.endswith("|"):
        return []
    return [cell.strip() for cell in row[1:-1].split("|")]


def parse_index(index_path: Path) -> tuple[dict[str, IndexEntry], list[str]]:
    entries: dict[str, IndexEntry] = {}
    section_rows: list[str] = []
    current_section: str | None = None
    index_order = 0
    if not index_path.exists():
        return entries, [f"Missing index: {index_path}"]

    for line in index_path.read_text(encoding="utf-8").splitlines():
        cells = split_table_row(line)
        if len(cells) < 4:
            continue
        filename, title, themes_raw, anthology_raw = cells[:4]
        if filename == "Filename" or set(filename) <= {"-"}:
            continue
        if not filename:
            continue
        if filename.startswith("**"):
            current_section = filename.strip("* ")
            section_rows.append(current_section)
            continue
        index_order += 1
        themes = [theme.strip() for theme in themes_raw.split(",") if theme.strip()]
        anthologies = [
            item.strip()
            for item in re.split(r"[,;]", anthology_raw)
            if item.strip() and item.strip().lower() != "no"
        ]
        entries[filename] = IndexEntry(
            filename=filename,
            title=title,
            themes=themes,
            anthologies=anthologies,
            index_section=current_section,
            index_order=index_order,
        )
    return entries, section_rows


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def scripture_or_opening(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines()]
    seen_heading = False
    collected: list[str] = []
    for line in lines:
        if not line:
            if collected:
                break
            continue
        if line.startswith("#"):
            seen_heading = True
            continue
        if not seen_heading:
            continue
        collected.append(strip_markdown(line))
        if len(" ".join(collected)) > 240:
            break
    value = " ".join(collected).strip()
    return value[:300] if value else None


def word_count(text: str) -> int:
    clean = strip_markdown(text)
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", clean))


def text_hash(text: str) -> str:
    clean = strip_markdown(text).lower()
    clean = re.sub(r"\s+", " ", clean).strip()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def rights_to_status(rights_status: str) -> str:
    if rights_status.startswith("blocked"):
        return "blocked"
    if rights_status in {"unknown", "public_domain_candidate"}:
        return "rights_review"
    return "metadata_ready"


def build_record(
    author: dict,
    file_path: Path,
    index_entry: IndexEntry | None,
) -> tuple[dict, dict]:
    rel_path = file_path.relative_to(ROOT).as_posix()
    text = file_path.read_text(encoding="utf-8")
    filename = file_path.name
    stem_slug = slugify(file_path.stem)
    sermon_id = f"{author['author_id']}-{stem_slug}"
    derived_title = first_heading(text) or file_path.stem
    index_title = index_entry.title if index_entry else None
    themes = index_entry.themes if index_entry else []
    rights_status = author.get("rights_status", "unknown")

    record = {
        "sermon_id": sermon_id,
        "author_id": author["author_id"],
        "author_name": author["display_name"],
        "title": index_title or derived_title,
        "index_section": index_entry.index_section if index_entry else None,
        "index_order": index_entry.index_order if index_entry else None,
        "scripture_reference": scripture_or_opening(text),
        "filename": rel_path,
        "source": {
            "source_id": None,
            "canonical_url": None,
            "retrieved_at": None,
            "raw_checksum": None,
            "cleaner": None,
            "source_notes": "Imported from existing local Markdown corpus.",
        },
        "rights_status": rights_status,
        "rights_notes": author.get("rights_notes"),
        "themes": themes,
        "status": rights_to_status(rights_status),
        "word_count": word_count(text),
        "anthologies": index_entry.anthologies if index_entry else [],
        "tts": {
            "voice_seed": author.get("primary_seed_voice"),
            "prompt_text": None,
            "job_id": None,
            "status": None,
            "output_dir": None,
        },
        "youtube": {
            "long_form_video_id": None,
            "long_form_status": None,
            "short_video_ids": [],
        },
        "review": {
            "rights_approved": False,
            "text_approved": False,
            "audio_approved": False,
            "publication_approved": False,
            "review_notes": None,
        },
    }
    diagnostics = {
        "author_id": author["author_id"],
        "filename": rel_path,
        "derived_title": derived_title,
        "index_title": index_title,
        "hash": text_hash(text),
        "indexed": index_entry is not None,
    }
    return record, diagnostics


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def report_list(items: list[str], empty: str = "None") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def build_report(
    records: list[dict],
    diagnostics: list[dict],
    missing_files: list[str],
    unindexed_files: list[str],
    index_section_rows: list[str],
    known_themes: set[str],
) -> str:
    by_author = Counter(record["author_name"] for record in records)
    by_status = Counter(record["status"] for record in records)
    by_rights = Counter(record["rights_status"] for record in records)
    theme_counter = Counter(theme for record in records for theme in record["themes"])
    out_of_vocab = sorted(theme for theme in theme_counter if theme not in known_themes)

    hashes: dict[str, list[str]] = defaultdict(list)
    titles: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record, diag in zip(records, diagnostics, strict=True):
        hashes[diag["hash"]].append(record["filename"])
        titles[(record["author_id"], record["title"].lower())].append(
            record["filename"]
        )

    duplicate_content = [
        ", ".join(paths) for paths in hashes.values() if len(paths) > 1
    ]
    duplicate_titles = [
        ", ".join(paths) for paths in titles.values() if len(paths) > 1
    ]
    title_mismatches = []
    for diag in diagnostics:
        index_title = diag["index_title"]
        derived_title = diag["derived_title"]
        if index_title and derived_title and index_title.strip() != derived_title.strip():
            title_mismatches.append(
                f"{diag['filename']}: index `{index_title}` vs heading `{derived_title}`"
            )

    lines = [
        "# Existing Sermon Scan Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        f"- Sermon records written: {len(records)}",
        f"- Author directories scanned: {len(by_author)}",
        f"- Indexed files missing on disk: {len(missing_files)}",
        f"- Markdown files missing from indexes: {len(unindexed_files)}",
        f"- Duplicate normalized content groups: {len(duplicate_content)}",
        f"- Duplicate title groups: {len(duplicate_titles)}",
        "",
        "## Counts By Author",
        "",
    ]
    lines.extend(f"- {author}: {count}" for author, count in sorted(by_author.items()))
    lines.extend(["", "## Counts By Status", ""])
    lines.extend(f"- {status}: {count}" for status, count in sorted(by_status.items()))
    lines.extend(["", "## Counts By Rights Status", ""])
    lines.extend(f"- {status}: {count}" for status, count in sorted(by_rights.items()))
    lines.extend(["", "## Top Themes", ""])
    lines.extend(
        f"- {theme}: {count}" for theme, count in theme_counter.most_common(25)
    )
    lines.extend(["", "## Themes Not In Controlled Vocabulary", ""])
    lines.append(report_list(out_of_vocab))
    lines.extend(["", "## Indexed Files Missing On Disk", ""])
    lines.append(report_list(missing_files))
    lines.extend(["", "## Markdown Files Missing From Indexes", ""])
    lines.append(report_list(unindexed_files))
    lines.extend(["", "## Index Section Rows", ""])
    lines.append(report_list(index_section_rows))
    lines.extend(["", "## Duplicate Normalized Content", ""])
    lines.append(report_list(duplicate_content))
    lines.extend(["", "## Duplicate Titles", ""])
    lines.append(report_list(duplicate_titles))
    lines.extend(["", "## Index Title And Markdown Heading Differences", ""])
    lines.append(report_list(title_mismatches[:100]))
    if len(title_mismatches) > 100:
        lines.append(f"- ...and {len(title_mismatches) - 100} more")
    lines.append("")
    return "\n".join(lines)


def scan(args: argparse.Namespace) -> int:
    authors_data = load_json(args.authors_path)
    known_themes = set(load_json(args.themes_path).get("themes", []))
    records: list[dict] = []
    diagnostics: list[dict] = []
    missing_files: list[str] = []
    unindexed_files: list[str] = []
    index_section_rows: list[str] = []

    authors = sorted(
        authors_data["authors"],
        key=lambda item: (item.get("pipeline_priority", 999), item["author_id"]),
    )
    for author in authors:
        author_dir = ROOT / author["directory"]
        index_entries, sections = parse_index(author_dir / "INDEX.md")
        index_section_rows.extend(
            f"{author['directory']}/INDEX.md: {item}" for item in sections
        )
        md_files = {
            path.name: path
            for path in sorted(author_dir.glob("*.md"))
            if path.name != "INDEX.md"
        }

        for filename in index_entries:
            if filename not in md_files:
                missing_files.append(f"{author['directory']}/{filename}")

        imported_files: set[str] = set()
        for filename, index_entry in index_entries.items():
            file_path = md_files.get(filename)
            if file_path is None:
                continue
            record, diag = build_record(author, file_path, index_entry)
            records.append(record)
            diagnostics.append(diag)
            imported_files.add(filename)

        for filename, file_path in md_files.items():
            if filename in imported_files:
                continue
            unindexed_files.append(file_path.relative_to(ROOT).as_posix())
            record, diag = build_record(author, file_path, None)
            records.append(record)
            diagnostics.append(diag)

    write_jsonl(args.catalog_path, records)
    report = build_report(
        records=records,
        diagnostics=diagnostics,
        missing_files=missing_files,
        unindexed_files=unindexed_files,
        index_section_rows=index_section_rows,
        known_themes=known_themes,
    )
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {len(records)} records to {args.catalog_path}")
    print(f"Wrote scan report to {args.report_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authors-path", type=Path, default=DEFAULT_AUTHORS_PATH)
    parser.add_argument("--themes-path", type=Path, default=DEFAULT_THEMES_PATH)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(scan(parse_args()))
