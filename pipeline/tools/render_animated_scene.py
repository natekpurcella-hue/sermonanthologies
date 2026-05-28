#!/usr/bin/env python3
"""
render_animated_scene.py — Render an animated sermon video.

Pipeline:
  1. Load captions.json (from align_captions.py)
  2. Compute RMS intensity from audio (librosa) → detect arm-raise events
  3. Load sentence boundaries from captions.json → detect lean events
  4. Build timeline.json
  5. Inject SVG + timeline + captions into GSAP HTML template
  6. Launch Puppeteer to capture frames at 24fps
  7. FFmpeg: frames + audio → MP4 (16:9 and optional 9:16 crop)

Usage:
    python render_animated_scene.py <sermon_id> [options]
    python render_animated_scene.py spurgeon-mtp-0003 \\
        --max-duration 90 --scene spurgeon --fps 24

Requirements (video_env):
    librosa, soundfile, numpy
Node requirements (global npm):
    puppeteer
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENES_DIR   = ROOT / "assets/scenes"
CAPTIONS_DIR = ROOT / "output/captions"
OUTPUT_DIR   = ROOT / "output/video/long"
TEMPLATE_PATH = Path(__file__).parent / "scene_renderer/template.html"

# Where we pre-fetch GSAP (avoids network calls during Puppeteer capture)
GSAP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"

FPS = 24
INTENSITY_THRESHOLD = 0.72  # RMS percentile above which arm_raise fires
MIN_ARM_RAISE_GAP   = 2.5   # seconds between arm raises
MIN_LEAN_GAP        = 1.2   # seconds between leans


# ─────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────

def load_captions(sermon_id: str, captions_path_override: str | None) -> dict:
    if captions_path_override:
        p = Path(captions_path_override)
    else:
        p = CAPTIONS_DIR / sermon_id / "captions.json"
    if not p.exists():
        raise FileNotFoundError(
            f"Captions not found at {p}.\n"
            f"Run first: python align_captions.py {sermon_id}"
        )
    with open(p) as f:
        return json.load(f)


def load_scene_content(scene_name: str) -> str:
    scene_dir = SCENES_DIR / scene_name
    # Check for PNG layers first
    layers = sorted(scene_dir.glob("layer_*.png"))
    if layers:
        print(f"Found {len(layers)} PNG layers.")
        html = ""
        for i, layer in enumerate(layers):
            if "layer_00" in layer.name:
                id_attr = 'id="background"'
            elif "layer_01" in layer.name:
                id_attr = 'id="spurgeon-body"'
            elif "layer_02" in layer.name:
                id_attr = 'id="foreground"'
            elif "layer_03" in layer.name:
                id_attr = 'id="congregation-group"'
            else:
                id_attr = ''
            html += f'<img src="file://{layer.absolute()}" {id_attr} style="position: absolute; top: 0; left: 0; width: 1920px; height: 1080px; z-index: {i};" />\n'
        return html

    # Fallback to SVG
    svg_path = scene_dir / "scene.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"Scene content not found in {scene_dir}")
    with open(svg_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Add id to root SVG for JS targeting
    return content.replace("<svg ", '<svg id="sermon-scene-svg" ', 1)


def resolve_audio(sermon_id: str, override: str | None) -> Path:
    if override:
        p = Path(override)
        return p if p.is_absolute() else ROOT / p
    candidates = [
        ROOT / "output/final_sermons" / f"{sermon_id}.wav",
        ROOT / f"{sermon_id}.wav",
        ROOT / "spurgeon_unbelief_full.wav",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"No audio found for {sermon_id}. Pass --audio-path."
    )


# ─────────────────────────────────────────────────────────────
# 2. INTENSITY ANALYSIS
# ─────────────────────────────────────────────────────────────

def compute_intensity_events(
    audio_path: Path,
    max_duration: float | None,
    sentence_boundaries: list[float],
) -> list[dict]:
    """
    Returns a merged list of timeline events:
      { "t": float, "event": "lean"|"arm_raise", "intensity": float }
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        print("WARNING: librosa not available — using sentence-only timeline.")
        events = [
            {"t": round(t, 3), "event": "lean", "intensity": 0.5}
            for t in sentence_boundaries
        ]
        return sorted(events, key=lambda e: e["t"])

    print("Analyzing audio intensity...")
    y, sr = librosa.load(str(audio_path), sr=None, mono=True,
                         duration=max_duration)

    # Compute RMS in ~50ms frames
    frame_length = int(sr * 0.05)
    hop_length   = int(sr / FPS)  # one frame per video frame
    rms = librosa.feature.rms(y=y, frame_length=frame_length,
                               hop_length=hop_length)[0]
    times = librosa.frames_to_time(range(len(rms)), sr=sr,
                                   hop_length=hop_length)

    # Normalize RMS to 0–1
    rms_max = rms.max() if rms.max() > 0 else 1.0
    rms_norm = rms / rms_max

    # Find intensity peaks (above threshold, with minimum gap)
    threshold = float(np.percentile(rms_norm, INTENSITY_THRESHOLD * 100))
    arm_events = []
    last_arm_t = -MIN_ARM_RAISE_GAP

    for i, (t, val) in enumerate(zip(times, rms_norm)):
        if val >= threshold and (t - last_arm_t) >= MIN_ARM_RAISE_GAP:
            # Check it's a local peak
            lo = max(0, i - 3)
            hi = min(len(rms_norm), i + 4)
            if val == rms_norm[lo:hi].max():
                arm_events.append({
                    "t": round(float(t), 3),
                    "event": "arm_raise",
                    "intensity": round(float(val), 3),
                })
                last_arm_t = t

    # Build lean events from sentence boundaries
    lean_events = []
    last_lean_t = -MIN_LEAN_GAP
    for boundary_t in sentence_boundaries:
        if max_duration and boundary_t > max_duration:
            break
        if (boundary_t - last_lean_t) >= MIN_LEAN_GAP:
            lean_events.append({
                "t": round(boundary_t, 3),
                "event": "lean",
                "intensity": 0.5,
            })
            last_lean_t = boundary_t

    all_events = sorted(arm_events + lean_events, key=lambda e: e["t"])
    print(f"Timeline: {len(arm_events)} arm raises, {len(lean_events)} leans.")
    return all_events


