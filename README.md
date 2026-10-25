# Polyphonic Scorer

A lightweight pipeline designed to turn raw, unquantized machine learning audio transcriptions from [Basic Pitch](https://github.com/spotify/basic-pitch)) into clean, human-readable **MusicXML** sheet music.

## Overview

ML transcription models output raw timestamps in seconds and continuous pitch data. Importing these raw outputs directly into notation software such as MuseScore, results in messy, unreadable sheet music full of micro-rests, complex ties, and 64th notes.

This project bridges the gap between raw ML outputs and rigid notation software through a 5-stage cleaning and quantization engine:

1. **Clean & Denoise:** Eliminates acoustic artifacts, fret buzz, and double-trigger glitches.
2. **Tempo & Rubato Tracking:** Uses Kernel Density Estimation (KDE) and Phase-Locked Loops (PLL) to fit human micro-timing and tempo variations onto an elastic beat grid.
3. **Quantization:** Snaps cleaned note events accurately to musical subdivisions (e.g., 16th notes).
4. **Voice & Staff Distribution:** Dynamically splits notes across staves (bass/treble via hand contour tracking) and routes voices/stem directions.
5. **MusicXML Export:** Outputs standard `.musicxml` files ready for print or editing.

---

## Key Features

* **Elastic Rubato Tracking:** Handles expressive human performance timings without producing unwanted tuplets or micro-rhythms.
* **Acoustic Artifact Cleanup:** Filters out low-velocity ghost notes and merges rapid double-trigger glitches.
* **Smart Voice Separation:** Uses dynamic contour tracking instead of rigid middle-C splits to separate hands cleanly on piano or route multi-voice stems on guitar.
* **Key & Time Signature Detection:** Automated key spelling via the Krumhansl-Schmuckler algorithm.
* **Dependency-Free XML Generation:** Features a lightweight, custom MusicXML fallback builder if `music21` is not installed.

---

## Installation

Clone the repository and install core dependencies:

```bash
git clone https://github.com/tia-s/polyphonic-engine.git
cd polyphonic-engine
pip install numpy scipy
```

### Optional Dependencies
Depending on your input files and preferred export engine:
* `basic-pitch` — Required for transcribing raw `.wav` or `.mp3` audio files.
* `pretty_midi` — Required for reading `.mid` inputs.
* `music21` — Optional advanced MusicXML export engine.

---

## Quickstart

### Command Line Interface

Process an audio, MIDI, or pre-extracted JSON file directly:

```bash
# Process audio directly to MusicXML
python main.py input_audio.wav --output score.musicxml

# Process with explicit grid settings and staff mode
python main.py transcription.json --staff-mode piano --grid 16th
```

### Python API Usage

```python
from preprocessor import Preprocessor, Note

# 1. Define or load raw notes from Basic Pitch output
raw_notes = [
    Note(start=0.0, end=0.50, pitch=60, velocity=0.8),
    Note(start=0.5, end=0.72, pitch=67, velocity=0.7),
    Note(start=0.73, end=1.00, pitch=67, velocity=0.6),  # Unison glitch
    Note(start=1.2, end=1.25, pitch=61, velocity=0.08), # Ghost note
]

# 2. Run Preprocessor Cleaning
preprocessor = Preprocessor()
cleaned_notes = preprocessor.process(raw_notes)

# 3. Execute Pipeline to ScoreIR & Export
# score_ir, report = run_pipeline(cleaned_notes)
# export(score_ir, "output_score.musicxml")
```

---

## Pipeline Architecture

```
 Raw Input (Audio / MIDI / JSON)
               │
               ▼
   ┌───────────────────────┐
   │ 1. Preprocessor       │ ──► Denoises, merges unisons (< 30ms), filters ghost notes
   └───────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ 2. Tempo Engine (PLL) │ ──► IOI + KDE peak finding for BPM; PLL for rubato mapping
   └───────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ 3. Quantizer          │ ──► Maps floating-point seconds into quantized beat grids
   └───────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ 4. Voice & Staffing   │ ──► Dynamic hand contour tracking & stem direction routing
   └───────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ 5. Exporter           │ ──► Generates formatted .musicxml file
   └───────────────────────┘
```

---

## License

Distributed under the MIT License.
