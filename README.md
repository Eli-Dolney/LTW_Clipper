# 🎬 LTW Video Splitter Pro

**Local-first YouTube automation studio.** Turn long videos into platform-ready short-form clips with captions, smart reframing, and publish-ready metadata — all on your own machine.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)
![Offline](https://img.shields.io/badge/Runs-100%25%20Local-brightgreen.svg)
![No API Keys](https://img.shields.io/badge/API%20Keys-None%20Required-blueviolet.svg)

## Why LTW?

- **No subscriptions, no API keys.** Whisper transcription, face-tracked reframing, and caption rendering all run locally.
- **Ollama-optional.** If you run a local LLM via [Ollama](https://ollama.com) the tool uses it for titles, descriptions, hooks, and tags. If not, a deterministic heuristic + template path still ships usable copy.
- **Produces a complete clip bundle** per highlight: portrait video with burned-in captions, horizontal version, thumbnail, `.srt`/`.vtt`/`.ass`, plus `youtube.txt` and `tiktok.txt` you can paste straight into the upload form.

## ✨ Features

### New in 2.2 (channel templates & transitions)

- **Channel Templates** — niche presets (Game Dev, Video Editing, Gaming, Geopolitics, AI, Long-form) that tune the *whole* pipeline: highlight detection hook phrases/words, scoring weights, caption style, and the channel's voice (persona/tone/title-style/hashtags). Pick one, tweak it, save your own, import/export.
- **Asset Packs ("add folder")** — point at the folders where your DaVinci transition / SFX packs live (local, external drive, or a synced cloud folder). Nothing is copied; offline folders are flagged and re-appear when available.
- **Automatic transitions + SFX** — build a short-form montage from multiple clips with ffmpeg `xfade`/`acrossfade` and a transition sound mixed at each cut (`python -m src.core.render.transitions`). 100% local, no Resolve needed.
- **Resolve SFX + transition placer** — `LTW_Place_SFX_At_Beats.lua` imports an SFX pack, drops a hit on every beat, and marks every cut with your transition note for a one-pass `Cmd+T`.

### New in 2.1 (modernized build)

- **Studio tab** — review `plan.json`, virality scores, thumbnails; re-run pipeline with resume
- **Settings: Local AI** — Whisper model, hwaccel, caption preset, Ollama check (no API keys)
- **Resumable runs** — atomic `manifest.json` skips finished clips after interruption
- **Local Whisper ASR** (`faster-whisper`) with word-level timestamps
- **Smart 9:16 reframing** with MediaPipe face tracking + smoothing (deadzone tuned for vertical)
- **Burn-in captions** with 4 presets: `bold_outline`, `minimal`, `mrbeast`, `tiktok`
- **Heuristic highlight scorer** (audio energy, hook phrases, length fit) with optional Ollama polish
- **YouTube + Shorts/TikTok metadata** auto-generated: title, description, chapters, tags, hashtags, thumbnail headline
- **Hardware-accelerated rendering** (VideoToolbox on macOS, NVENC / QSV / VAAPI on Win/Linux) with libx264 fallback
- **Typed configuration** (`config/settings.yaml`) and pydantic `Settings` model
- **Pytest suite** for all deterministic logic (no ffmpeg/ASR required to run tests)

### Existing capabilities

- **Professional GUI** — dark, modern, sidebar navigation
- **Time-based or scene-detection splitting**
- **Quality Presets** — YouTube SD/HD/4K + original
- **DaVinci Resolve integration** — 11 Lua automation scripts
- **Batch processing** with resumable runs
- **Preset system** for repeatable workflows
- **Full CLI** for automation

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/Eli-Dolney/LTW_Clipper.git
cd LTW_Clipper

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install `ffmpeg` (required):

```bash
# macOS
brew install ffmpeg
# Debian/Ubuntu
sudo apt install ffmpeg
```

### 2. (Optional) Install Ollama for smarter copy

```bash
brew install ollama
ollama pull llama3.1:8b
```

### 3. Launch

```bash
python launch_gui.py
```

Or double-click:
- **macOS**: `LTW_Video_Splitter.command`
- **Windows**: `LTW_Video_Splitter.bat`

### CLI

```bash
# Split a long video by duration
python -m src.core.video_splitter -i videos/ -o ~/Desktop/clips

# Vertical conversion with smart face tracking
python -m src.core.vertical_cropper --file my_video.mp4 --mode smart

# Classic center crop (no tracking)
python -m src.core.vertical_cropper --file my_video.mp4 --mode center
```

## ⚙️ Configuration

Copy `config/settings.example.yaml` to `config/settings.yaml` and tweak:

```yaml
whisper:
  model: "small"          # tiny | base | small | medium | large-v3
ffmpeg:
  hwaccel: "auto"         # auto | videotoolbox | nvenc | qsv | vaapi | cpu
ollama:
  enabled: true           # set false to skip LLM polish entirely
captions:
  preset: "bold_outline"
  burn_in: true
```

Any value can also be overridden with env vars like `LTW_WHISPER__MODEL=medium`.

## 🎛️ Channel Templates & Transitions

Channel templates live in `assets/templates/*.json` and drive niche-specific
highlight detection and copy. In the GUI, open the **Templates** tab to pick a
niche (e.g. *Game Dev Tutorial*, *Gaming*, *Geopolitics*, *AI Channel*), edit its
hook phrases / scoring weights / voice, then **Use in Opus Clip AI** to run the
pipeline with that tuning. Save custom variants or import/export to share.

Add your transition/SFX packs from the same tab via **Add folder** (works with
local disks, external drives, or synced cloud folders — paths only, never copied).

Build an automatic montage with transitions + a whoosh at each cut:

```bash
python -m src.core.render.transitions clip1.mp4 clip2.mp4 clip3.mp4 \
  -o montage.mp4 --transition dissolve --duration 0.5 --sfx whoosh.wav
```

In DaVinci Resolve, run `LTW_Place_SFX_At_Beats.lua` to auto-place SFX on every
beat and mark each cut with your chosen transition.

## 📦 Per-clip output bundle

Each highlight produces:

```
ltw_output/<project>/
  plan.json
  transcript.json
  manifest.json
  clips/<slug>/
    clip.mp4                      # horizontal (original aspect)
    clip_portrait.mp4             # 9:16, face-tracked, captions burned in
    thumbnail.jpg
    captions.ass                  # stylized (for editing in Resolve or re-burning)
    captions.srt
    captions.vtt
    metadata.json                 # structured metadata (title, desc, tags, chapters, score)
    youtube.txt                   # copy-paste ready
    tiktok.txt                    # caption + hashtags
```

## 🧠 How the AI works (all local)

```
long video
  -> ffprobe (duration, fps, size)
  -> faster-whisper (word timestamps, local)
  -> heuristic scorer (audio energy, hook phrases, length fit, completeness)
  -> (optional) Ollama re-rank + rewrite titles/descriptions/tags
  -> MediaPipe face tracking -> smoothed 9:16 crop path
  -> ffmpeg render + ASS caption burn
  -> per-clip bundle
```

No component calls out to the cloud. If Ollama isn't running, the
highlight engine falls back to deterministic templates and everything still
works.

## 📦 Packaging (macOS)

```bash
python scripts/first_run_setup.py
pyinstaller build/ltw_splitter.spec
xattr -dr com.apple.quarantine "dist/LTW Video Splitter.app"  # if Gatekeeper blocks
```

See [build/README.md](build/README.md).

## 🧪 Development

```bash
# Run the test suite
venv/bin/python -m pytest -q

# Lint + type check
pip install -e .[dev]
ruff check .
black --check .
mypy src
```

## 📁 Project structure

```
LTW_Clipper/
├── src/
│   ├── config/             # pydantic Settings loader
│   ├── core/
│   │   ├── ai/             # transcriber, ollama, heuristic scorer, highlight engine, metadata
│   │   ├── templates/      # channel templates (niche presets) + manager
│   │   ├── assets/         # asset pack registry/scanner (transitions, SFX, overlays)
│   │   ├── reframe/        # MediaPipe tracker + ffmpeg reframe renderer
│   │   ├── captions/       # ASS/SRT/VTT styler + burner
│   │   ├── render/         # ffmpeg helpers (probe, hwaccel, extract, thumbnail, transitions)
│   │   ├── opus_clip_processor.py   # end-to-end pipeline
│   │   ├── video_splitter.py
│   │   ├── vertical_cropper.py
│   │   └── ...
│   └── gui/                # CustomTkinter app
├── resolve_scripts/        # DaVinci Resolve Lua automation
├── presets/                # Workflow presets (JSON)
├── config/
│   └── settings.example.yaml
├── tests/
├── pyproject.toml
└── requirements.txt
```

## 📄 License

MIT — see [LICENSE](LICENSE).

---

**Made for creators who want control, local-first tools, and zero API bills.**
