import json
import os
import subprocess
import argparse
import shutil
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
OUTPUT_DIR = ROOT / "output/final_sermons"
CROSSFADE_DURATION = 0.1 # 100ms

def update_catalog_status(sermon_id, status, audio_path=None):
    records = []
    updated = False
    if not CATALOG_PATH.exists():
        return

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            r = json.loads(line)
            if r["sermon_id"] == sermon_id:
                r["status"] = status
                if audio_path:
                    r["tts"]["output_dir"] = str(audio_path.parent)
                    r["review"]["audio_approved"] = False
                updated = True
            records.append(r)
    
    if updated:
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

def merge_locally(chunks, output_path):
    if not chunks: return False
    print(f"\n🎬 Blending {len(chunks)} chunks locally...")
    
    temp_dir = Path("/tmp/merge_work")
    temp_dir.mkdir(exist_ok=True)
    
    current_file = chunks[0]
    try:
        for i in range(1, len(chunks)):
            next_file = chunks[i]
            output_temp = temp_dir / f"temp_merge_{i}.wav"
            
            # acrossfade=d=0.1:c1=tri:c2=tri uses 100ms triangular fade
            cmd = [
                "ffmpeg", "-y", "-i", str(current_file), "-i", str(next_file),
                "-filter_complex", f"[0:a][1:a]acrossfade=d={CROSSFADE_DURATION}:c1=tri:c2=tri[aout]",
                "-map", "[aout]", str(output_temp)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            current_file = output_temp

        shutil.copy(current_file, output_path)
        return True
    except Exception as e:
        print(f"Merge failed: {e}")
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def retrieve_results(sermon_id, kernel_id):
    print(f"Monitoring Kaggle Kernel: {kernel_id} for {sermon_id}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            result = subprocess.run(
                ["kaggle", "kernels", "status", kernel_id],
                capture_output=True, text=True, check=True
            )
            
            # We accept ERROR because our v9-style jobs might "fail" in the merge step 
            # but still have all the chunks we need.
            is_done = "KernelWorkerStatus.COMPLETED" in result.stdout or "KernelWorkerStatus.ERROR" in result.stdout
            
            if is_done:
                print(f"\n✅ Kernel run ended. Attempting to retrieve chunks for {sermon_id}...")
                
                temp_download = Path(f"/tmp/kaggle_results_{sermon_id}")
                if temp_download.exists(): shutil.rmtree(temp_download)
                temp_download.mkdir(exist_ok=True)
                
                # Download ALL chunks
                subprocess.run([
                    "kaggle", "kernels", "output", kernel_id, 
                    "-p", str(temp_download), 
                    "--file-pattern", "sermon_chunk_.*\.wav"
                ], check=True)

                chunks = sorted(list(temp_download.glob("sermon_chunk_*.wav")))
                if not chunks:
                    print("❌ No chunks found in Kaggle output. The run likely failed early.")
                    return False
                
                dest_wav = OUTPUT_DIR / f"{sermon_id}.wav"
                if merge_locally(chunks, dest_wav):
                    print(f"🚀 Final audio saved to: {dest_wav.relative_to(ROOT)}")
                    update_catalog_status(sermon_id, "audio_ready", dest_wav)
                    shutil.rmtree(temp_download)
                    return True
                else:
                    return False
            
            else:
                sys.stdout.write(".")
                sys.stdout.flush()
                time.sleep(30)

        except Exception as e:
            print(f"Error during retrieval: {e}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor and retrieve Kaggle TTS chunks and merge locally.")
    parser.add_argument("sermon_id", help="The sermon ID being processed")
    parser.add_argument("--kernel", default="nathanpurcella/fish-speech-sermon-generator-hf", help="The Kaggle kernel ID")
    
    args = parser.parse_args()
    retrieve_results(args.sermon_id, args.kernel)