# ─────────────────────────────────────────────────────────────
# 3. GSAP HTML ASSEMBLY
# ─────────────────────────────────────────────────────────────

def fetch_gsap_local(tmp_dir: Path) -> Path:
    """Download GSAP to a temp file so Puppeteer doesn't need network."""
    gsap_path = tmp_dir / "gsap.min.js"
    if not gsap_path.exists():
        print("Fetching GSAP...")
        result = subprocess.run(
            ["curl", "-fsSL", "-o", str(gsap_path), GSAP_CDN],
            capture_output=True,
        )
        if result.returncode != 0:
            print("WARNING: Could not fetch GSAP. Will use CDN URL (requires network).")
            return None
    return gsap_path


def build_html(
    scene_content: str,
    captions: list[dict],
    timeline_events: list[dict],
    total_duration: float,
    gsap_path: Path | None,
    tmp_dir: Path,
) -> Path:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Inject Scene Content (replace placeholder comment)
    template = template.replace("%%SVG_CONTENT%%", scene_content)

    # GSAP path — use local file URI if available, else CDN
    if gsap_path and gsap_path.exists():
        gsap_ref = f"file://{gsap_path}"
    else:
        gsap_ref = GSAP_CDN
    template = template.replace("%%GSAP_PATH%%", gsap_ref)

    # Data injection
    template = template.replace("%%CAPTIONS_JSON%%",
                                 json.dumps(captions, ensure_ascii=False))
    template = template.replace("%%TIMELINE_JSON%%",
                                 json.dumps(timeline_events, ensure_ascii=False))
    template = template.replace("%%TOTAL_DURATION%%", str(total_duration))

    html_path = tmp_dir / "scene.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"HTML assembled: {html_path}")
    return html_path


# ─────────────────────────────────────────────────────────────
# 4. PUPPETEER FRAME CAPTURE
# ─────────────────────────────────────────────────────────────

