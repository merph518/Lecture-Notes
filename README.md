# Eve's Lectures

Study notes made from Eve's recorded lectures. Each lecture becomes a **transcript-by-slide PDF**: every slide shown in the recording, followed by everything said while it was on screen, with timestamps and a clickable contents page.

> **Keep this repo private.** The PDFs contain images of the publisher's (Pearson) textbook slides.

## Lectures

All PDFs are in [`output/`](output/), named by course week and topic (`Week_04_Analyzing_EKG_Rhythm_Strips.pdf`, with `_2` for a second lecture in the same week).

| Week | Lecture | PDF |
|---|---|---|
| 1 | Cardiac Anatomy and Physiology: Appendix A, 22 min | [Week_01_Cardiac_Anatomy_and_Physiology.pdf](output/Week_01_Cardiac_Anatomy_and_Physiology.pdf) |
| 1 | Electrophysiology: Chapter 1, 27 min (also posted under Week 2) | [Week_01_2_Electrophysiology.pdf](output/Week_01_2_Electrophysiology.pdf) |
| 2 | 12 Lead EKGs: Appendix C, 26 min | [Week_02_12_Lead_EKGs.pdf](output/Week_02_12_Lead_EKGs.pdf) |
| 3 | Waves and Measurements: Chapter 2, 33 min (first part of the Week 3 recording) | [Week_03_Waves_and_Measurements.pdf](output/Week_03_Waves_and_Measurements.pdf) |
| 4 | Analyzing EKG Rhythm Strips: Chapter 3 plus a 12-lead review, 1 h 10 min (Week 3 recording from 33:18) | [Week_04_Analyzing_EKG_Rhythm_Strips.pdf](output/Week_04_Analyzing_EKG_Rhythm_Strips.pdf) |
| 7 | Atrial and Junctional Rhythms: Chapters 5–6, 1 h 50 min (also posted under Week 8; to be split at 1:08:30) | [Week_07_Atrial_and_Junctional_Rhythms.pdf](output/Week_07_Atrial_and_Junctional_Rhythms.pdf) |

## Finding and downloading lectures

Run `/course-scan <course URL>` with the Brightspace course link, such as `https://<school>.brightspace.com/d2l/home/123456`. The skill, in [`.claude/skills/course-scan/`](.claude/skills/course-scan/SKILL.md):

1. Opens the course in your Chrome, which is already signed in. If you're not signed in, it asks you to sign in yourself; it never types passwords.
2. Reads the course's contents through Brightspace's API ([`d2l_toc.js`](.claude/skills/course-scan/scripts/d2l_toc.js)) and picks out the lecture recordings.
3. Shows you a list of every video with its module, duration, suggested name and status (new, downloaded, or already has a PDF).
4. Downloads only the lectures you approve. It uses [`fetch_hls.py`](.claude/skills/course-scan/scripts/fetch_hls.py), which saves the course player's stream as a single `recordings/<name>/<name>.mkv` with both video and audio, then checks it.

Videos hosted elsewhere (Zoom share links, YouTube, Panopto and so on) are listed but not downloaded.

## Making a PDF for a new lecture

1. Get the lecture recording into `recordings/<name>/`, either with `/course-scan` or by downloading the Zoom/HLS `.mkv`/`.mp4` files yourself. For example: `recordings/Week_07/`.
2. Open Claude Code in this folder and run `/lecture-to-pdf`, or just ask for a transcript-by-slide PDF of the new recording.

The skill, in [`.claude/skills/lecture-to-pdf/`](.claude/skills/lecture-to-pdf/SKILL.md), runs the steps below. **The PDF in `output/` is the only thing it keeps.** Transcripts and slide lists are temporary working files, and it asks before deleting the downloaded recording once the PDF is checked.

1. **Inspect the files.** Zoom downloads often include duplicates, 10-second `.ts` fragments, and separate renditions: one with the screen share (often silent) and one with the audio. If the file has a subtitle track, that's used instead of transcribing.
2. **Transcribe** the audio with [whisper.cpp](https://github.com/ggerganov/whisper.cpp), using the `large-v3-turbo` model.
3. **Find slide changes.** [`scenes.py`](.claude/skills/lecture-to-pdf/scripts/scenes.py) detects screen changes and makes labeled contact sheets. Claude reads them and writes a temporary slide list (one `h:mm:ss<TAB>Slide title` line per slide), leaving out quick flips, slide-sorter views and editor flashes.
4. **Build the PDF.** [`build_pdf.py`](.claude/skills/lecture-to-pdf/scripts/build_pdf.py) grabs a cropped image of each slide, splits the transcript into paragraphs at speaker pauses, and prints `output/<name>_<Topic>.pdf` with headless Chrome. The formatting matches the Chapter 5–6 PDF.
5. **Check** the rendered pages, then fix the slide list and rebuild if needed.

### Running the scripts by hand

```bash
python3 -I .claude/skills/lecture-to-pdf/scripts/scenes.py SLIDES_VIDEO WORKDIR
# read WORKDIR/sheet_*.jpg and write WORKDIR/sections.tsv
python3 -I .claude/skills/lecture-to-pdf/scripts/build_pdf.py \
  --video SLIDES_VIDEO --srt WORKDIR/<name>.srt --sections WORKDIR/sections.tsv \
  --workdir WORKDIR --out output/<name>_<Topic>.pdf --subtitle "Week N · Chapters … · length"
```

## Requirements

Ubuntu packages (install with apt):

```bash
sudo apt install ffmpeg whisper.cpp python3-pil poppler-utils
```

You also need Google Chrome or Chromium to print the PDF, and the Whisper model at `~/.cache/whisper/ggml-large-v3-turbo-q5_0.bin` (574 MB, from [huggingface.co/ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp)).

Transcription runs on the CPU and takes about 25 minutes for a 2-hour lecture.

## Notes

- Recordings and audio (`*.mkv`, `*.mp4`, `*.ts`, `*.wav`, `*.m4a`) are git-ignored because they're too large for GitHub.
- Transcripts are automatic and may contain errors, especially in medical terms.
