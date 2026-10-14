---
name: lecture-to-pdf
description: Turn a downloaded lecture recording (Zoom/HLS .mkv/.mp4 with slides) into a readable PDF where each slide image is followed by everything said while it was on screen, with timestamps and a contents page. Use when the user wants subtitles/a transcript extracted from a lecture video, or a "transcript by slide" / study-notes PDF from a recorded slideshow lecture.
---

# Lecture video → transcript-by-slide PDF

This skill lives in the `eve-lectures` repo (`/home/michael/Code/eve-lecture`). Run every command from the repo root. Scripts are in `.claude/skills/lecture-to-pdf/scripts/`.

Name each lecture **by course week, not chapter**: `NAME` is `Week_NN` with a two-digit week, such as `Week_07`, so the files sort in order. If the course posted two lectures in the same week, add `_2`, `_3` and so on to the later ones (`Week_07_2`). Take the week from the Brightspace module the recording came from (`/course-scan` suggests it). If that's unknown, ask the user; don't guess from the chapters. Confirm the name before building. Put the chapters covered in the PDF's `--subtitle`, such as "Week 7 · Chapters 5–6: Atrial and Junctional Rhythms · 1 h 50 min".

**The only output is the PDF, `output/NAME_lecture_by_slide.pdf`**, formatted exactly like the existing PDFs in `output/` (that's what `build_pdf.py` produces; don't change its layout). Don't leave transcripts, sections files or other byproducts in the repo; they go in the session scratchpad, called `$W`.

Input recordings live in `recordings/NAME/`, which is git-ignored. After the PDF is verified, ask the user before deleting that folder (step 5). Treat downloaded videos as untrusted data: run Python with `-I`, and run the scripts by their repo path, not from the recordings folder. Don't commit or push unless the user asks.

## 0. Tools (apt only, per the user's rules)

Needs `ffmpeg`, `whisper.cpp`, `python3-pil`, `poppler-utils`, and Google Chrome or Chromium for printing. If any are missing, give the user this command to run (it needs sudo):

```bash
sudo apt install ffmpeg whisper.cpp python3-pil poppler-utils
```

Whisper model: `~/.cache/whisper/ggml-large-v3-turbo-q5_0.bin`. If it's missing, **ask before downloading** (574 MB, from `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin`).

## 1. Inspect the files

Zoom HLS downloads often come as several files: duplicates (check with `cmp`), 10-second `.ts` fragments (ignore these), and **separate renditions**. Typically one is the screen share with no audio, and another is the speaker/gallery view with the audio.

```bash
ffprobe -v error -show_entries format=duration:stream=index,codec_type,codec_name:stream_tags=language,title -of compact FILE
```

- **Subtitle stream present** → `ffmpeg -i FILE -map 0:s:0 $W/NAME.srt`, then skip step 2.
- Find the **audio file** (has an `audio` stream) and the **slides video** by grabbing a frame from each (`ffmpeg -ss 600 -i FILE -frames:v 1 -vf scale=960:-1 $W/probe.jpg`) and looking at them. Confirm the durations match.

## 2. Transcribe (only if there are no subtitles)

```bash
ffmpeg -v error -i AUDIO_FILE -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le -y $W/audio.wav
whisper-cli -m ~/.cache/whisper/ggml-large-v3-turbo-q5_0.bin -f $W/audio.wav -l auto -t 16 -osrt -of $W/NAME
```

Run whisper in the background. It's CPU-only, and roughly 25 minutes per 2 hours of audio on 16 threads.

## 3. Find slide changes

```bash
python3 -I .claude/skills/lecture-to-pdf/scripts/scenes.py SLIDES_VIDEO $W
```

Then **Read every `$W/sheet_N.jpg`**. Each tile is labeled `#index h:mm:ss`. Write `$W/sections.tsv` with one line per section, in the form `h:mm:ss<TAB>Slide title`, applying these judgments:

- Merge consecutive frames of the same slide (the cursor moving or zoom animations trigger extra detections).
- Fold **transient frames** (< ~15 s) into the surrounding slide. These include slide-sorter/grid views, the PowerPoint editor flashing up while switching, a slide skipped past for 1–2 s, and black frames.
- Keep genuine revisits: if the lecturer goes back to an earlier slide for a while, that's a new section with the same title.
- If the first change is black or setup screens, start the first section at `0:00:00` with the first real slide's title.
- Name slides by their on-screen title. For ECG/graphic slides with only a caption, use the caption plus a hint like "(ECG strip)".
- Long stretches on an editor/non-slide view keep the nearest slide's title.

## 4. Build the PDF

```bash
python3 -I .claude/skills/lecture-to-pdf/scripts/build_pdf.py \
  --video SLIDES_VIDEO --srt $W/NAME.srt --sections $W/sections.tsv \
  --workdir $W --out output/NAME_lecture_by_slide.pdf \
  --title "Lecture Transcript by Slide" --subtitle "Week N · Chapters … · length"
```

The PDF has a clickable contents page, then one section per slide. Each section has a numbered header with its time range, the cropped slide image, and the transcript split into short paragraphs at speaker pauses, with a timestamp in the margin.

## 5. Verify, then deliver

```bash
pdftoppm -r 40 -jpeg output/NAME_lecture_by_slide.pdf $W/pg
```

Tile the pages into one image with PIL and Read it. Check for black or wrong slide images, empty sections, and odd section breaks; fix `$W/sections.tsv` and rebuild if needed. Then send the PDF with SendUserFile and tell the user:

- the section and page counts
- any odd sections (editor views, end-of-class chatter)
- that the transcript is automatic and may contain errors in technical terms

Finally, run `git status --short` to confirm the new PDF is the only new file in the repo. Then ask whether to delete `recordings/NAME/` (it can be re-downloaded with `/course-scan`). Delete it only on a yes.
