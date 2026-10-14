#!/usr/bin/env python3
"""Build a "transcript by slide" PDF: each slide image followed by what was said while it was shown.

Usage:
  python3 -I build_pdf.py --video SCREEN_VIDEO --srt TRANSCRIPT.srt --sections SECTIONS.tsv \
      --workdir WORKDIR --out OUT.pdf --title "Lecture Transcript by Slide" [--subtitle "..."] [--end h:mm:ss]

SECTIONS.tsv: one line per slide section, "h:mm:ss<TAB>Slide title", in time order.
Each section runs until the next section's start (the last one runs to the end of the video, or to --end).
To split one recording into two PDFs, give each its own sections file covering its part, and --end for the first.
"""
import argparse, html, os, shutil, subprocess
from PIL import Image, ImageStat

ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True)
ap.add_argument("--srt", required=True)
ap.add_argument("--sections", required=True)
ap.add_argument("--workdir", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--title", default="Lecture Transcript by Slide")
ap.add_argument("--subtitle", default="")
ap.add_argument("--end", help="h:mm:ss where the last section ends, if before the end of the video")
args = ap.parse_args()


def secs(t):
    h, m, s = t.strip().replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def fmt(x):
    x = int(x)
    return f"{x // 3600}:{x % 3600 // 60:02}:{x % 60:02}"


duration = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.video],
    capture_output=True, text=True, check=True).stdout.strip())

sections = [l.split("\t", 1) for l in open(args.sections).read().strip().split("\n") if l.strip()]
starts = [secs(t) for t, _ in sections] + [secs(args.end) if args.end else duration]

cues = []
for block in open(args.srt, encoding="utf-8").read().strip().split("\n\n"):
    l = block.strip().split("\n")
    if len(l) < 3 or "-->" not in l[1]:
        continue
    a, b = l[1].split(" --> ")
    cues.append((secs(a), secs(b), " ".join(x.strip() for x in l[2:]).strip()))


def paragraphs(cs):
    """Break at speaker pauses (>1.2 s) or every few sentences in long unbroken stretches."""
    paras, cur, words = [], [], 0
    for i, (a, b, t) in enumerate(cs):
        if cur:
            gap = a - cs[i - 1][1]
            ends = cs[i - 1][2].rstrip().endswith((".", "?", "!"))
            if (gap > 1.2 and words >= 25) or (words >= 110 and ends) or words >= 170:
                paras.append(cur)
                cur, words = [], 0
        cur.append((a, t))
        words += len(t.split())
    if cur:
        if paras and words < 12:
            paras[-1] += cur  # fold a tiny tail into the previous paragraph
        else:
            paras.append(cur)
    return [(p[0][0], " ".join(t for _, t in p)) for p in paras]


imgdir = os.path.join(args.workdir, "pdfimg")
shutil.rmtree(imgdir, ignore_errors=True)
os.makedirs(imgdir)

