#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Environment Paths
XTTS_ENV_PYTHON = ROOT / "xtts_env/bin/python3"
VIDEO_ENV_PYTHON = ROOT / "video_env/bin/python3"
QUALITY_ENV_PYTHON = ROOT / "qwen_tts_project/venv/bin/python3"

# Tool Paths
RETRIEVE_RESULTS_TOOL = ROOT / "pipeline/tools/retrieve_results.py" 
GENERATE_SCRIPT_TOOL = ROOT / "pipeline/tools/generate_audio_scripts.py"
GENERATE_AUDIO_TOOL = ROOT / "pipeline/tools/generate_audio_xtts.py"
VERIFY_QUALITY_TOOL = ROOT / "qwen_tts_project/verify_quality.py"
ALIGN_CAPTIONS_TOOL = ROOT / "pipeline/tools/align_captions.py"
GENERATE_VIDEO_TOOL = ROOT / "pipeline/tools/generate_long_video.py"

def run_command(python_bin, script_path, args=None):
    cmd = [str(python_bin), str(script_path)]
    if args:
        cmd.extend(args)
    
    print(f"\n>>> Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nFATAL: Stage failed with exit code {e.returncode}")
        return False

def get_sermon_id_from_antigravity():
    """
    Triggers autonomous retrieval via agy CLI.
    """
    print("\n>>> Triggering autonomous retrieval via agy...")
    prompt = (
        "Retrieve a public domain sermon by Charles Spurgeon about grace, "
        "process it (clean/normalize), add it to the catalog/sermons.jsonl, "
        "and output ONLY the resulting sermon_id. Do not provide any other text."
    )
    
    try:
        # We use --prompt to run non-interactively and --dangerously-skip-permissions 
        # to allow the agent to perform file edits autonomously.
        result = subprocess.run(
            ["agy", "--prompt", prompt, "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            check=True
        )
        sermon_id = result.stdout.strip()
        
        # Simple validation: sermon_id should not contain spaces and should be relatively short
        if sermon_id and " " not in sermon_id and len(sermon_id) < 100:
            print(f"Successfully retrieved sermon ID: {sermon_id}")
            return sermon_id
        else:
            print(f"Error: Received unexpected output from agy: {sermon_id}")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Error: agy call failed with exit code {e.returncode}")
        print(f"Stderr: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser(description="End-to-End Sermon Pipeline Orchestrator")
    parser.add_argument("--sermon-id", help="Existing sermon ID to process")
    parser.add_argument("--max-duration", type=int, default=30, help="Max duration for test (default: 30)")
    
    args = parser.parse_args()
    
    sermon_id = args.sermon_id
    
    if not sermon_id:
        sermon_id = get_sermon_id_from_antigravity()
        if not sermon_id:
            print("Failed to retrieve sermon ID autonomously. Exiting.")
            sys.exit(1)

    print(f"\n=== Orchestrating E2E Pipeline for: {sermon_id} ===")

    # 1. Audio Script Generation (LLM)
    # We use the current environment's python as it doesn't need heavy dependencies
    if not run_command(sys.executable, GENERATE_SCRIPT_TOOL, [sermon_id]):
        print("Warning: Audio script generation failed. Proceeding with raw text.")

    # 2. Audio Generation (XTTS)
    audio_args = [sermon_id]
    if args.max_duration:
        # Estimate ~15 characters per second of speech
        audio_args.extend(["--max-chars", str(args.max_duration * 15)])
        
    if not run_command(XTTS_ENV_PYTHON, GENERATE_AUDIO_TOOL, audio_args):
        sys.exit(1)

    # 3. Quality Verification (Whisper)
    quality_args = [sermon_id]
    if args.max_duration:
        quality_args.extend(["--max-chars", str(args.max_duration * 15)])
        
    if not run_command(QUALITY_ENV_PYTHON, VERIFY_QUALITY_TOOL, quality_args):
        sys.exit(1)

    # 4. Caption Alignment (Whisper)
    if not run_command(VIDEO_ENV_PYTHON, ALIGN_CAPTIONS_TOOL, [sermon_id, "--max-duration", str(args.max_duration)]):
        sys.exit(1)

    # 5. Video Rendering (Puppeteer + FFmpeg)
    if not run_command(VIDEO_ENV_PYTHON, GENERATE_VIDEO_TOOL, [sermon_id, "--max-duration", str(args.max_duration)]):
        sys.exit(1)

    print(f"\n=== E2E Pipeline for {sermon_id} completed successfully ===")

if __name__ == "__main__":
    main()
