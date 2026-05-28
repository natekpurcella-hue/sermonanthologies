import os
import re
import torch
from TTS.api import TTS
from pathlib import Path

# --- Configuration ---
SERMON_PATH = "Charles Spurgeon/MTP-0003-The Sin of Unbelief.md"
SEED_PATH = "seeds/spurgeon/spurgeon_seed.wav"
OUTPUT_DIR = "output/spurgeon_unbelief"
DEVICE = "cpu"
LANGUAGE = "en"

# Create output directory
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def clean_text(text):
    # Remove Markdown headers
    text = re.sub(r'^#+.*$', '', text, flags=re.MULTILINE)
    # Remove dynamic markers like (Grave, Narrative Weight) or [breath]
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def split_text(text, max_chars=250):
    # XTTS works best with shorter chunks (sentences or small paragraphs)
    # We split by punctuation to keep natural flow
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

# --- Execution ---
print("Loading XTTS v2 model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(DEVICE)

print(f"Reading sermon: {SERMON_PATH}")
with open(SERMON_PATH, 'r') as f:
    raw_text = f.read()

cleaned_text = clean_text(raw_text)
chunks = split_text(cleaned_text)

print(f"Total chunks to process: {len(chunks)}")

for i, chunk in enumerate(chunks):
    chunk_filename = f"chunk_{i:03d}.wav"
    chunk_path = os.path.join(OUTPUT_DIR, chunk_filename)
    
    if os.path.exists(chunk_path):
        print(f"Skipping {chunk_filename} (already exists)")
        continue
        
    print(f"[{i+1}/{len(chunks)}] Generating: {chunk[:50]}...")
    try:
        tts.tts_to_file(
            text=chunk,
            speaker_wav=SEED_PATH,
            language=LANGUAGE,
            file_path=chunk_path
        )
    except Exception as e:
        print(f"Error on chunk {i}: {e}")

print(f"\nAll chunks generated in: {OUTPUT_DIR}")
print("To merge them, run:")
print(f"ffmpeg -f concat -safe 0 -i <(for f in {OUTPUT_DIR}/*.wav; do echo \"file '$PWD/$f'\"; done) -c copy spurgeon_unbelief_full.wav")
