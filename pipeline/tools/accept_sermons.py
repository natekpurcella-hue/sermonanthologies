import json
import os
import re
import shutil
from pathlib import Path

CLEANED_DIR = Path("source_cache/cleaned")
ROOT = Path(__file__).resolve().parents[2]
THEME_VOCAB_PATH = ROOT / "pipeline/theme_vocabulary.json"

def suggest_themes(text, vocab):
    suggested = []
    text_lower = text.lower()
    for theme in vocab:
        if re.search(rf"\b{re.escape(theme.lower())}\b", text_lower):
            suggested.append(theme)
    return suggested

def first_heading(text):
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return None

def main():
    if not CLEANED_DIR.exists():
        print("No cleaned sermons found.")
        return

    if not THEME_VOCAB_PATH.exists():
        vocab = []
    else:
        with open(THEME_VOCAB_PATH, "r") as f:
            vocab = json.load(f).get("themes", [])

    for author_dir in CLEANED_DIR.iterdir():
        if not author_dir.is_dir():
            continue
            
        author_id = author_dir.name
        with open(ROOT / "pipeline/authors.json", "r") as f:
            authors = json.load(f)["authors"]
            
        author_meta = next((a for a in authors if a["author_id"] == author_id), None)
        if not author_meta:
            print(f"Author {author_id} not found in authors.json")
            continue
            
        dest_dir = ROOT / author_meta["directory"]
        dest_dir.mkdir(parents=True, exist_ok=True)
        index_path = dest_dir / "INDEX.md"
        
        # Load existing index filenames to avoid duplicates
        existing_filenames = set()
        if index_path.exists():
            with open(index_path, "r") as f:
                for line in f:
                    match = re.match(r"\|\s*(.*?\.md)\s*\|", line)
                    if match:
                        existing_filenames.add(match.group(1).strip())

        for sermon_file in author_dir.glob("*.md"):
            if sermon_file.name in existing_filenames:
                print(f"Skipping {sermon_file.name} - already in INDEX.md")
                continue
                
            dest_path = dest_dir / sermon_file.name
            if dest_path.exists():
                print(f"Skipping {sermon_file.name} - already exists on disk")
                continue
            
            print(f"Accepting {sermon_file.name}...")
            with open(sermon_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            title = first_heading(content) or sermon_file.stem
            themes = suggest_themes(content, vocab)
            theme_str = ", ".join(themes[:3])
            
            # Move file
            shutil.move(sermon_file, dest_path)
            
            # Append to INDEX.md
            if not index_path.exists():
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(f"# Index of {author_meta['display_name']}\n\n")
                    f.write("| Filename | Title | Themes | Used in Anthology |\n")
                    f.write("|----------|-------|--------|-------------------|\n")
            
            with open(index_path, "a", encoding="utf-8") as f:
                f.write(f"| {sermon_file.name} | {title} | {theme_str} | No |\n")

if __name__ == "__main__":
    main()
