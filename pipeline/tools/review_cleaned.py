import json
import os
import re
from pathlib import Path

CLEANED_DIR = Path("source_cache/cleaned")
THEME_VOCAB_PATH = Path("pipeline/theme_vocabulary.json")

def suggest_themes(text, vocab):
    suggested = []
    text_lower = text.lower()
    # Simple keyword matching
    for theme in vocab:
        # Check for whole word match
        if re.search(rf"\b{re.escape(theme.lower())}\b", text_lower):
            suggested.append(theme)
    return suggested

def main():
    if not THEME_VOCAB_PATH.exists():
        vocab = []
    else:
        with open(THEME_VOCAB_PATH, "r") as f:
            vocab = json.load(f).get("themes", [])

    if not CLEANED_DIR.exists():
        print("No cleaned sermons found in source_cache/cleaned.")
        return

    print(f"{'Sermon ID':<25} {'Words':<8} {'Themes'}")
    print("-" * 60)

    for author_dir in CLEANED_DIR.iterdir():
        if not author_dir.is_dir():
            continue
            
        for sermon_file in author_dir.glob("*.md"):
            # Extract ID from filename if possible, or just use filename
            # Filename format: MTP-XXXX-Title.md
            match = re.match(r"(MTP-\d+)", sermon_file.name)
            sermon_id = f"{author_dir.name}-{match.group(1).lower()}" if match else sermon_file.stem
            
            with open(sermon_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            word_count = len(content.split())
            suggested = suggest_themes(content, vocab)
            
            # Limit display to 3 suggested themes
            theme_str = ", ".join(suggested[:3])
            if len(suggested) > 3:
                theme_str += f" (+{len(suggested)-3} more)"
                
            print(f"{sermon_id:<25} {word_count:<8} {theme_str}")

if __name__ == "__main__":
    main()
