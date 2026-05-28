import json
import os
import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
AUDIO_SCRIPTS_DIR = ROOT / "pipeline/audio_scripts"

PROMPT_TEMPLATE = """You are a performance narrator for historical sermons, specifically in the style of Charles Spurgeon. 
Your task is to transform the provided sermon text into an audioscript by injecting emotional tags and pauses.

Use the following tags:
[solemn] - for serious, heavy, or theological points.
[warm] - for compassionate, encouraging, or fatherly moments.
[excited] - for jubilant, intense, or high-energy points.
[emphasis] - for specific words or phrases that need weight.
[whisper] - for intimate, low-volume, or intense secrets.
[pause] - for a 1-2 second break after a point.
[assertive] - for strong, definitive statements.

Guidelines:
- Maintain every word of the original text.
- Do not add your own commentary.
- Place tags on their own lines before the text they apply to, or inline for emphasis/pause.
- Output ONLY the final script. No preamble or postamble.

SERMON TEXT:
{text}
"""

def generate_script(sermon_id):
    # Find sermon record
    record = None
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r["sermon_id"] == sermon_id:
                record = r
                break
    
    if not record:
        print(f"Error: Sermon {sermon_id} not found in catalog.")
        return

    text_path = ROOT / record["filename"]
    if not text_path.exists():
        print(f"Error: Sermon file {text_path} not found.")
        return

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Apply phonetic normalization (e.g., 2 Kings -> Second Kings)
    from phonetic_normalizer import normalize_text
    text = normalize_text(text)

    # Prepare prompt
    prompt = PROMPT_TEMPLATE.format(text=text)

    print(f"Generating audio script for {sermon_id} via Gemini CLI...")
    
    try:
        # Run gemini -p in headless mode
        # We use --raw-output to avoid ANSI noise and --approval-mode yolo to prevent prompts
        process = subprocess.Popen(
            ["gemini", "--approval-mode", "plan", "-p", prompt],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Error calling Gemini CLI: {stderr}")
            return

        # Clean up output - gemini CLI might include some log lines at the start
        # We look for the start of the script (often starts with # or [tag])
        script_content = stdout.strip()
        
        # Strip potential log noise from the start (looking for the first [ or #)
        match = re.search(r"([#\[].*)", script_content, re.DOTALL)
        if match:
            script_content = match.group(1)

        out_dir = AUDIO_SCRIPTS_DIR / record["author_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a consistent naming convention
        base_name = Path(record["filename"]).stem
        out_path = out_dir / f"{base_name}-Audio-Script.md"
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(script_content)
            
        print(f"Successfully generated audio script: {out_path.relative_to(ROOT)}")
        
    except Exception as e:
        print(f"Failed to generate script: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 generate_audio_scripts.py <sermon_id>")
    else:
        generate_script(sys.argv[1])
