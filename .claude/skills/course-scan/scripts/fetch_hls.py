#!/usr/bin/env python3
"""Download an HLS (.m3u8) lecture stream to one .mkv with both video and audio, then check it.

Usage: python3 -I fetch_hls.py M3U8_URL OUT.mkv [--referer URL]

Give it the MASTER playlist (the first .m3u8 the player requests). Zoom recordings in
Brightspace often put video and audio in separate renditions; the master playlist lets
ffmpeg pick the best video and the audio track and mux them into a single file.
Exits non-zero if the result is missing a video or an audio stream.
"""
import argparse, json, os, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("out")
ap.add_argument("--referer")
a = ap.parse_args()

if os.path.exists(a.out):
    sys.exit(f"{a.out} already exists; not overwriting.")
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-stats"]
if a.referer:
    cmd += ["-headers", f"Referer: {a.referer}\r\n"]
cmd += ["-i", a.url, "-map", "0:v:0?", "-map", "0:a:0?", "-c", "copy", a.out]
tmp_ok = subprocess.run(cmd).returncode == 0
if not tmp_ok:
    if os.path.exists(a.out):
        os.remove(a.out)
    sys.exit("ffmpeg failed (expired link, or the stream needs the browser session). Get a fresh .m3u8 URL and retry.")

info = json.loads(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", a.out],
    capture_output=True, text=True, check=True).stdout)
kinds = {s["codec_type"] for s in info.get("streams", [])}
dur = float(info["format"].get("duration", 0))
size = os.path.getsize(a.out) / 1e6
print(f"{a.out}: {int(dur // 3600)}:{int(dur % 3600 // 60):02}:{int(dur % 60):02}, {size:.0f} MB, streams: {', '.join(sorted(kinds))}")
missing = {"video", "audio"} - kinds
if missing:
    sys.exit(f"Missing {', '.join(sorted(missing))}: this was probably a single rendition, not the master playlist.")
