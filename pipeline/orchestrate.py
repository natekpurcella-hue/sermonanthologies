import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def run_tool(tool_name, args=None):
    tool_path = ROOT / "tools" / tool_name
    cmd = [sys.executable, str(tool_path)]
    if args:
        cmd.extend(args)
    
    print(f"\n>>> Running {tool_name}...")
    try:
        result = subprocess.run(cmd, check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {tool_name} failed with exit code {e.returncode}")
        return False

def main():
    print("=== Sermon Content Pipeline Orchestrator ===")
    
    # 1. Retrieval
    if not run_tool("retrieve_sources.py"):
        sys.exit(1)
        
    # 2. Normalization
    if not run_tool("normalize_sources.py"):
        sys.exit(1)
        
    # 3. Cleaning
    if not run_tool("clean_sermons.py"):
        sys.exit(1)
        
    # 4. Scan & Sync (Ensure catalog is current before script generation)
    print("\n>>> Refreshing catalog for script generation...")
    if not run_tool("scan_existing_sermons.py"):
        sys.exit(1)
    
    # 5. Audio Script Generation (LLM)
    print("\n>>> Generating missing performance audio scripts...")
    if not run_tool("generate_audio_scripts_bulk.py"):
        print("Warning: Audio script generation tool failed.")

    # 6. Final Sync
    print("\n>>> Final sync of author indexes...")
    if not run_tool("sync_author_indexes.py", ["--write"]):
        sys.exit(1)
        
    print("\n=== Pipeline execution complete ===")
    print("Pending Action: Review extracted sermons in 'source_cache/cleaned/'")
    print("Run 'python3 pipeline/tools/review_cleaned.py' for a report.")
    print("Run 'python3 pipeline/tools/accept_sermons.py' to approve and move them to author directories.")

if __name__ == "__main__":
    main()
