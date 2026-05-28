# Content Pipeline To Do

This backlog starts from the current repository state: Markdown sermons exist,
author indexes exist, voice seeds exist, and Kaggle Fish Speech generation is
partially working.

Current status: the metadata foundation is complete. The next active work is
Phase 2, source retrieval.

## Phase 0: Decisions And Guardrails

- [ ] Confirm which authors are in scope for public release first.
- [ ] Decide whether `catalog/sermons.jsonl` becomes the source of truth for
  indexes.
- [ ] Define the minimum human approval gates: rights, cleaned text, generated
  audio, YouTube draft, public release, and audiobook package.
- [ ] Decide where private credentials live for YouTube, Kaggle, and any
  audiobook distributor.
- [ ] Document rights basis per author and per source edition.

## Phase 1: Metadata Foundation

- [x] Finalize `pipeline/authors.json`.
- [x] Finalize `pipeline/sermon_record.schema.json`.
- [x] Create `pipeline/theme_vocabulary.json`.
- [x] Create `catalog/sermons.jsonl`.
- [x] Write an importer that scans current author directories and builds initial
  sermon records from existing Markdown and `INDEX.md` files.
- [x] Write a validator that checks catalog records against the schema.
- [x] Write an index sync script that generates author `INDEX.md` rows from the
  catalog.

## Phase 2: Source Retrieval

- [ ] Select the first public-domain author for adapter development.
- [ ] Add `source_records.jsonl` to track source URL, format, rights note,
  retrieval date, checksum, and adapter name.
- [ ] Implement a downloader that stores raw source files under
  `source_cache/raw/`.
- [ ] Implement normalization to UTF-8 text under `source_cache/normalized/`.
- [ ] Add duplicate detection by title, source URL, and text hash.
- [ ] Add failure logging for missing pages, blocked downloads, malformed files,
  and uncertain rights.

## Phase 3: Cleaning And Review

- [ ] Implement cleaner interfaces for HTML, plain text, EPUB, PDF, and OCR text.
- [ ] Add source-specific cleaning rules for the first adapter.
- [ ] Add fixture tests for forewords, footnotes, navigation text, scripture
  headers, and duplicated titles.
- [ ] Add a review report showing removed sections, word count, title, scripture
  reference, and theme suggestions.
- [ ] Add a command to accept cleaned text into the author directory.
- [ ] Add a command to reject or block a candidate with a reason.

## Phase 4: Theme And Catalog Automation

- [ ] Build deterministic keyword-based first-pass theme suggestions.
- [ ] Add optional LLM-based theme review after deterministic suggestions.
- [ ] Store reviewed themes in the catalog.
- [ ] Update author indexes from reviewed metadata.
- [ ] Add anthology membership fields and status tracking.
- [ ] Add quality checks for missing title, very short sermons, OCR noise, and
  suspicious boilerplate.

## Phase 5: TTS Job Packaging

- [ ] Map each author to a seed voice and prompt text.
- [ ] Create a job package format for Kaggle generation.
- [ ] Split long sermons into stable chunks with resumable ids.
- [ ] Generate audio-script variants when needed without changing the canonical
  sermon text.
- [ ] Update `kaggle_watcher.py` to associate downloads with `sermon_id`.
- [ ] Add post-generation checks for missing chunks, duration, clipping, silence,
  and file naming.
- [ ] Store approved audio under `output/audio/<author_id>/<sermon_id>/`.

## Phase 6: Long-Form Video Drafts

- [ ] Define visual template for each author or series.
- [ ] Define a reusable video style guide for animated sermon scenes: aspect
  ratio, safe caption areas, typography rules, color palette, motion limits, and
  tone guardrails.
- [ ] Choose the first prototype sermon and target a 60-90 second render before
  building the full-video workflow.
- [ ] Align generated audio with its source audio script to create phrase-level
  timestamps.
- [ ] Decide whether alignment uses forced alignment, speech-to-text timestamp
  recovery, or a hybrid script/audio matching workflow.
- [ ] Generate a caption timing format that can drive both long-form videos and
  short-form clips.
- [ ] Design dynamic caption overlays that appear above or around the
  congregation instead of only as bottom subtitles.
- [ ] Add caption emphasis rules for keywords, scripture references, quoted
  lines, paragraph transitions, and high-intensity sermon moments.
- [ ] Build the first reusable preacher-and-congregation scene with a pulpit,
  preacher figure, congregation figures, and simple background.
- [ ] Create a limited animation vocabulary: idle motion, arm gesture, pulpit
  lean, emphasis pose, congregation reaction, and camera push-in.
- [ ] Drive basic preacher motion from audio intensity, sentence boundaries, and
  selected text cues.
- [ ] Create per-author scene notes so each preacher has a distinct church
  atmosphere without rebuilding the whole renderer.
- [ ] Draft initial author scene directions for Spurgeon, Finney, Wesley,
  Tozer, Ravenhill, and George Muller.
- [ ] Decide on the rendering stack for template-based video generation, such as
  SVG/canvas, Remotion, MoviePy, Blender, or After Effects templates.
- [ ] Render a 60-90 second combined prototype with animated pulpit scene,
  dynamic captions, and approved sermon audio.
- [ ] Review whether the animation feels reverent, readable, and consistent
  before scaling to full-length sermons.
- [ ] Generate title, description, chapters, tags, and source note from catalog
  data.
- [ ] Render full sermon video from approved audio.
- [ ] Upload via YouTube API as private or draft only.
- [ ] Store YouTube video id, upload status, and approval state in the catalog.
- [ ] Add a manual approval command that can switch visibility to public.

## Phase 7: Short-Form Clips

- [ ] Identify candidate spans from sermon text.
- [ ] Score spans for standalone clarity, intensity, and connection to the
  long-form sermon.
- [ ] Map selected text spans to audio chunks and timestamps.
- [ ] Render vertical video with captions.
- [ ] Upload shorts as private/draft.
- [ ] Link shorts to the long-form video after approval.
- [ ] Track performance metadata for future clip selection.

## Phase 8: Anthologies And Audiobooks

- [ ] Define anthology records by theme, author, or series.
- [ ] Build Markdown anthology output from catalog-selected sermons.
- [ ] Export EPUB/PDF from reviewed Markdown.
- [ ] Assemble audiobook chapters from approved audio.
- [ ] Normalize audiobook loudness and spacing.
- [ ] Generate cover, title metadata, chapter metadata, and credits.
- [ ] Hold final audiobook distribution package for manual approval.

## Phase 9: Operations

- [ ] Add a dry-run mode for every publishing or distribution command.
- [ ] Add resumable job state for retrieval, cleaning, TTS, render, and upload.
- [ ] Add dashboard/report command for blocked records and records awaiting
  approval.
- [ ] Add backups for catalog and index updates.
- [ ] Add CI-style validation for JSON, Markdown links, catalog schema, and
  notebook JSON.
- [ ] Document common recovery paths in `KAGGLE_PIPELINE.md`.
