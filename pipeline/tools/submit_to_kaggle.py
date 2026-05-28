import json
import os
import subprocess
import argparse
import re
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "fish_speech_sermon.ipynb"
METADATA_PATH = ROOT / "kernel-metadata.json"
AUDIO_SCRIPTS_DIR = ROOT / "pipeline/audio_scripts"

def split_script(text, max_chars=3000):
    # Split into chunks of approx max_chars, trying to break at [tags] or double newlines
    parts = re.split(r"(\[.*?\]|\n\n+)", text)
    
    chunks = []
    current_chunk = ""
    
    for part in parts:
        if len(current_chunk) + len(part) < max_chars:
            current_chunk += part
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = part
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks

def main():
    parser = argparse.ArgumentParser(description="Submit a sermon to Kaggle for narration with chunking.")
    parser.add_argument("sermon_id", help="The sermon ID to submit")
    parser.add_argument("--webhook", help="Optional webhook URL for progress notifications")
    args = parser.parse_args()

    # 1. Find the audio script
    with open(ROOT / "catalog/sermons.jsonl", "r") as f:
        author_id = None
        sermon_filename = None
        for line in f:
            r = json.loads(line)
            if r["sermon_id"] == args.sermon_id:
                author_id = r["author_id"]
                sermon_filename = Path(r["filename"]).stem
                break
    
    if not author_id:
        print(f"Error: Sermon {args.sermon_id} not found.")
        return

    script_path = AUDIO_SCRIPTS_DIR / author_id / f"{sermon_filename}-Audio-Script.md"
    if not script_path.exists():
        print(f"Error: Audio script not found at {script_path}")
        print("Run 'python3 pipeline/tools/generate_audio_scripts.py <sermon_id>' first.")
        return

    with open(script_path, "r") as f:
        full_script = f.read()

    # Apply chunking
    script_chunks = split_script(full_script)
    print(f"Split script into {len(script_chunks)} chunks for GPU safety.")

    # 2. Inject chunks into notebook
    with open(NOTEBOOK_PATH, "r") as f:
        nb = json.load(f)

    script_injected = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code" and "sermon_script =" in "".join(cell["source"]):
            new_lines = []
            new_lines.append("sermon_chunks = [\n")
            for chunk in script_chunks:
                escaped_chunk = chunk.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                new_lines.append(f'    "{escaped_chunk}",\n')
            new_lines.append("]\n")
            
            found_original = False
            for line in cell["source"]:
                if 'sermon_script = """' in line:
                    found_original = True
                    continue
                if found_original:
                    if '"""' in line:
                        found_original = False
                    continue
                if "subprocess.run" in line or "Stage 1:" in line or "Stage 2:" in line or "codes_candidates" in line:
                    continue
                if "CHECKPOINT_DIR =" in line or "VOCODER_CKPT =" in line or "PROMPT_TOKENS_PATH =" in line:
                    new_lines.append(line)

            # Add the corrected Loop Logic with Webhook Support
            new_lines.extend([
                "\n",
                "import os\n",
                "import shutil\n",
                "import subprocess\n",
                "import glob\n",
                "import requests\n",
                "from pathlib import Path\n",
                "\n",
                f"WEBHOOK_URL = \"{args.webhook if args.webhook else ''}\"\n",
                "def notify(msg, chunk=0, total=0, status='processing'):\n",
                "    if not WEBHOOK_URL: return\n",
                "    try:\n",
                "        requests.post(WEBHOOK_URL, json={\n",
                f"            \"job_id\": \"{args.sermon_id}\",\n",
                "            \"status\": status,\n",
                "            \"message\": msg,\n",
                "            \"current_chunk\": chunk,\n",
                "            \"total_chunks\": total\n",
                "        }, timeout=5)\n",
                "    except: pass\n",
                "\n",
                "# ── Stage 0: Reference Audio → Prompt Tokens (Run once) ──────────────────\n",
                "print(\"Stage 0: Reference audio → prompt tokens...\")\n",
                "notify(\"Starting Stage 0\")\n",
                "subprocess.run([\n",
                "    \"python\", \"-m\", \"fish_speech.models.vqgan.inference\",\n",
                "    \"-i\", REFERENCE_AUDIO,\n",
                "    \"-o\", \"prompt_tokens.wav\",\n",
                "    \"--checkpoint-path\", VOCODER_CKPT,\n",
                "], check=True)\n",
                "\n",
                "chunk_outputs = []\n",
                "for i, chunk_text in enumerate(sermon_chunks):\n",
                "    print(f\"\\nProcessing Chunk {i+1}/{len(sermon_chunks)}...\")\n",
                "    \n",
                "    # Stage 1: Text -> Semantic\n",
                "    subprocess.run([\n",
                "        \"python\", \"-m\", \"fish_speech.models.text2semantic.inference\",\n",
                "        \"--text\", chunk_text,\n",
                "        \"--prompt-text\", prompt_text,\n",
                "        \"--prompt-tokens\", PROMPT_TOKENS_PATH,\n",
                "        \"--checkpoint-path\", CHECKPOINT_DIR,\n",
                "        \"--num-samples\", \"1\",\n",
                "        \"--half\",\n",
                "    ], check=True)\n",
                "    \n",
                "    # Discover the code file\n",
                "    codes_candidates = glob.glob(\"**/codes_0.npy\", recursive=True) + glob.glob(\"codes_0.npy\")\n",
                "    if not codes_candidates: raise FileNotFoundError(\"codes_0.npy not found\")\n",
                "    \n",
                "    # Stage 2: Semantic -> Audio\n",
                "    chunk_wav = f\"chunk_{i:03d}.wav\"\n",
                "    subprocess.run([\n",
                "        \"python\", \"-m\", \"fish_speech.models.vqgan.inference\",\n",
                "        \"-i\", codes_candidates[0],\n",
                "        \"-o\", chunk_wav,\n",
                "        \"--checkpoint-path\", VOCODER_CKPT,\n",
                "    ], check=True)\n",
                "    \n",
                "    # Move output to prevent overwrite and track it\n",
                "    final_chunk_wav = f\"/kaggle/working/sermon_chunk_{i:03d}.wav\"\n",
                "    actual_output = \"fake.wav\" if os.path.exists(\"fake.wav\") else chunk_wav\n",
                "    shutil.move(actual_output, final_chunk_wav)\n",
                "    \n",
                "    # CLEANUP Stage 1 files for next loop iteration\n",
                "    if os.path.exists(codes_candidates[0]):\n",
                "        os.remove(codes_candidates[0])\n",
                "    \n",
                "    chunk_outputs.append(final_chunk_wav)\n",
                "    notify(f\"Chunk {i+1} complete\", chunk=i+1, total=len(sermon_chunks))\n",
                "    print(f\"✅ Chunk {i+1} saved to {final_chunk_wav}\")\n"
            ])
            
            cell["source"] = new_lines
            script_injected = True
            break
            
    if not script_injected:
        print("Error: Could not find script injection point in notebook.")
        return

    for cell in nb["cells"]:
        if cell["cell_type"] == "code" and "Smart Merge" in "".join(cell["source"]):
            cell["source"] = [
                "# ── Cell 6: Bulletproof Crossfade Merge ──────────────────────────────────\n",
                "import os\n",
                "import glob\n",
                "import subprocess\n",
                "import shutil\n",
                "from pathlib import Path\n",
                "\n",
                "CHUNKS = sorted(glob.glob(\"/kaggle/working/sermon_chunk_*.wav\"))\n",
                "if not CHUNKS:\n",
                "    print(\"❌ No chunks found to merge!\")\n",
                "    notify(\"Error: No chunks found\", status='failed')\n",
                "elif len(CHUNKS) == 1:\n",
                "    shutil.copy(CHUNKS[0], \"/kaggle/working/sermon_output_full.wav\")\n",
                "    print(\"✅ Single chunk saved.\")\n",
                "    notify(\"Sermon complete (single chunk)\", status='complete')\n",
                "else:\n",
                "    print(f\"Blending {len(CHUNKS)} chunks...\")\n",
                "    notify(f\"Blending {len(CHUNKS)} chunks\")\n",
                "    current_file = CHUNKS[0]\n",
                "    for i in range(1, len(CHUNKS)):\n",
                "        next_file = CHUNKS[i]\n",
                "        output_temp = f\"temp_merge_{i}.wav\"\n",
                "        print(f\"  Blending {current_file} with {next_file}...\")\n",
                "        cmd = [\n",
                "            \"ffmpeg\", \"-y\", \"-i\", current_file, \"-i\", next_file, \n",
                "            \"-filter_complex\", \"[0:a][1:a]acrossfade=d=0.1:c1=tri:c2=tri[aout]\", \n",
                "            \"-map\", \"[aout]\", output_temp\n",
                "        ]\n",
                "        subprocess.run(cmd, check=True, capture_output=True)\n",
                "        current_file = output_temp\n",
                "    \n",
                "    shutil.move(current_file, \"/kaggle/working/sermon_output_full.wav\")\n",
                "    print(\"✅ Final sermon merged: /kaggle/working/sermon_output_full.wav\")\n",
                "    notify(\"Sermon complete and merged\", status='complete')\n"
            ]

    staging_dir = Path("/tmp/kaggle_submit")
    staging_dir.mkdir(exist_ok=True)
    with open(staging_dir / "fish_speech_sermon.ipynb", "w") as f:
        json.dump(nb, f, indent=1)

    with open(METADATA_PATH, "r") as f:
        meta = json.load(f)
    meta["id"] = "nathanpurcella/fish-speech-sermon-generator-hf"
    meta["code_file"] = "fish_speech_sermon.ipynb"
    
    with open(staging_dir / "kernel-metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Pushing chunked job for {args.sermon_id}...")
    subprocess.run(["kaggle", "kernels", "push", "-p", str(staging_dir)], check=True)
    print("✅ Job submitted! v9 with optional Webhook support.")

if __name__ == "__main__":
    main()
