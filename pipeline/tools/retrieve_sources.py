import json
import os
import hashlib
import requests
from datetime import datetime
from pathlib import Path

SOURCE_RECORDS_PATH = Path("catalog/source_records.jsonl")
RAW_CACHE_DIR = Path("source_cache/raw")

def get_checksum(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    if not SOURCE_RECORDS_PATH.exists():
        print(f"Error: {SOURCE_RECORDS_PATH} not found.")
        return

    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    with open(SOURCE_RECORDS_PATH, "r") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    any_updated = False
    for record in records:
        if record.get("status") == "candidate":
            source_id = record["source_id"]
            url = record["source_url"]
            fmt = record["format"]

            print(f"Retrieving {source_id} from {url}...")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                filename = f"{source_id}.{fmt}"
                file_path = RAW_CACHE_DIR / filename

                with open(file_path, "wb") as out_f:
                    out_f.write(response.content)

                record["status"] = "retrieved"
                record["retrieval_date"] = datetime.now().isoformat()
                record["checksum"] = get_checksum(file_path)
                any_updated = True
                print(f"Successfully retrieved {source_id}.")
            except Exception as e:
                record["status"] = "failed"
                record["error_log"] = str(e)
                any_updated = True
                print(f"Failed to retrieve {source_id}: {e}")

    if any_updated:
        with open(SOURCE_RECORDS_PATH, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        print(f"Updated {SOURCE_RECORDS_PATH}.")
    else:
        print("No candidates to retrieve.")

if __name__ == "__main__":
    main()
