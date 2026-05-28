# Project Status: Fish Speech Sermon Generator

## 1. Migration to Kaggle (Primary Pipeline)
The project has been migrated to Kaggle to leverage better GPU availability (P100/T4) and stable environments.
- **Notebook**: `Fish_Speech_Sermon_Generator_Kaggle.ipynb` (currently at **Version 8**).
- **Kaggle ID**: `nathanpurcella/fish-speech-sermon-generator`.
- **Mirror Bypassed**: All `apt-get` commands removed to avoid unresponsive Ubuntu mirrors.
- **NMS Fix**: Pinned `torchvision==0.21.0` and `torch==2.8.0` to resolve the `nms does not exist` error.
- **Dataset Input**: Notebook is configured to automatically find `spurgeon_seed.wav` under `/kaggle/input/`.

## 2. Automation & CLI Tools
- **Global CLI**: Kaggle API installed via `pipx` for agnostic system-wide use.
- **Watcher Script**: `kaggle_watcher.py` created to poll status and auto-download results.
- **Metadata**: `kernel-metadata.json` configured for private, GPU-enabled runs.

## 3. Local Fallback Environment
- **Environment**: `fish_env` (Python 3.12).
- **Status**: Installed `fish-speech` (editable) and downloaded standard `1.5` checkpoints.
- **Note**: CPU generation is available but extremely slow compared to Kaggle.

## 4. Pending Actions (Next Session)
1. **Kaggle Attachment**: Ensure the `spurgeon_seed` dataset is "Attached" to the notebook in the Kaggle Web UI sidebar.
2. **First Successful Run**: Monitor Version 8 for completion and download `sermon_output.wav`.
3. **Option B (Caching)**: Once a run succeeds, export the environment to a Kaggle Dataset to reduce setup time from 15 mins to 30 seconds.
4. **Webhook Integration**: Add actual webhook URL to the notebook for real-time notifications.
