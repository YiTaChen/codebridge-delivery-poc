"""Shorten only model waiting intervals; retain real actions/results. No synthetic responses."""
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work" / "recording"
try:
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    raise SystemExit("Install ffmpeg or pip install imageio-ffmpeg first.")
timeline = json.loads((WORK / "timeline.json").read_text())
video = (WORK / "video-path.txt").read_text().strip()
pieces = []
cursor = 0.0
for wait in timeline["waits"]:
    if wait["end"] <= wait["start"]:
        continue
    pieces.append((cursor, wait["start"], 1.0))
    length = wait["end"] - wait["start"]
    pieces.append((wait["start"], wait["end"], min(1.0, 3.0 / length)))
    cursor = wait["end"]
pieces.append((cursor, None, 1.0))
filters = []
for index, (start, end, speed) in enumerate(pieces):
    stop = f":end={end:.3f}" if end is not None else ""
    filters.append(f"[0:v]trim=start={start:.3f}{stop},setpts={speed:.8f}*(PTS-STARTPTS),fps=24[v{index}]")
filters.append("".join(f"[v{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=1:a=0[out]")
out = ROOT / "walkthrough.mp4"
subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", video,
                "-filter_complex", ";".join(filters), "-map", "[out]", "-an", "-c:v", "libx264",
                "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], check=True)
probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(out)], capture_output=True, text=True)
match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
if not match:
    raise SystemExit("Could not verify video duration")
duration = int(match[1])*3600 + int(match[2])*60 + float(match[3])
if duration >= 120:
    raise SystemExit(f"Demo exceeds the 120-second limit: {duration}")
timeline["edited_duration_seconds"] = duration
timeline["editing"] = "Only model waiting intervals accelerated to 3 seconds each; captions disclose acceleration. No results replaced. Silent captioned recording."
(ROOT / "docs" / "demo_timeline.json").write_text(json.dumps(timeline, indent=2) + "\n")
print(f"Verified demo duration: {duration:.2f}s; file: {out.name}")
