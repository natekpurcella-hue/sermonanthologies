# Pipeline Metadata

This directory contains the metadata contracts for the sermon content pipeline.
It is intentionally small: the existing Markdown corpus remains in the author
directories, and generated audio/video should continue to live under `output/`.

## Files

- `authors.json`: Author registry, including directory names, voice seeds,
  source candidates, and rights status.
- `CONTENT_PIPELINE.md`: End-to-end design for retrieval, cleaning, metadata,
  TTS, video, shorts, anthology, and distribution workflows.
- `TODO.md`: Phased implementation backlog.
- `sermon_record.schema.json`: Draft JSON Schema for future
  `catalog/sermons.jsonl` records.
- `theme_vocabulary.json`: Controlled theme list for indexes, anthology
  grouping, and clip discovery.
- `audio_scripts/`: TTS narration variants with voice-direction tags. These are
  derived from sermons and should not live in the canonical author corpus.
- `tools/scan_existing_sermons.py`: Imports current author Markdown and indexes
  into `catalog/sermons.jsonl`.
- `tools/sync_author_indexes.py`: Regenerates author `INDEX.md` files from the
  catalog. Dry-run by default; use `--write` to update files.
- `tools/validate_catalog.py`: Checks catalog shape, author ids, file paths,
  status values, duplicate ids, duplicate filenames, and theme vocabulary.

## Intended Flow

1. Scan author directories and indexes.
2. Create or update catalog records.
3. Retrieve raw source material for missing sermons.
4. Clean into Markdown.
5. Review rights, text, and themes.
6. Generate TTS jobs for approved sermons.
7. Create long-form and short-form YouTube drafts.
8. Build anthologies and audiobook packages from approved catalog records.

## Common Commands

```bash
python3 pipeline/tools/scan_existing_sermons.py
python3 pipeline/tools/validate_catalog.py
python3 pipeline/tools/sync_author_indexes.py
python3 pipeline/tools/sync_author_indexes.py --write
```
