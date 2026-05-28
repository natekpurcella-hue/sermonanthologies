import json
import os
import re
from pathlib import Path

SOURCE_RECORDS_PATH = Path("catalog/source_records.jsonl")
NORMALIZED_CACHE_DIR = Path("source_cache/normalized")
CLEANED_CACHE_DIR = Path("source_cache/cleaned")

def clean_spurgeon_ccel(text):
    # Split by the separator (long underscores)
    # The CCEL text uses these to separate sermons and metadata sections.
    parts = re.split(r"_{20,}", text)
    
    sermons = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Look for (No. XXX) to identify a sermon section
        match = re.search(r"\(No\.\s+(\d+)\)", part)
        if not match:
            continue
            
        sermon_no = match.group(1).zfill(4)
        
        # Extract title: just the first non-empty line before "A Sermon"
        header_lines = []
        lines = part.splitlines()
        body_start_idx = 0
        for i, line in enumerate(lines):
            clean_line = line.strip()
            if clean_line == "A Sermon":
                body_start_idx = i + 1
                break
            if clean_line:
                header_lines.append(clean_line)
        
        # Use only the first non-empty line as the primary title
        title = header_lines[0] if header_lines else "Unknown Title"
        
        # Extract body: everything after "REV. C.H. SPURGEON"
        # We search from body_start_idx
        body_text = "\n".join(lines[body_start_idx:])
        body_parts = re.split(r"REV\..*?\n", body_text, maxsplit=1, flags=re.IGNORECASE)
        body = body_parts[1].strip() if len(body_parts) > 1 else body_text.strip()
        
        # Extract scripture reference if possible
        # Look for something like "--Philippians 2:1." or " -- Philippians 2:1"
        scripture = None
        script_match = re.search(r"--\s*([1-4]?\s*[A-Z][a-z]+(?:\s+\d+)?:?\s*\d+:\d+(?:-\d+)?)", body)
        if script_match:
            scripture = script_match.group(1)

        # Sanitize filename and truncate
        safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
        filename = f"MTP-{sermon_no}-{safe_title[:64]}.md"
        
        sermons.append({
            "sermon_id": f"spurgeon-mtp-{sermon_no}",
            "author_id": "spurgeon",
            "title": title,
            "scripture": scripture,
            "content": body,
            "filename": filename
        })
    return sermons

def main():
    if not SOURCE_RECORDS_PATH.exists():
        print(f"Error: {SOURCE_RECORDS_PATH} not found.")
        return
        
    CLEANED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    records = []
    with open(SOURCE_RECORDS_PATH, "r") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
                
    any_updated = False
    for record in records:
        if record.get("status") == "normalized":
            source_id = record["source_id"]
            author_id = record["author_id"]
            
            norm_file = NORMALIZED_CACHE_DIR / f"{source_id}.txt"
            if not norm_file.exists():
                print(f"Error: Normalized file {norm_file} not found.")
                continue
                
            print(f"Cleaning source {source_id}...")
            with open(norm_file, "r", encoding="utf-8") as f:
                text = f.read()
                
            if author_id == "spurgeon":
                sermons = clean_spurgeon_ccel(text)
            else:
                print(f"No cleaner for author {author_id}")
                continue
                
            print(f"Extracted {len(sermons)} sermons.")
            for s in sermons:
                out_path = CLEANED_CACHE_DIR / author_id / s["filename"]
                out_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(out_path, "w", encoding="utf-8") as out_f:
                    out_f.write(f"# {s['title']}\n\n")
                    if s["scripture"]:
                        out_f.write(f"**Scripture:** {s['scripture']}\n\n")
                    out_f.write(s["content"])
                
            record["status"] = "processed"
            any_updated = True
            print(f"Successfully cleaned {source_id}.")

    if any_updated:
        with open(SOURCE_RECORDS_PATH, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        print(f"Updated {SOURCE_RECORDS_PATH}.")
    else:
        print("No normalized sources to clean.")

if __name__ == "__main__":
    main()
