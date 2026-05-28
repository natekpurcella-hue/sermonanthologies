# Repository Guidelines

## Project Structure & Module Organization

This repository is a Markdown sermon corpus with Python tooling for audio
generation. Author collections live in top-level directories such as
`Charles Spurgeon/`, `Finney/`, `George Muller/`, `Wesley/`, `AW Tozer/`, and
`Ravenhill/`; keep each `INDEX.md` updated when sermons change. Shared material
lives in `Anthologies/`, `SERMON_CONTEXTS.md`, and `PROJECT_STATUS.md`. TTS and
Kaggle workflow files are at the root: `fish_speech_sermon.ipynb`,
`Fish_Speech_Sermon_Generator*.ipynb`, `generate_*.py`, `kaggle_watcher.py`,
`kernel-metadata.json`, and `KAGGLE_PIPELINE.md`. The `fish-speech/` directory
is vendored upstream code; avoid broad edits unless intentional. Generated logs,
checkpoints, virtualenvs, and WAVs belong under `output/`, `checkpoints/`,
`fish_env/`, `test_venv/`, or `xtts_env/`.

## Build, Test, and Development Commands

- `python3 -m json.tool fish_speech_sermon.ipynb >/dev/null`: validate notebook
  JSON after manual edits.
- `python3 generate_spurgeon.py` or `python3 generate_sermon_batch.py`: run local
  generation scripts; inspect arguments before launching long jobs.
- `kaggle kernels push -p /tmp/kaggle-fish-speech-sermon-hf`: push the staged
  Kaggle notebook described in `KAGGLE_PIPELINE.md`.
- `kaggle kernels status nathanpurcella/fish-speech-sermon-generator-hf`: check
  Kaggle state only when explicitly needed.
- `pip install -r requirements_no_pyaudio.txt`: install local Fish Speech
  dependencies without the Kaggle-blocking `pyaudio` path.

## Coding Style & Naming Conventions

Use Python 3, four-space indentation, descriptive `snake_case` names, and
explicit constants near the top of scripts. Keep notebook cells reproducible and
avoid hidden local paths. Sermon Markdown filenames should include author or
series context plus a stable title, for example
`MTP-0003-The Sin of Unbelief.md` or
`Finney-Revival-Lecture-04-PREVAILING_PRAYER.md`. Preserve existing title
capitalization patterns inside each author directory.

## Testing Guidelines

There is no full automated test suite in the root project. For content changes,
verify links and update the relevant `INDEX.md`. For Python and notebook changes,
run `python3 -m py_compile generate_spurgeon.py` and validate notebooks with
`json.tool`. For Kaggle changes, document failures and fixes in
`KAGGLE_PIPELINE.md` before pushing.

## Commit & Pull Request Guidelines

Recent commits use concise, imperative summaries such as `Add INDEX.md and clean
sermons for all authors`. Start with a verb, name the affected content or
workflow, and keep the subject under about 72 characters. Pull requests should
include purpose, changed paths, validation performed, and any generated artifacts
intentionally excluded.

## Security & Configuration Tips

Do not commit Kaggle credentials, Hugging Face tokens, private API keys, model
checkpoints, or generated bulk audio. Keep runtime secrets in local config or the
Kaggle environment, and prefer documenting reproducible commands over committing
machine-specific paths.
