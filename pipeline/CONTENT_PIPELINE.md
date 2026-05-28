# Content Pipeline Framework

This project should treat every sermon as a managed content asset that moves
through repeatable stages: source retrieval, cleaning, metadata, approval, audio
generation, packaging, and publishing.

## Pipeline Goals

- Retrieve sermons for each author represented by a top-level author directory.
- Preserve a traceable raw source before producing cleaned Markdown.
- Remove forewords, publisher notes, navigation text, ads, footnotes, and other
  extras that are not part of the sermon message.
- Store each cleaned sermon in the correct author directory and keep that
  author's `INDEX.md` current.
- Assign a small set of themes from a controlled vocabulary plus free-form notes
  when needed.
- Generate long-form narrated content from approved sermons using the existing
  voice seeds and Kaggle Fish Speech workflow.
- Extract short, poignant clips from the sermon text and generated audio for
  short-form video.
- Package sermons into text anthologies and audiobook-ready audio collections.
- Keep YouTube and audiobook distribution behind explicit human approval.

## High-Level Stages

| Stage | Output | Automation Target |
|-------|--------|-------------------|
| 1. Author inventory | `pipeline/authors.json` | List authors, directories, seed voices, source candidates, and rights status. |
| 2. Source discovery | Source records | Find canonical source URLs or local scans for each sermon. |
| 3. Rights gate | Approved source list | Block ingestion until the work is public domain, licensed, or permissioned. |
| 4. Retrieval | Raw source files | Download HTML, TXT, EPUB, PDF, or OCR text with checksum and citation. |
| 5. Text cleaning | Clean Markdown | Remove non-sermon material while preserving title, text, scripture, and section headings. |
| 6. Metadata | Catalog record | Assign sermon id, author, title, source, themes, status, word count, and downstream usage. |
| 7. Index sync | Author `INDEX.md` | Generate or update index rows from catalog metadata. |
| 8. Review | Approved sermon | Human review for text quality, rights, themes, and TTS readiness. |
| 9. Audio generation | WAV chunks/full WAV | Submit approved script to local or Kaggle generation pipeline. |
| 10. Audio QA | Approved audio | Check duration, clipping, silence, missing chunks, and obvious pronunciation failures. |
| 11. Long-form video | Draft upload | Generate title, description, chapters, thumbnail, and upload as private or draft. |
| 12. Short-form clips | Draft shorts | Select text spans, cut matching audio, render vertical video, upload as private or draft. |
| 13. Anthologies | Text/audio packages | Group sermons by theme, produce Markdown/EPUB/PDF and audiobook chapters. |
| 14. Publication approval | Public release | Human approves final public YouTube status or distribution submission. |

## Repository Layout

Recommended additions:

```text
pipeline/
  README.md
  authors.json
  sermon_record.schema.json
  theme_vocabulary.json
  sources/
    README.md
  jobs/
    README.md

catalog/
  sermons.jsonl
  source_records.jsonl

source_cache/
  raw/
  normalized/

assets/
  thumbnails/
  video_templates/
  shorts_templates/

output/
  audio/
  video/
  anthology/
```

`output/`, checkpoints, generated WAV files, and downloaded bulk source caches
should stay out of commits unless a specific generated artifact is intentionally
being preserved.

## Core Data Model

The durable unit should be a `sermon_record`, stored eventually as one JSON
object per line in `catalog/sermons.jsonl`.

Required fields:

- `sermon_id`: Stable id such as `spurgeon-mtp-0003`.
- `author_id`: Stable author id from `pipeline/authors.json`.
- `author_name`: Display name.
- `title`: Clean sermon title.
- `filename`: Markdown path in the author directory.
- `source`: Canonical source metadata and retrieval checksum.
- `rights_status`: `public_domain`, `licensed`, `permissioned`, `blocked`, or
  `unknown`.
- `themes`: Three to seven controlled vocabulary themes.
- `status`: Current pipeline state.
- `word_count`: Clean text word count.
- `tts`: Voice seed, prompt text, generation status, and output paths.
- `youtube`: Long-form and short-form draft/upload status.
- `anthologies`: Anthology memberships.

The local Markdown files should remain the readable corpus. The catalog should
become the source of truth for automation and index generation.

## Status Flow

Use explicit states so automation can resume safely:

```text
candidate
rights_review
source_selected
retrieved_raw
cleaned
metadata_ready
text_review
tts_ready
audio_generating
audio_review
video_ready
youtube_draft
publication_review
published
anthology_ready
blocked
```

Any state that can publish, distribute, or spend meaningful compute should have a
human approval gate before it.

## Author Scope And Rights Gate

Initial author directories:

