# Kaggle Deployment Pipeline: Fish Speech Sermon Generator

This document tracks the working Kaggle API pipeline for the Fish Speech sermon
TTS notebook.

## 1. Current Kaggle Target

- **Kaggle notebook ID**: `nathanpurcella/fish-speech-sermon-generator-hf`
- **Kaggle URL**: <https://www.kaggle.com/code/nathanpurcella/fish-speech-sermon-generator-hf>
- **Active notebook file**: `fish_speech_sermon.ipynb`
- **Fish Speech version**: `v1.5.1`
- **GPU target**: Kaggle P100/T4
- **Dataset input**: `nathanpurcella/spurgeon-seed-audio`
- **Expected seed file**: `spurgeon_seed.wav`

## 2. Qwen3-TTS Standalone Target

- **Kaggle notebook ID**: `nathanpurcella/qwen3-tts-sermon-generator`
- **Kaggle URL**: <https://www.kaggle.com/code/nathanpurcella/qwen3-tts-sermon-generator>
- **Active notebook file**: `qwen3_tts_sermon_generator.ipynb`
- **GPU target**: Kaggle T4/P100 (Required for reasonable inference time)
- **Dataset input**: `nathanpurcella/spurgeon-seed-audio`

## 3. Prerequisites

- Kaggle API credentials available to the local `kaggle` CLI.
- Internet enabled in the Kaggle notebook metadata.
- GPU enabled in the Kaggle notebook metadata.
- The `spurgeon-seed-audio` dataset attached to the notebook.

Standard local Kaggle API setup:

```bash
pip install kaggle
mkdir -p ~/.kaggle
mv path/to/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

## 3. Push Workflow

The active notebook was pushed as a new Kaggle notebook using a clean staging
directory so the old repo-level metadata would not overwrite the wrong notebook.

Expected staging metadata:

```json
{
  "id": "nathanpurcella/fish-speech-sermon-generator-hf",
  "title": "Fish Speech Sermon Generator HF",
  "code_file": "fish_speech_sermon.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": ["nathanpurcella/spurgeon-seed-audio"],
  "competition_sources": [],
  "kernel_sources": []
}
```

Push command:

```bash
kaggle kernels push -p /tmp/kaggle-fish-speech-sermon-hf
```

Status command:

```bash
kaggle kernels status nathanpurcella/fish-speech-sermon-generator-hf
```

Download output/logs:

```bash
kaggle kernels output nathanpurcella/fish-speech-sermon-generator-hf -p ./output
```

For debugging, downloading to a temp directory is useful:

```bash
mkdir -p /tmp/kaggle-hf-output
kaggle kernels output nathanpurcella/fish-speech-sermon-generator-hf -p /tmp/kaggle-hf-output
```

## 4. Notebook Fixes Applied

### Hugging Face Download

The original notebook used:

```python
!huggingface-cli download ...
```

That CLI is deprecated. Replacing it with `hf download` avoided the deprecation
message but introduced a new Kaggle blocker: `hf` prompted interactively to
update `huggingface_hub`.

Current fix: use the Python API instead.

```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="fishaudio/fish-speech-1.5",
    local_dir=CHECKPOINT_DIR,
)
```

### `pyaudio` Build Failure

Fish Speech `v1.5.1` declares `pyaudio`, which fails to build on Kaggle. The
offline generation path does not need it.

Current fix:

```python
!pip install -e . --no-deps -q
```

Then install the runtime dependencies explicitly, including `loguru`, `lightning`,
`hydra-core`, `vector_quantize_pytorch`, `faster_whisper`, `funasr`, and related
packages.

### Torch and NumPy Pins

The notebook pins torch after dependency installation:

```python
!pip install -q --force-reinstall \
    torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu121
```

The torch reinstall can disturb NumPy, so NumPy is re-pinned afterward:

```python
!pip install -q --force-reinstall numpy==1.26.4
```

### Fish Speech v1.5.1 Prompt Flow

Fish Speech `v1.5.1` text-to-semantic inference does **not** accept
`--prompt-audio`. It expects precomputed prompt tokens.

Current flow:

1. Encode the reference WAV with `fish_speech.models.vqgan.inference`.
2. Save prompt tokens as `prompt_tokens.npy`.
3. Pass `--prompt-tokens prompt_tokens.npy` to text-to-semantic inference.

Relevant command structure:

```python
subprocess.run([
    "python", "-m", "fish_speech.models.vqgan.inference",
    "-i", REFERENCE_AUDIO,
    "-o", "prompt_tokens.wav",
    "--checkpoint-path", VOCODER_CKPT,
], check=True)

subprocess.run([
    "python", "-m", "fish_speech.models.text2semantic.inference",
    "--text", sermon_script,
    "--prompt-text", prompt_text,
    "--prompt-tokens", "prompt_tokens.npy",
    "--checkpoint-path", CHECKPOINT_DIR,
    "--num-samples", "1",
    "--half",
], check=True)
```

`--half` is used because the run has been landing on a Tesla P100, and the script
defaults to bfloat16 when `--half` is not set.

### Codec Symlink

The notebook creates an absolute symlink:

```python
codec.pth -> firefly-gan-vq-fsq-8x1024-21hz-generator.pth
```

This avoids broken relative links inside the Kaggle working directory.

## 5. Failure History

- **Version 1**: Replaced `huggingface-cli` with `hf`, but `hf` hung on an
  interactive `huggingface_hub` update prompt.
- **Version 2**: Switched to `snapshot_download`; model download worked, but
  Stage 1 failed with `ModuleNotFoundError: No module named 'loguru'` because
  `pip install -e .` had failed earlier on `pyaudio`.
- **Version 3**: Installed package with `--no-deps` and explicit runtime deps;
  Stage 1 then failed because `--prompt-audio` is not a valid option in
  Fish Speech `v1.5.1`.
- **Version 4**: Added reference-audio-to-prompt-token encoding and switched
  Stage 1 to `--prompt-tokens`. This run moved into long generation.

## 6. Monitoring Notes

The current run may take a long time for sermon-length text. Once it reports
`KernelWorkerStatus.COMPLETED`, download output and confirm that
`sermon_output.wav` exists.

As of May 27, 2026, the Kaggle UI showed the notebook generating roughly 7,000
pieces. Automated status polling was stopped at the user's request; resume with
the status command above only when an explicit check is needed.

If it reports `KernelWorkerStatus.ERROR`, pull the log bundle:

```bash
mkdir -p /tmp/kaggle-hf-error-output
kaggle kernels output nathanpurcella/fish-speech-sermon-generator-hf -p /tmp/kaggle-hf-error-output
tail -200 /tmp/kaggle-hf-error-output/fish-speech-sermon-generator-hf.log
```