PUPPETEER_SCRIPT = """
const puppeteer = require('/home/networkserver/node_modules/puppeteer');
const path = require('path');
const fs = require('fs');

(async () => {
  const htmlPath = process.argv[2];
  const framesDir = process.argv[3];
  const totalDuration = parseFloat(process.argv[4]);
  const fps = parseInt(process.argv[5]) || 24;
  const width = parseInt(process.argv[6]) || 1920;
  const height = parseInt(process.argv[7]) || 1080;

  fs.mkdirSync(framesDir, { recursive: true });

  console.log(`[puppeteer] Launching for ${totalDuration}s at ${fps}fps (${width}x${height})`);

  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--allow-file-access-from-files',
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process',
      `--window-size=${width},${height}`,
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1 });

  // Inject flag so the page knows it's being captured (disables auto-preview)
  await page.evaluateOnNewDocument(() => { window._PUPPETEER_MODE = true; });

  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 30000 });

  // Wait for GSAP and fonts
  await new Promise(r => setTimeout(r, 1200));

  const totalFrames = Math.ceil(totalDuration * fps);
  const dt = 1.0 / fps;

  for (let frame = 0; frame < totalFrames; frame++) {
    const t = frame * dt;
    await page.evaluate((time) => {
      if (window.seekToTime) window.seekToTime(time);
    }, t);

    // Brief settle time for GSAP to apply
    await new Promise(r => setTimeout(r, 8));

    const framePath = path.join(framesDir, String(frame).padStart(6, '0') + '.png');
    await page.screenshot({ path: framePath, type: 'png' });

    if (frame % 60 === 0) {
      const pct = ((frame / totalFrames) * 100).toFixed(1);
      console.log(`[puppeteer] Frame ${frame}/${totalFrames} (${pct}%) t=${t.toFixed(2)}s`);
    }
  }

  await browser.close();
  console.log(`[puppeteer] Done. ${totalFrames} frames written to ${framesDir}`);
})();
"""


def capture_frames(
    html_path: Path,
    frames_dir: Path,
    total_duration: float,
    fps: int,
    width: int,
    height: int,
    tmp_dir: Path,
) -> None:
    """Write the Puppeteer script and run it."""
    script_path = tmp_dir / "capture.js"
    with open(script_path, "w") as f:
        f.write(PUPPETEER_SCRIPT)

    # Find puppeteer binary
    result = subprocess.run(
        ["npm", "root", "-g"], capture_output=True, text=True
    )
    npm_global = result.stdout.strip()
    puppeteer_bin = Path(npm_global) / "puppeteer" / "lib" / "cjs" / "puppeteer" / "node.js"

    print(f"Capturing {math.ceil(total_duration * fps)} frames via Puppeteer...")
    frames_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "node",
        str(script_path),
        str(html_path),
        str(frames_dir),
        str(total_duration),
        str(fps),
        str(width),
        str(height),
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────────
# 5. FFMPEG ENCODE
# ─────────────────────────────────────────────────────────────

