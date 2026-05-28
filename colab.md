# Google Colab Setup for Sermon Audio Generation

Use this guide to generate high-quality audio for your sermons using Google Colab's GPUs.

## 1. Environment Setup
Run this cell first to install the necessary libraries and dependencies.

```python
# Install Coqui TTS and specific transformers version for stability
!pip install TTS transformers<4.34.0
!apt-get install -y ffmpeg

# Set environment variable to agree to Coqui's terms
import os
os.environ["COQUI_TOS_AGREED"] = "1"
```

## 2. File Preparation
Upload the following files to the Colab file browser (left sidebar):
1. The sermon Markdown file (e.g., `MTP-0003-The Sin of Unbelief.md`)
2. The speaker seed WAV file (e.g., `spurgeon_seed.wav`)

## 3. Batch Generation Script
This script is optimized for GPU (`cuda`) and includes automatic chunking and merging.

```python
import os
import re
import torch
from TTS.api import TTS
from pathlib import Path

# --- SETTINGS ---
SERMON_PATH = "MTP-0003-The Sin of Unbelief.md"  # Replace with your filename
SEED_PATH = "spurgeon_seed.wav"               # Replace with your seed filename
OUTPUT_DIR = "chunks"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
LANGUAGE = "en"

# Create output directory
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def clean_text(text):
    # Remove Markdown headers
    text = re.sub(r'^#+.*$', '', text, flags=re.MULTILINE)
    # Remove dynamic markers
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def split_text(text, max_chars=250):
    # Split by punctuation to maintain natural pauses
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += " " + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

# --- Initialize TTS ---
print(f"Loading XTTS v2 on {DEVICE}...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(DEVICE)

# --- Process Sermon ---
with open(SERMON_PATH, 'r') as f:
    raw_text = f.read()

cleaned_text = clean_text(raw_text)
chunks = split_text(cleaned_text)

print(f"Total chunks to process: {len(chunks)}")

for i, chunk in enumerate(chunks):
    chunk_filename = f"chunk_{i:03d}.wav"
    chunk_path = os.path.join(OUTPUT_DIR, chunk_filename)
    
    if os.path.exists(chunk_path):
        continue
        
    print(f"[{i+1}/{len(chunks)}] Processing...")
    tts.tts_to_file(
        text=chunk,
        speaker_wav=SEED_PATH,
        language=LANGUAGE,
        file_path=chunk_path
    )

# --- Merge Chunks ---
print("\nMerging audio files...")
# Create a temporary file list for ffmpeg
with open("filelist.txt", "w") as f:
    # Sort files to ensure correct order
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".wav")])
    for filename in files:
        f.write(f"file '{OUTPUT_DIR}/{filename}'\n")

# Run ffmpeg concat
output_filename = SERMON_PATH.replace('.md', '.wav')
!ffmpeg -f concat -safe 0 -i filelist.txt -c copy "{output_filename}"

print(f"\nSUCCESS: {output_filename} generated!")
```
