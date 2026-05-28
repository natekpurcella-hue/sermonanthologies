#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path

# Important: This script is intended to be run within the 'xtts_env' virtual environment.

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
OUTPUT_DIR = ROOT / "output/final_sermons"

def load_sermon_record(sermon_id):
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Catalog not found at {CATALOG_PATH}")
    
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            if record["sermon_id"] == sermon_id:
                return record
    return None

def clean_text_for_xtts(text):
    """
    Basic cleaning of Markdown to plain text for XTTS.
    Removes headers, bold/italic markers, and potential LLM-injected [tags].
    """
    # Remove Markdown headers (# Header)
    text = re.sub(r"^#+\s+.*$", "", text, flags=re.MULTILINE)
    # Remove Bold/Italic
    text = text.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
    # Remove [emotional tags] or [pause] injected by LLM
    text = re.sub(r"\[[a-zA-Z\s]+\]", "", text)
    # Remove metadata lines like "Scripture:", "At the...", etc. if they are at the top
    # (Optional: might be better to keep them if they are part of the sermon)
    
    # Normalize whitespace
    text = " ".join(text.split())
    return text

def main():
    parser = argparse.ArgumentParser(description="Generate audio for a sermon using XTTS v2")
    parser.add_argument("sermon_id", help="The ID of the sermon in the catalog")
    parser.add_argument("--output", help="Override output path")
    parser.add_argument("--max-chars", type=int, help="Limit characters for short tests")
    
    args = parser.parse_args()
    
    record = load_sermon_record(args.sermon_id)
    if not record:
        print(f"Error: Sermon {args.sermon_id} not found in catalog.")
        return

    # Determine source text
    # Prefer Audio-Script if it exists, otherwise use raw filename
    author_id = record["author_id"]
    base_name = Path(record["filename"]).stem
    audio_script_path = ROOT / "pipeline/audio_scripts" / author_id / f"{base_name}-Audio-Script.md"
    
    if audio_script_path.exists():
        print(f"Using Audio-Script: {audio_script_path.relative_to(ROOT)}")
        source_path = audio_script_path
    else:
        source_path = ROOT / record["filename"]
        print(f"Using raw sermon text: {source_path.relative_to(ROOT)}")

    with open(source_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Apply phonetic normalization (e.g., 2 Kings -> Second Kings)
    try:
        from tools.phonetic_normalizer import normalize_text
    except ImportError:
        try:
            from phonetic_normalizer import normalize_text
        except ImportError:
            print("Warning: phonetic_normalizer not found. Skipping normalization.")
            def normalize_text(t): return t

    raw_text = normalize_text(raw_text)
    text = clean_text_for_xtts(raw_text)
    if args.max_chars:
        text = text[:args.max_chars]
        # Try to break at a space
        last_space = text.rfind(" ")
        if last_space != -1:
            text = text[:last_space]

    print(f"Text length: {len(text)} characters.")

    # Voice Seed
    voice_seed = record["tts"].get("voice_seed")
    if not voice_seed:
        # Fallback to a default if not specified
        voice_seed = f"seeds/{author_id}/{author_id}_seed.wav"
    
    voice_seed_path = ROOT / voice_seed
    if not voice_seed_path.exists():
        print(f"Error: Voice seed not found at {voice_seed_path}")
        return

    # Output Path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = OUTPUT_DIR / f"{args.sermon_id}.wav"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Synthesis
    try:
        import torch
        from TTS.api import TTS
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading XTTS v2 model on {device}...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

        print(f"Generating audio to: {output_path.relative_to(ROOT)} ...")
        tts.tts_to_file(
            text=text,
            speaker_wav=str(voice_seed_path),
            language="en",
            file_path=str(output_path)
        )
        print("Audio generation complete.")

    except ImportError:
        print("Error: TTS or torch not found in current environment.")
        print("Make sure to run this script in 'xtts_env'.")
    except Exception as e:
        print(f"An error occurred during synthesis: {e}")

if __name__ == "__main__":
    main()
