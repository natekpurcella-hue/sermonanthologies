import json
import os
from pathlib import Path
from bs4 import BeautifulSoup

SOURCE_RECORDS_PATH = Path("catalog/source_records.jsonl")
RAW_CACHE_DIR = Path("source_cache/raw")
NORMALIZED_CACHE_DIR = Path("source_cache/normalized")

def normalize_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    # Basic normalization: strip scripts and styles, then get text
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    
    # We might want to preserve some newlines
    text = soup.get_text(separator="\n")
    
    # Clean up excessive newlines
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

def main():
    if not SOURCE_RECORDS_PATH.exists():
        print(f"Error: {SOURCE_RECORDS_PATH} not found.")
        return

    NORMALIZED_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    with open(SOURCE_RECORDS_PATH, "r") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    any_updated = False
    for record in records:
        if record.get("status") == "retrieved":
            source_id = record["source_id"]
            fmt = record["format"]

            raw_file = RAW_CACHE_DIR / f"{source_id}.{fmt}"
            if not raw_file.exists():
                print(f"Error: Raw file {raw_file} not found for {source_id}.")
                continue

            print(f"Normalizing {source_id}...")
            try:
                with open(raw_file, "rb") as f:
                    content = f.read()

                if fmt == "html":
                    text = normalize_html(content)
                elif fmt == "txt":
                    text = content.decode("utf-8", errors="ignore")
                else:
                    print(f"Normalization for {fmt} not implemented yet.")
                    continue

                norm_file = NORMALIZED_CACHE_DIR / f"{source_id}.txt"
                with open(norm_file, "w", encoding="utf-8") as out_f:
                    out_f.write(text)

                record["status"] = "normalized"
                any_updated = True
                print(f"Successfully normalized {source_id}.")
            except Exception as e:
                print(f"Failed to normalize {source_id}: {e}")

    if any_updated:
        with open(SOURCE_RECORDS_PATH, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        print(f"Updated {SOURCE_RECORDS_PATH}.")
    else:
        print("No retrieved sources to normalize.")

if __name__ == "__main__":
    main()
