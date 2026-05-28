import json
import os
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
AUTHORS_PATH = ROOT / "pipeline/authors.json"
JOBS_DIR = ROOT / "pipeline/jobs"

def clean_for_tts(text):
    # Remove markdown headers and emphasis
    text = re.sub(r"^#+.*$", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    # Remove [Scripture: ...] if it was added by the cleaner
    text = re.sub(r"^\*\*Scripture:\*\*.*$", "", text, flags=re.MULTILINE)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def split_chunks(text, max_chars=1000):
    # Split into chunks of approx max_chars, trying to break at sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += " " + s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks

def package_job(sermon_id):
    # Find sermon record
    record = None
    if not CATALOG_PATH.exists():
        print(f"Error: {CATALOG_PATH} not found.")
        return

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

    # Find author meta
    with open(AUTHORS_PATH, "r", encoding="utf-8") as f:
        authors = json.load(f)["authors"]
    author = next((a for a in authors if a["author_id"] == record["author_id"]), None)
    
    if not author or not author.get("primary_seed_voice"):
        print(f"Error: Author {record['author_id']} has no primary seed voice.")
        return

    job_id = f"job-{sermon_id}"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Read text
    text_path = ROOT / record["filename"]
    if not text_path.exists():
        print(f"Error: Sermon file {text_path} not found.")
        return

    with open(text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    tts_text = clean_for_tts(text)
    chunks = split_chunks(tts_text)
    
    chunk_dir = job_dir / "chunks"
    chunk_dir.mkdir(exist_ok=True)
    
    for i, chunk in enumerate(chunks):
        with open(chunk_dir / f"{i:03d}.txt", "w", encoding="utf-8") as f:
            f.write(chunk)
            
    # Copy seed
    seed_src = ROOT / author["primary_seed_voice"]
    seed_dest = job_dir / "seed.wav"
    if seed_src.exists():
        shutil.copy(seed_src, seed_dest)
    else:
        print(f"Warning: Seed voice {seed_src} not found.")
        
    # Write manifest
    manifest = {
        "job_id": job_id,
        "sermon_id": sermon_id,
        "author_id": record["author_id"],
        "num_chunks": len(chunks),
        "seed_voice": "seed.wav",
        "status": "pending",
        "title": record["title"]
    }
    with open(job_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Successfully created job package in {job_dir.relative_to(ROOT)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 package_tts_job.py <sermon_id>")
    else:
        package_job(sys.argv[1])