toc, body = [], []
for i, (t, title) in enumerate(sections):
    st, en = starts[i], starts[i + 1]
    img = os.path.join(imgdir, f"slide_{i + 1:03}.jpg")
    # Grab a few seconds in (past transitions). If that frame is mostly blank or dark (a black
    # frame, or Zoom's speaker-name screen), retry mid-section, then just after the start.
    for g in (st + min(6, (en - st) / 2), (st + en) / 2, st + min(1, (en - st) / 4)):
        subprocess.run(["ffmpeg", "-v", "quiet", "-ss", str(g), "-i", args.video, "-frames:v", "1", "-y", img],
                       check=True)
        im = Image.open(img).convert("RGB")
        bbox = im.point(lambda p: 255 if p > 24 else 0).convert("L").getbbox()
        if bbox:
            mean = sum(ImageStat.Stat(im.crop(bbox).convert("L")).mean)
        if bbox and (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 0.2 * im.width * im.height and mean > 90:
            break
    if bbox:
        im = im.crop(bbox)  # trim black pillarbox around 4:3 slides
    im.thumbnail((1400, 1400))
    im.save(img, quality=85)

    paras = paragraphs([c for c in cues if st <= c[0] < en])
    toc.append(f'<li><a href="#s{i + 1}"><span class="tt">{fmt(st)}</span>{html.escape(title)}</a></li>')
    ptxt = "".join(f'<div class="para"><span class="ts">{fmt(a)}</span><p>{html.escape(x)}</p></div>'
                   for a, x in paras) or '<p class="none">(Nothing was said while this slide was shown.)</p>'
    body.append(f'''<section id="s{i + 1}"><header><span class="num">{i + 1}</span><div><h2>{html.escape(title)}</h2>
<div class="time">{fmt(st)} – {fmt(en)}</div></div></header>
<figure><img src="file://{img}"></figure>{ptxt}</section>''')

subtitle = html.escape(args.subtitle) + ("<br>" if args.subtitle else "")
doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(args.title)}</title><style>
@page {{ size: Letter; margin: 0.65in 0.75in; }}
body {{ font-family: 'Liberation Serif', 'DejaVu Serif', Georgia, serif; font-size: 11.5pt; line-height: 1.55; color: #1a1a1a; }}
h1, h2, header, .ts, .time, .toc, .sub, .num {{ font-family: 'Liberation Sans', 'DejaVu Sans', sans-serif; }}
h1 {{ font-size: 22pt; margin: 0 0 4pt; }}
.sub {{ color: #555; font-size: 10pt; margin-bottom: 20pt; }}
.toc {{ list-style: none; padding: 0; columns: 2; column-gap: 24pt; font-size: 9.5pt; }}
.toc li {{ break-inside: avoid; margin: 0 0 4pt; }}
.toc a {{ color: #1a1a1a; text-decoration: none; }}
.tt {{ display: inline-block; width: 44pt; color: #1f5fa8; font-variant-numeric: tabular-nums; }}
section {{ break-before: page; }}
header {{ display: flex; align-items: center; gap: 10pt; border-bottom: 2pt solid #1f5fa8; padding-bottom: 6pt; margin-bottom: 12pt; }}
.num {{ background: #1f5fa8; color: #fff; font-weight: bold; font-size: 11pt; min-width: 22pt; height: 22pt; border-radius: 11pt;
        display: flex; align-items: center; justify-content: center; }}
h2 {{ font-size: 15pt; margin: 0; line-height: 1.2; }}
.time {{ color: #666; font-size: 9pt; margin-top: 2pt; }}
figure {{ margin: 0 auto 16pt; text-align: center; break-inside: avoid; }}
figure img {{ max-width: 85%; max-height: 3.5in; border: 1px solid #d0d0d0; box-shadow: 0 1pt 4pt rgba(0,0,0,.12); }}
.para {{ display: flex; gap: 12pt; margin: 0 0 10pt; }}
.ts {{ flex: 0 0 42pt; color: #1f5fa8; font-size: 8.5pt; padding-top: 3pt; font-variant-numeric: tabular-nums; }}
.para p {{ margin: 0; text-align: left; orphans: 3; widows: 3; }}
.none {{ color: #777; font-style: italic; }}
</style></head><body>
<h1>{html.escape(args.title)}</h1>
<div class="sub">{subtitle}Auto-transcribed, so expect occasional errors, especially in technical terms. Timestamps are positions in the recording.</div>
<ol class="toc">{''.join(toc)}</ol>
{''.join(body)}</body></html>"""
html_path = os.path.join(args.workdir, "lecture.html")
open(html_path, "w", encoding="utf-8").write(doc)

chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
if not chrome:
    raise SystemExit("No Chrome/Chromium found to print the PDF.")
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--user-data-dir={os.path.join(args.workdir, 'chrome-profile')}",
                f"--print-to-pdf={os.path.abspath(args.out)}", f"file://{os.path.abspath(html_path)}"],
               check=True, capture_output=True)
print(f"{len(sections)} sections, {len(cues)} cues -> {args.out}")
