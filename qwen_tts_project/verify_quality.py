import whisper
import sys
import json
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
AUDIO_DIR = ROOT / "output/final_sermons"

def load_sermon_record(sermon_id):
    if not CATALOG_PATH.exists():
        return None
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            if record["sermon_id"] == sermon_id:
                return record
    return None

def clean_text_for_comparison(text):
    """Basic cleaning to remove markdown and LLM tags."""
    text = re.sub(r"^#+\s+.*$", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
    text = re.sub(r"\[[a-zA-Z\s]+\]", "", text)
    return text

def verify(audio_path, original_text, threshold=0.1):
    print(f"--- Verifying Quality for {audio_path.name} ---")
    if not audio_path.exists():
        print(f"Error: {audio_path} not found.")
        return False

    # Load the Whisper model
    print("Loading Whisper model (base)...")
    # Whisper base is usually enough for quality sanity checks
    model = whisper.load_model("base")

    # Transcribe the audio
    print("Transcribing audio...")
    result = model.transcribe(str(audio_path))
    transcribed_text = result["text"].strip()

    print("\n--- Comparison Report ---")
    print(f"ORIGINAL (start):    {original_text[:100]}...")
    print(f"TRANSCRIBED (start): {transcribed_text[:100]}...")
    
    # Basic word match check
    orig_words = set(original_text.lower().split())
    trans_words = set(transcribed_text.lower().split())
    
    missing = orig_words - trans_words
    hallucinated = trans_words - orig_words
    
    print(f"\nMissing keywords (potential skips): {list(missing)[:15]}")
    # print(f"Extra words (potential hallucinations): {list(hallucinated)[:10]}")
    
    missing_ratio = len(missing) / len(orig_words) if orig_words else 0
    print(f"\nMissing Ratio: {missing_ratio:.2%}")

    if missing_ratio <= threshold:
        print("\n✅ Quality check passed!")
        return True
    else:
        print(f"\n⚠️ Quality check failed! Missing ratio ({missing_ratio:.2%}) exceeds threshold ({threshold:.2%}).")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify audio quality against sermon text.")
    parser.add_argument("sermon_id", help="The ID of the sermon in the catalog")
    parser.add_argument("--audio-path", help="Override path to the audio file")
    parser.add_argument("--threshold", type=float, default=0.25, help="Failure threshold for missing words ratio")
    parser.add_argument("--max-chars", type=int, help="Limit original text to first N characters for comparison")
    
    args = parser.parse_args()

    record = load_sermon_record(args.sermon_id)
    if not record:
        print(f"Error: Sermon {args.sermon_id} not found in catalog.")
        sys.exit(1)

    # Determine source text (prefer Audio-Script)
    author_id = record["author_id"]
    base_name = Path(record["filename"]).stem
    audio_script_path = ROOT / "pipeline/audio_scripts" / author_id / f"{base_name}-Audio-Script.md"
    
    if audio_script_path.exists():
        source_path = audio_script_path
    else:
        source_path = ROOT / record["filename"]

    with open(source_path, "r", encoding="utf-8") as f:
        text = clean_text_for_comparison(f.read())

    if args.max_chars:
        text = text[:args.max_chars]
        last_space = text.rfind(" ")
        if last_space != -1:
            text = text[:last_space]

    # Audio Path
    if args.audio_path:
        audio_path = Path(args.audio_path)
    else:
        audio_path = AUDIO_DIR / f"{args.sermon_id}.wav"

    success = verify(audio_path, text, threshold=args.threshold)
    if not success:
        sys.exit(1)
