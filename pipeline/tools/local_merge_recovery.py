import os
import glob
import subprocess
import shutil
from pathlib import Path

# Configuration
CHUNKS_DIR = Path("/tmp/v9_recovery")
OUTPUT_PATH = Path("output/final_sermons/spurgeon-mtp-0003-the-sin-of-unbelief.wav")
CROSSFADE_DURATION = 0.1 # 100ms

def merge_chunks():
    chunks = sorted(list(CHUNKS_DIR.glob("sermon_chunk_*.wav")))
    if not chunks:
        print("No chunks found in /tmp/v9_recovery")
        return

    print(f"Blending {len(chunks)} chunks locally...")
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # We'll merge them one by one to ensure ffmpeg stability
    current_file = chunks[0]
    
    # Create a temporary directory for intermediate merges
    temp_dir = Path("/tmp/merge_work")
    temp_dir.mkdir(exist_ok=True)

    try:
        for i in range(1, len(chunks)):
            next_file = chunks[i]
            output_temp = temp_dir / f"temp_merge_{i}.wav"
            
            print(f"  Blending chunk {i-1} with {i}...")
            
            # -y overwrites existing
            # acrossfade=d=0.1:c1=tri:c2=tri uses 100ms triangular fade
            cmd = [
                "ffmpeg", "-y", "-i", str(current_file), "-i", str(next_file),
                "-filter_complex", f"[0:a][1:a]acrossfade=d={CROSSFADE_DURATION}:c1=tri:c2=tri[aout]",
                "-map", "[aout]", str(output_temp)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            current_file = output_temp

        # Final move to destination
        shutil.copy(current_file, OUTPUT_PATH)
        print(f"\n✅ SUCCESS! Sermon merged with crossfades.")
        print(f"Location: {OUTPUT_PATH}")

    finally:
        # We'll keep the recovery chunks for now but clean up intermediate merge files
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    merge_chunks()
