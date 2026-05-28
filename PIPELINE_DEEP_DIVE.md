# Deep Dive: The Sermon Anthology Production Pipeline

This document provides a detailed technical reference for the sermon audio and video production pipeline.

## 1. Core Concept: A State-Driven Content Workflow

The entire pipeline is best understood not as a single automated script, but as a **Content Management System (CMS)** centered around the master catalog file: `catalog/sermons.jsonl`.

This file acts as the "brain" of the operation. Each line is a JSON object representing a single sermon and tracking its progress through the production lifecycle. An operator manually runs different scripts (the "tools") to process a sermon, and then updates that sermon's entry in `sermons.jsonl` to reflect its new status.

### Key `sermons.jsonl` Schema Fields:

-   `sermon_id`: A unique identifier for the sermon.
-   `filename`: The path to the source `.md` text file.
-   `status`: The current stage of the sermon in the pipeline (e.g., `rights_review`, `tts_in_progress`, `blocked`, `tts_failed`).
-   `review`: A nested object with booleans (`text_approved`, `audio_approved`) that represents a manual Quality Assurance checklist.
-   `tts`: A nested object to track audio generation, including the `job_id` (for Kaggle), `output_dir`, and the `voice_seed` to use.
-   `youtube`: A nested object to store the final `long_form_video_id` and an array of `short_video_ids`, representing the final output of the pipeline.

## 2. The Production Lifecycle

The workflow consists of manually advancing a sermon through the following stages.

### Stage 1: Ingestion and Curation

1.  **Trigger:** The process begins when a new sermon is acquired (as you described, likely via an LLM process or manual curation).
2.  **Artifacts:** A new `.md` file is created in the appropriate author directory (e.g., `Charles Spurgeon/`).
3.  **Catalog Entry:** A corresponding JSON line is added to `catalog/sermons.jsonl`.
4.  **Initial Status:** The `status` is set to `rights_review` or `blocked` (e.g., for authors like A.W. Tozer whose work is not yet in the public domain).

### Stage 2: Audio Generation (The "Toolbox")

Once a sermon is ready for audio generation, the operator chooses one of the following tools based on the desired outcome.

#### Tool A: Local XTTS v2 Generator

-   **Scripts:** `generate_sermon_batch.py`, `generate_finney.py`, `generate_spurgeon.py`
-   **Description:** These are scripts for generating audio locally using the `Coqui-AI/TTS` library with the `xtts_v2` model. The `generate_sermon_batch.py` script is specifically designed for long-form content. It cleans the markdown, splits the text into smaller chunks, and generates a separate `.wav` file for each chunk into an `output/` directory.
-   **Workflow:**
    1.  Configure the `SERMON_PATH`, `SEED_PATH`, and `OUTPUT_DIR` in the script.
    2.  Run the script: `python generate_sermon_batch.py`.
    3.  Manually merge the resulting chunks using the `ffmpeg` command printed by the script upon completion.
-   **Pros:** Runs locally, simple to set up for a single file.
-   **Cons:** Requires a manual merge step, does not support emotional control tags (it actively strips them out).

#### Tool B: Expressive Fish-Speech Generator (Colab)

-   **Script:** `Fish_Speech_Sermon_Generator.ipynb`
-   **Description:** This Jupyter Notebook is optimized for Google Colab and uses a smaller, non-gated version of the `Fish-Speech` model (`s1-mini`). Its primary advantage is the support for **inline emotional tags** (e.g., `[solemn]`, `[whisper]`, `[excited]`, `[pause]`) for highly expressive and nuanced audio generation.
-   **Workflow:**
    1.  Open the notebook in Google Colab.
    2.  Upload the required `spurgeon_seed.wav` file.
    3.  Paste the sermon text into the `sermon_script` variable, including any emotional tags.
    4.  Run the notebook cells in order. The output is saved as `fake.wav` and can be played directly in the notebook.
-   **Pros:** **Enables fine-grained emotional control**, easy to run in a free Colab environment.
-   **Cons:** A more manual copy-paste workflow for the text.

#### Tool C: High-Quality Qwen3-TTS Generator (Kaggle)

-   **Script:** `qwen3_tts_sermon_generator.ipynb`
-   **Description:** A self-contained notebook designed for high-quality voice cloning on Kaggle's GPU infrastructure. Its standout feature is the **"AI Listener,"** which uses `openai-whisper` to transcribe the generated audio, providing an automated quality check by comparing the transcription to the original text.
-   **Workflow:** This notebook is designed to be run as part of the Kaggle Offloading process (see Section 3).
-   **Pros:** High-quality model, includes an automated quality verification step.
-   **Cons:** Requires using the Kaggle platform.

#### Tool D: The "Pro" Fish-Speech Kaggle Pipeline (Legacy/Complex)

-   **Documentation:** `KAGGLE_PIPELINE.md`
-   **Description:** This document outlines a complex, multi-step workflow for running a professional-grade `Fish-Speech v1.5.1` model on Kaggle. It details specific workarounds for dependency issues (`pyaudio`), deprecated CLIs (`huggingface-cli`), and the model's specific prompt requirements (it requires pre-computed prompt tokens, not a direct audio file). This workflow appears to be older and more complex than the Qwen3-TTS process.
-   **Pros:** Uses a more powerful "pro" model.
-   **Cons:** Highly complex, requires specific dependency management, and is largely superseded by the simpler Qwen3 and Colab Fish-Speech workflows.

### Stage 3: Kaggle Offloading & Monitoring

For the GPU-intensive `Qwen3-TTS` and "Pro" `Fish-Speech` workflows, the process is:

1.  **Push:** The developer pushes the notebook to Kaggle using the CLI, ensuring the `kernel-metadata.json` is correctly configured with the right GPU type, datasets, etc.
    -   `kaggle kernels push -p /path/to/notebook/dir`
2.  **Monitor:** The `kaggle_watcher.py` script is run locally to poll the job status.
    -   `python kaggle_watcher.py <username>/<kernel-slug>`
3.  **Download:** When the watcher detects the `complete` status, it automatically downloads the output `.wav` files into the specified directory.

### Stage 4: QA, Assembly, and Publication

1.  **Manual Review:** The operator listens to the generated audio. If it meets quality standards, they update the `review` object in `sermons.jsonl` (e.g., `audio_approved: true`).
2.  **Anthology/Video Creation:** Downstream processes (which are not explicitly defined in the scripts but implied by the project structure) use the approved audio and assets from the `assets/` directory to create the final video products.
3.  **Final Catalog Update:** Once a video is created and uploaded, the operator updates the `youtube` object in `sermons.jsonl` with the new video IDs, completing the lifecycle for that sermon.
