#!/usr/bin/env python3
"""
align_captions.py — Extract word-level timestamps from a sermon WAV using Whisper,
then group them into short caption phrases.

Usage:
    python align_captions.py <sermon_id> [options]
    python align_captions.py spurgeon-mtp-0003 --max-duration 90 --model medium

Output:
    captions.json — list of { "start": float, "end": float, "text": str }
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
OUTPUT_DIR = ROOT / "output/captions"

# Phrase grouping rules
MAX_WORDS_PER_PHRASE = 7
MAX_PHRASE_DURATION = 4.0   # seconds — never hold a caption longer than this
PAUSE_THRESHOLD = 0.4        # gap between words that forces a phrase break


def load_sermon_record(sermon_id: str) -> dict:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record["sermon_id"] == sermon_id:
                return record
    raise ValueError(f"Sermon '{sermon_id}' not found in catalog.")


def resolve_audio_path(sermon_id: str, override: str | None) -> Path:
    if override:
        p = Path(override)
        return p if p.is_absolute() else ROOT / p
    # Check standard locations
    candidates = [
        ROOT / "output" / "final_sermons" / f"{sermon_id}.wav",
        ROOT / f"{sermon_id}.wav",
        ROOT / "spurgeon_unbelief_full.wav",  # fallback for mtp-0003
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"No audio file found for {sermon_id}. "
        f"Pass --audio-path explicitly."
    )


def trim_audio_if_needed(audio_path: Path, max_duration: float | None, tmp_dir: Path) -> Path:
    """Use ffmpeg to trim audio to max_duration if specified."""
    if max_duration is None:
        return audio_path
    import subprocess
    trimmed = tmp_dir / "trimmed.wav"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-t", str(max_duration),
            "-c", "copy",
            str(trimmed),
        ],
        check=True,
        capture_output=True,
    )
    return trimmed


def extract_word_timestamps(audio_path: Path, model_name: str, language: str = "en") -> list[dict]:
    """Run Whisper with word_timestamps=True and return flat word list."""
    import whisper

    print(f"Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)

    print(f"Transcribing: {audio_path.name} ...")
    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        verbose=False,
    )

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            word_text = w.get("word", "").strip()
            if not word_text:
                continue
            words.append({
                "word": word_text,
                "start": round(w["start"], 3),
                "end": round(w["end"], 3),
            })
    print(f"Extracted {len(words)} word timestamps.")
    return words


def group_into_phrases(words: list[dict]) -> list[dict]:
    """Group word-level timestamps into caption phrases."""
    if not words:
        return []

    phrases = []
    current_words = []
    current_start = words[0]["start"]

    for i, word in enumerate(words):
        current_words.append(word["word"])
        current_end = word["end"]

        # Check break conditions
        gap_after = (words[i + 1]["start"] - word["end"]) if i + 1 < len(words) else 999
        duration = current_end - current_start
        at_punctuation = bool(re.search(r"[.!?,;:]$", word["word"]))

        should_break = (
            len(current_words) >= MAX_WORDS_PER_PHRASE
            or duration >= MAX_PHRASE_DURATION
            or gap_after >= PAUSE_THRESHOLD
            or (at_punctuation and len(current_words) >= 3)
        )

        if should_break:
            phrase_text = " ".join(current_words).strip()
            phrase_text = re.sub(r"\s+([.,!?;:])", r"\1", phrase_text)
            phrases.append({
                "start": round(current_start, 3),
                "end": round(current_end, 3),
                "text": phrase_text,
            })
            # Start next phrase
            if i + 1 < len(words):
                current_start = words[i + 1]["start"]
            current_words = []

    # Flush any remainder
    if current_words:
        phrase_text = " ".join(current_words).strip()
        phrase_text = re.sub(r"\s+([.,!?;:])", r"\1", phrase_text)
        phrases.append({
            "start": round(current_start, 3),
            "end": round(words[-1]["end"], 3),
            "text": phrase_text,
        })

    print(f"Grouped into {len(phrases)} caption phrases.")
    return phrases


def detect_sentence_boundaries(words: list[dict]) -> list[float]:
    """Return timestamps of sentence-ending words (for the animation timeline)."""
    boundaries = []
    for word in words:
        if re.search(r"[.!?]$", word["word"]):
            boundaries.append(word["end"])
    return boundaries


def align_captions(
    sermon_id: str,
    audio_path_override: str | None = None,
    max_duration: float | None = None,
    model_name: str = "medium",
    output_path_override: str | None = None,
) -> Path:
    import tempfile

    audio_path = resolve_audio_path(sermon_id, audio_path_override)
    print(f"Audio: {audio_path}")

    with tempfile.TemporaryDirectory(prefix="sermon-align-") as tmp_str:
        tmp_dir = Path(tmp_str)
        working_audio = trim_audio_if_needed(audio_path, max_duration, tmp_dir)

        words = extract_word_timestamps(working_audio, model_name)
        phrases = group_into_phrases(words)
        sentence_boundaries = detect_sentence_boundaries(words)

    # Output
    if output_path_override:
        out_dir = Path(output_path_override).parent
        captions_path = Path(output_path_override)
    else:
        out_dir = OUTPUT_DIR / sermon_id
        out_dir.mkdir(parents=True, exist_ok=True)
        captions_path = out_dir / "captions.json"

    output = {
        "sermon_id": sermon_id,
        "model": model_name,
        "max_duration": max_duration,
        "phrase_count": len(phrases),
        "sentence_boundaries": sentence_boundaries,
        "phrases": phrases,
    }

    with open(captions_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Captions written to: {captions_path.relative_to(ROOT)}")
    return captions_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Whisper-aligned captions from sermon audio.")
    parser.add_argument("sermon_id", help="Sermon ID from the catalog")
    parser.add_argument("--audio-path", help="Override path to sermon WAV")
    parser.add_argument("--max-duration", type=float, help="Only process first N seconds (for prototyping)")
    parser.add_argument("--model", default="medium", help="Whisper model size: tiny, base, small, medium, large")
    parser.add_argument("--output", help="Override output path for captions.json")
    args = parser.parse_args()

    align_captions(
        sermon_id=args.sermon_id,
        audio_path_override=args.audio_path,
        max_duration=args.max_duration,
        model_name=args.model,
        output_path_override=args.output,
    )
