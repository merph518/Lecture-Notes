#!/usr/bin/env python3
"""Detect slide changes in a screen-share video and build labeled contact sheets.

Usage: python3 -I scenes.py VIDEO WORKDIR [THRESHOLD]

Writes to WORKDIR:
  scene_times.txt   one timestamp (seconds) per detected screen change
  scenes/s_NNNN.jpg the frame at each change
  sheet_N.jpg       3x3 contact sheets labeled "#index  h:mm:ss" for reading slide titles
"""
import glob, os, re, shutil, subprocess, sys
from PIL import Image, ImageDraw

video, work = sys.argv[1], sys.argv[2]
threshold = sys.argv[3] if len(sys.argv) > 3 else "0.08"
scenes = os.path.join(work, "scenes")
shutil.rmtree(scenes, ignore_errors=True)
os.makedirs(scenes)

# fps=2 keeps decoding fast; showinfo logs pts_time for every selected frame.
vf = f"fps=2,scale=640:-1,select='eq(n\\,0)+gt(scene\\,{threshold})',showinfo"
log = subprocess.run(
    ["ffmpeg", "-hide_banner", "-loglevel", "info", "-i", video, "-an", "-vf", vf,
     "-fps_mode", "vfr", "-q:v", "4", os.path.join(scenes, "s_%04d.jpg")],
    capture_output=True, text=True).stderr
times = re.findall(r"pts_time:([0-9.]+)", log)
open(os.path.join(work, "scene_times.txt"), "w").write("\n".join(times) + "\n")

files = sorted(glob.glob(os.path.join(scenes, "s_*.jpg")))
assert len(times) == len(files), (len(times), len(files))
for old in glob.glob(os.path.join(work, "sheet_*.jpg")):
    os.remove(old)

W, H, C = 640, 360, 3
for k in range(0, len(files), 9):
    sheet = Image.new("RGB", (W * C, (H + 24) * 3), "white")
    d = ImageDraw.Draw(sheet)
    for j, (f, t) in enumerate(zip(files[k:k + 9], times[k:k + 9])):
        x, y = (j % C) * W, (j // C) * (H + 24)
        sheet.paste(Image.open(f).resize((W, H)), (x, y + 24))
        t = float(t)
        d.text((x + 6, y + 4), f"#{k + j + 1}  {int(t // 3600)}:{int(t % 3600 // 60):02}:{int(t % 60):02}",
               fill="red", font_size=18)
    sheet.save(os.path.join(work, f"sheet_{k // 9 + 1}.jpg"), quality=80)

print(f"{len(times)} screen changes; {(len(files) + 8) // 9} contact sheets in {work}")
