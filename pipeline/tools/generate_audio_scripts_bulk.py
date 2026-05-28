import json
import os
import subprocess
from pathlib import Path
from generate_audio_scripts import generate_script

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
AUDIO_SCRIPTS_DIR = ROOT / "pipeline/audio_scripts"

def main():
    if not CATALOG_PATH.exists():
        print(f"Error: {CATALOG_PATH} not found.")
        return

    records = []
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    count = 0
    for record in records:
        author_id = record["author_id"]
        base_name = Path(record["filename"]).stem
        script_path = AUDIO_SCRIPTS_DIR / author_id / f"{base_name}-Audio-Script.md"

        # Only generate if it doesn't exist yet
        if not script_path.exists():
            print(f"Processing missing script for: {record['sermon_id']}")
            generate_script(record["sermon_id"])
            count += 1
            # Rate limiting / polite to LLM
            if count >= 10: 
                print("Limit of 10 scripts per bulk run reached to avoid overwhelming the LLM.")
                break

    if count == 0:
        print("No missing audio scripts found.")

if __name__ == "__main__":
    main()
