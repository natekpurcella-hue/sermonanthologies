#!/usr/bin/env python3
import time
import subprocess
import sys
import argparse
import json

def get_status(kernel_id):
    try:
        result = subprocess.run(
            ["kaggle", "kernels", "status", kernel_id],
            capture_output=True,
            text=True,
            check=True
        )
        # Output is usually "user/slug has status 'Status'"
        if "KernelWorkerStatus.COMPLETED" in result.stdout or "complete" in result.stdout.lower():
            return "complete"
        if "error" in result.stdout.lower() or "failed" in result.stdout.lower():
            return "error"
        return "running"
    except subprocess.CalledProcessError as e:
        print(f"Error checking status: {e.stderr}")
        return "unknown"

def download_output(kernel_id, destination):
    print(f"Downloading output to {destination}...")
    try:
        subprocess.run(
            ["kaggle", "kernels", "output", kernel_id, "-p", destination, "--file-pattern", ".*\\.wav"],
            check=True
        )
        print("Download successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading output: {e.stderr}")

def main():
    parser = argparse.ArgumentParser(description="Monitor a Kaggle kernel and download output on completion.")
    parser.add_argument("kernel_id", help="The Kaggle kernel ID (username/slug)")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds (default: 60)")
    parser.add_argument("--output-dir", default="./output", help="Directory to download output to (default: ./output)")
    parser.add_argument("--webhook", help="Optional webhook URL to notify on completion")

    args = parser.parse_args()

    print(f"Monitoring Kaggle Kernel: {args.kernel_id}")
    print(f"Polling every {args.interval} seconds...")

    while True:
        status = get_status(args.kernel_id)
        
        if status == "complete":
            print("\n✅ Kernel execution complete!")
            download_output(args.kernel_id, args.output_dir)
            
            if args.webhook:
                print(f"Sending webhook notification to {args.webhook}...")
                try:
                    import requests
                    requests.post(args.webhook, json={"status": "complete", "kernel": args.kernel_id})
                except ImportError:
                    print("Error: 'requests' library not found. Skipping webhook.")
                except Exception as e:
                    print(f"Webhook failed: {e}")
            break
        
        elif status == "error":
            print("\n❌ Kernel execution failed.")
            if args.webhook:
                try:
                    import requests
                    requests.post(args.webhook, json={"status": "failed", "kernel": args.kernel_id})
                except:
                    pass
            sys.exit(1)
        
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
