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
* `basic-pitch` — Required for transcribing raw `.wav` or `.mp3` audio files.
* `music21` — Optional advanced MusicXML export engine.

---

## Quickstart

Note: Requires **Python 3.10** or **3.11** (64-bit).

```bash
# Process audio directly to MusicXML
python scorer.py -i input_audio.wav --o score.musicxml
```

<img src="assets/terminal-demo.gif" width="960" height="540" alt="terminal-demo" />


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