def encode_video(
    frames_dir: Path,
    audio_path: Path,
    output_path: Path,
    fps: int,
    max_duration: float | None,
    preset: str = "medium",
) -> None:
    """Combine frame sequence + audio into MP4."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    crf = "18" if preset == "delivery" else "23"
    x264_preset = "slow" if preset == "delivery" else "medium"

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "%06d.png"),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", x264_preset,
        "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
    ]
    if max_duration:
        cmd.extend(["-t", str(max_duration)])
    cmd.append(str(output_path))

    print(f"Encoding: {output_path.name} (preset={preset}, crf={crf})")
    subprocess.run(cmd, check=True)
    size_mb = output_path.stat().st_size / 1_048_576
    print(f"  Output: {output_path.relative_to(ROOT)} ({size_mb:.1f} MB)")


def encode_vertical_crop(
    source_mp4: Path,
    output_path: Path,
    max_duration: float | None,
) -> None:
    """Crop 1920×1080 to 1080×1920 (9:16) centered, scaling for Shorts."""
    # Center crop: x=420 to x=1500 (1080px wide), then scale up to 1080×1920
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_mp4),
        "-vf", "crop=1080:1080:420:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
    ]
    if max_duration:
        cmd.extend(["-t", str(max_duration)])
    cmd.append(str(output_path))
    print(f"Encoding vertical crop: {output_path.name}")
    subprocess.run(cmd, check=True)
    size_mb = output_path.stat().st_size / 1_048_576
    print(f"  Output: {output_path.relative_to(ROOT)} ({size_mb:.1f} MB)")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def render_animated_scene(
    sermon_id: str,
    scene_name: str = "spurgeon",
    audio_path_override: str | None = None,
    captions_path_override: str | None = None,
    output_path_override: str | None = None,
    max_duration: float | None = None,
    fps: int = FPS,
    preset: str = "medium",
    vertical: bool = False,
    keep_frames: bool = False,
) -> None:
    # ── Load data ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f" Rendering: {sermon_id}")
    print(f" Scene: {scene_name} | FPS: {fps} | Duration: {max_duration or 'full'}")
    print(f"{'='*60}\n")

    cap_data = load_captions(sermon_id, captions_path_override)
    captions = cap_data["phrases"]
    sentence_boundaries = cap_data.get("sentence_boundaries", [])

    if max_duration:
        captions = [c for c in captions if c["start"] < max_duration]
        sentence_boundaries = [t for t in sentence_boundaries if t < max_duration]

    total_duration = max_duration or (captions[-1]["end"] if captions else 60.0)
    print(f"Caption phrases: {len(captions)} | Duration: {total_duration:.1f}s")

    audio_path = resolve_audio(sermon_id, audio_path_override)
    print(f"Audio: {audio_path.name}")

    scene_content = load_scene_content(scene_name)
    print(f"Scene Content loaded for {scene_name}.")

    # ── Timeline ───────────────────────────────────────────
    timeline_events = compute_intensity_events(
        audio_path, max_duration, sentence_boundaries
    )

    # ── Output path ────────────────────────────────────────
    if output_path_override:
        output_path = Path(output_path_override)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
    else:
        tag = f"-preview-{int(max_duration)}s" if max_duration else ""
        output_path = OUTPUT_DIR / f"{sermon_id}-animated{tag}.mp4"

    # ── Render ─────────────────────────────────────────────
    with tempfile.TemporaryDirectory(prefix="sermon-anim-") as tmp_str:
        tmp_dir = Path(tmp_str)
        frames_dir = tmp_dir / "frames"

        # Fetch GSAP locally
        gsap_path = fetch_gsap_local(tmp_dir)

        # Build HTML
        html_path = build_html(
            scene_content=scene_content,
            captions=captions,
            timeline_events=timeline_events,
            total_duration=total_duration,
            gsap_path=gsap_path,
            tmp_dir=tmp_dir,
        )

        # Capture frames
        capture_frames(
            html_path=html_path,
            frames_dir=frames_dir,
            total_duration=total_duration,
            fps=fps,
            width=1920,
            height=1080,
            tmp_dir=tmp_dir,
        )

        # Handle keep_frames
        if keep_frames:
            saved_frames = output_path.parent / f"{output_path.stem}_frames"
            shutil.copytree(str(frames_dir), str(saved_frames), dirs_exist_ok=True)
            print(f"Frames saved to: {saved_frames.relative_to(ROOT)}")

        # Encode 16:9
        encode_video(
            frames_dir=frames_dir,
            audio_path=audio_path,
            output_path=output_path,
            fps=fps,
            max_duration=max_duration,
            preset=preset,
        )

        # Encode 9:16 vertical crop
        if vertical:
            vertical_path = output_path.with_name(
                output_path.stem + "-vertical.mp4"
            )
            encode_vertical_crop(output_path, vertical_path, max_duration)

    print(f"\n✓ Render complete: {output_path.relative_to(ROOT)}")
    if vertical:
        print(f"✓ Vertical: {vertical_path.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render animated sermon scene.")
    parser.add_argument("sermon_id", help="Sermon ID from catalog")
    parser.add_argument("--scene", default="spurgeon", help="Scene name (assets/scenes/<scene>/)")
    parser.add_argument("--audio-path", help="Override audio WAV path")
    parser.add_argument("--captions-path", help="Override captions.json path")
    parser.add_argument("--output", help="Override output MP4 path")
    parser.add_argument("--max-duration", type=float, help="Render only first N seconds")
    parser.add_argument("--fps", type=int, default=FPS, help="Frame rate (default: 24)")
    parser.add_argument("--preset", choices=["medium", "delivery"], default="medium",
                        help="Encoding preset: medium (fast) or delivery (smaller/HQ)")
    parser.add_argument("--vertical", action="store_true",
                        help="Also render 9:16 vertical crop for Shorts")
    parser.add_argument("--keep-frames", action="store_true",
                        help="Save PNG frame sequence alongside output")
    args = parser.parse_args()

    render_animated_scene(
        sermon_id=args.sermon_id,
        scene_name=args.scene,
        audio_path_override=args.audio_path,
        captions_path_override=args.captions_path,
        output_path_override=args.output,
        max_duration=args.max_duration,
        fps=args.fps,
        preset=args.preset,
        vertical=args.vertical,
        keep_frames=args.keep_frames,
    )