- `Charles Spurgeon`
- `Finney`
- `George Muller`
- `Wesley`
- `AW Tozer`
- `Ravenhill`

Spurgeon, Finney, Muller, and Wesley are strong public-domain candidates, though
each source edition still needs a source-level check. Tozer and Ravenhill should
be treated as rights-blocked until permission or a license is documented. Their
original messages, recordings, edited books, and modern transcriptions may still
be protected even when the theology or facts are not.

Before public YouTube upload or audiobook distribution, every item should have a
recorded rights basis and source citation. This is a workflow control, not legal
advice.

## Retrieval Strategy

Retrieval should be source-specific and repeatable:

1. Maintain source candidates per author in `pipeline/authors.json`.
2. Create one source adapter per site or archive format.
3. Save raw source material with checksum before cleaning.
4. Normalize raw text to UTF-8 plain text.
5. Run cleaning rules with source-specific selectors or section markers.
6. Produce a diffable Markdown sermon file.
7. Record source URL, retrieval date, checksum, and cleaner version.

Prefer structured extraction for HTML, EPUB, and PDF when practical. Avoid
fragile regex-only extraction for source formats with reliable parsers.

## Cleaning Policy

Cleaning should remove:

- Site headers, footers, navigation, ads, and related links.
- Editor introductions, publisher forewords, biographical prefaces, and notes
  that are not part of the message.
- Page numbers, OCR artifacts, duplicate headings, footnote markers, and
  boilerplate copyright text.
- Modern commentary unless intentionally stored as a separate context note.

Cleaning should preserve:

- Sermon title.
- Scripture text or primary passage.
- Sermon body.
- Original major section headings when useful.
- Short source note in metadata, not in the sermon body.

## Theme Assignment

Use a controlled vocabulary for index consistency. A first pass can be automated
by keyword and embedding/LLM classification, then reviewed by a human.

Recommended seed themes:

```text
Assurance
Christ
Comfort
Conscience
Conversion
Faith
Grace
Holiness
Holy Spirit
Humility
Judgment
Obedience
Prayer
Providence
Repentance
Revival
Salvation
Sanctification
Scripture
Sin
Sovereignty
Suffering
Temptation
Witness
```

Each sermon should usually have three to seven themes. If more are needed, the
theme list is probably too broad and should be tightened during review.

## Kaggle Integration

The existing Kaggle Fish Speech notebook remains the GPU generation backend.
The content pipeline should prepare jobs for it rather than replacing it.

Expected job package:

- Clean sermon text or an audio-script variant.
- Author voice seed path or Kaggle dataset reference.
- Prompt text matched to the seed voice.
- Generation parameters.
- Expected output names.
- Callback or watcher metadata.

The watcher should download output into `output/audio/<author_id>/<sermon_id>/`
and update the sermon catalog status after validation.

## Long-Form YouTube Flow

For each approved audio sermon:

1. Produce full audio master.
2. Generate still or lightly animated video background.
3. Generate title, description, scripture reference, chapters, and source note.
4. Upload through the YouTube API as private or draft.
5. Store returned video id in the catalog.
6. Require human approval before public visibility.

## Short-Form Flow

Shorts should be derived from the sermon itself, not separate commentary.

1. Identify candidate spans from the text: 20 to 60 seconds when spoken.
2. Score for clarity, emotional force, standalone meaning, and relation to the
   long-form sermon.
3. Map text span to generated audio chunk/timecode.
4. Render vertical video with captions and a consistent visual template.
5. Upload private/draft.
6. Link the short to the long-form video after the long-form video id exists.

## Anthology And Audiobook Flow

Anthologies should be built from catalog queries:

- Theme-driven collections such as faith, prayer, revival, assurance, or
  judgment.
- Author collections such as early Spurgeon or selected Wesley sermons.
- Mixed-author devotional sequences.

For each anthology:

1. Select approved sermons.
2. Generate table of contents.
3. Build text edition as Markdown first.
4. Export EPUB/PDF after text review.
5. Build audiobook chapters from approved audio masters.
6. Normalize loudness and spacing.
7. Create cover, metadata, introduction, and credits.
8. Hold distribution package for human approval.

## Implementation Order

1. Define author metadata, theme vocabulary, and sermon schema.
2. Build catalog reader/writer and index sync.
3. Import existing sermons into `catalog/sermons.jsonl`.
4. Add one source adapter for a public-domain author.
5. Add source retrieval and cleaning test fixtures.
6. Add review states and approval commands.
7. Generate Kaggle job packages from approved records.
8. Add audio output watcher integration.
9. Add long-form video draft generation.
10. Add short-form clip extraction and draft rendering.
11. Add anthology builder.
12. Add publishing integrations behind approval gates.

