# End-to-End Orchestration Script Plan

## Objective
Create a dedicated orchestration script (`pipeline/orchestrate_e2e.py`) to manage the complete end-to-end generation of an animated sermon video. The script will handle autonomous LLM-based text retrieval (if necessary), text-to-speech generation, audio quality verification, caption alignment, and final video rendering, bridging the gaps between different Python environments.

## Scope & Impact
- **New Script:** `pipeline/orchestrate_e2e.py`
- **Impact:** This will unify the currently disjointed scripts (`generate_spurgeon.py`, `verify_quality.py`, `align_captions.py`, `generate_long_video.py`) into a single, automated workflow with robust error handling and environment switching.

## Proposed Solution

### 1. Entry Point and Argument Parsing
The script will accept an optional `--sermon-id` argument.
- **If `--sermon-id` is provided:** The pipeline begins directly at the audio generation phase for that specific catalog entry.
- **If `--sermon-id` is omitted:** The script will execute an `antigravity` CLI command to autonomously prompt an LLM to retrieve a public domain sermon, process it into the catalog, and return the newly generated `sermon_id`. The orchestrator will parse this ID and continue.

### 2. Environment Handoffs
Different stages of the pipeline require specific Python virtual environments due to conflicting dependencies (e.g., XTTS vs. Whisper/Video tools). The orchestrator will use `subprocess.run` to call each script within its required environment:
- **Audio Generation:** Uses `xtts_env`
- **Quality Verification:** Uses `qwen_tts_project/venv` (or `video_env` if Whisper is consolidated)
- **Captioning & Video:** Uses `video_env`

### 3. Pipeline Stages & Failure Hooks
The orchestrator will execute the following steps sequentially. If any step returns a non-zero exit code, the orchestrator will catch the `subprocess.CalledProcessError`, log a clear failure message detailing which stage failed, and exit gracefully without proceeding to the next step.

1.  **Autonomous Retrieval (Conditional):** Call `antigravity` to fetch text and create a catalog entry. Extract the `sermon_id`.
2.  **Audio Generation:** Call `generate_spurgeon.py` (or a generalized version) using the `xtts_env` to synthesize the sermon text into a WAV file.
3.  **Quality Verification:** Call `verify_quality.py` to transcribe the generated audio and compare it against the source text. If the discrepancy threshold is exceeded, the script will exit.
4.  **Caption Alignment:** Call `align_captions.py` using `video_env` to generate `captions.json`.
5.  **Video Rendering:** Call `generate_long_video.py` using `video_env` to produce the final `mp4`.

## Implementation Steps
1.  Create `pipeline/orchestrate_e2e.py`.
2.  Implement the `argparse` logic for the optional `--sermon-id`.
3.  Implement the `antigravity` subprocess call for the autonomous retrieval path.
4.  Implement the sequence of `subprocess.run` calls, ensuring the correct environment python binaries (`xtts_env/bin/python3`, `video_env/bin/python3`, etc.) are used for each respective script.
5.  Add error handling (`try/except subprocess.CalledProcessError`) around each stage to act as failure hooks.

## Verification
- Test the script by providing a known, valid `--sermon-id` (e.g., `MTP-0501-Grace_Abounding`) and verify it runs through to video generation.
- Test the script without arguments to ensure the `antigravity` call is triggered correctly.
- Intentionally cause a failure (e.g., by providing an invalid ID) to ensure the script halts gracefully and reports the error.
