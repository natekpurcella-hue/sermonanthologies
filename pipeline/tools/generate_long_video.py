import json
import argparse
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog/sermons.jsonl"
TEMPLATES_DIR = ROOT / "assets/video_templates"
OUTPUT_DIR = ROOT / "output/video/long"
VIDEO_SIZE = (1920, 1080)
TITLE_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
AUTHOR_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def load_sermon_record(sermon_id):
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record["sermon_id"] == sermon_id:
                return record
    raise ValueError(f"Sermon {sermon_id} not found.")


def markdown_title(record):
    filename = record.get("filename")
    if not filename:
        return None

    sermon_path = ROOT / filename
    if not sermon_path.exists():
        return None

    with open(sermon_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    return None


def resolve_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return ROOT / path


def wrapped_lines(draw, text, font, max_width):
    lines = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=2)
            if bbox[2] - bbox[0] <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def fit_title(draw, title, max_width, max_height):
    for font_size in range(82, 39, -2):
        font = ImageFont.truetype(str(TITLE_FONT), font_size)
        lines = wrapped_lines(draw, title, font, max_width)
        line_boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=2) for line in lines]
        line_height = max(box[3] - box[1] for box in line_boxes)
        total_height = len(lines) * line_height + (len(lines) - 1) * 18
        widest = max(box[2] - box[0] for box in line_boxes)
        if widest <= max_width and total_height <= max_height:
            return font, lines, line_height, total_height

    font = ImageFont.truetype(str(TITLE_FONT), 40)
    lines = textwrap.wrap(title, width=32)
    line_height = draw.textbbox((0, 0), "Ag", font=font, stroke_width=2)[3]
    total_height = len(lines) * line_height + (len(lines) - 1) * 18
    return font, lines, line_height, total_height


def render_overlay(title, author_name, output_path):
    image = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    title_font, title_lines, line_height, title_height = fit_title(
        draw, title, max_width=1500, max_height=220
    )
    author_font = ImageFont.truetype(str(AUTHOR_FONT), 42)

    y = 430 - title_height // 2
    for line in title_lines:
        draw.text(
            (VIDEO_SIZE[0] // 2, y),
            line,
            font=title_font,
            fill=(245, 245, 245, 255),
            anchor="ma",
            align="center",
            stroke_width=3,
            stroke_fill=(0, 0, 0, 210),
        )
        y += line_height + 18

    draw.text(
        (VIDEO_SIZE[0] // 2, 575),
        f"by {author_name}",
        font=author_font,
        fill=(220, 220, 220, 255),
        anchor="ma",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 210),
    )

    image.save(output_path)


def generate_long_video(
    sermon_id,
    audio_path=None,
    background_path=None,
    output_path=None,
    max_duration=None,
    preset="fast",
):
    record = load_sermon_record(sermon_id)

    if audio_path is None:
        audio_path = ROOT / "output/final_sermons" / f"{sermon_id}.wav"
    else:
        audio_path = resolve_path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found at {audio_path}. Run retrieve_results.py first."
        )

    if background_path is None:
        background_path = TEMPLATES_DIR / "loop_static.mp4"
    else:
        background_path = resolve_path(background_path)

    if not background_path.exists():
        raise FileNotFoundError(f"Template not found at {background_path}.")

    if output_path is None:
        output_path = OUTPUT_DIR / f"{sermon_id}.mp4"
    else:
        output_path = resolve_path(output_path)

    title = markdown_title(record) or record["title"]
    print(f"Generating long-form video for: {title}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Encoding quality preset
    if preset == "delivery":
        preset_name, crf_value = "slow", "18"
    else:
        preset_name, crf_value = "ultrafast", "23"

    with tempfile.TemporaryDirectory(prefix="sermon-video-") as temp_dir:
        overlay_path = Path(temp_dir) / "overlay.png"
        render_overlay(title, record["author_name"], overlay_path)

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(background_path),
            "-i",
            str(audio_path),
            "-loop",
            "1",
            "-i",
            str(overlay_path),
            "-filter_complex",
            (
                "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
                "crop=1920:1080,format=rgba[bg];"
                "[bg][2:v]overlay=0:0:format=auto,format=yuv420p[v]"
            ),
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-shortest",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-preset",
            preset_name,
            "-crf",
            crf_value,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
        ]
        if max_duration is not None:
            command.extend(["-t", str(max_duration)])
        command.append(str(output_path))

        subprocess.run(command, check=True)

    print(f"Video rendered successfully: {output_path.relative_to(ROOT)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate long-form sermon video.")
    parser.add_argument("sermon_id", help="The sermon ID to process")
    parser.add_argument("--audio-path", help="Path to the mastered sermon WAV.")
    parser.add_argument("--background-path", help="Path to the looping video background.")
    parser.add_argument("--output-path", help="Path for the rendered MP4.")
    parser.add_argument(
        "--max-duration",
        type=float,
        help="Render only the first N seconds. Useful for smoke tests.",
    )
    parser.add_argument(
        "--preset",
        choices=["fast", "delivery"],
        default="fast",
        help="Encoding preset: fast (ultrafast/crf23) or delivery (slow/crf18, smaller HQ file).",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Route through the legacy static overlay path instead of the animated renderer.",
    )
    parser.add_argument(
        "--scene",
        default="spurgeon",
        help="Scene name for animated mode (default: spurgeon).",
    )
    args = parser.parse_args()

    if not args.static:
        # Route to animated renderer
        from render_animated_scene import render_animated_scene
        render_animated_scene(
            sermon_id=args.sermon_id,
            scene_name=args.scene,
            audio_path_override=args.audio_path,
            output_path_override=args.output_path,
            max_duration=args.max_duration,
            preset=args.preset,
        )
    else:
        generate_long_video(
            args.sermon_id,
            audio_path=args.audio_path,
            background_path=args.background_path,
            output_path=args.output_path,
            max_duration=args.max_duration,
            preset=args.preset,
        )
