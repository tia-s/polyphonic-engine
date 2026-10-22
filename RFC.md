# Polyphonic Scorer
**Date:** October 12, 2026

**Status:** Draft  

## 1. Context & Scope
*   **Background:** Machine learning models like Spotify's `basic-pitch` output raw note events (pitch, start, end) from audio. Standard notation software (like MuseScore) and traditional DAWs rely on musical events being perfectly aligned to a quantized grid. When raw ML output containing human micro-timing is imported directly, the software interprets those timings literally. This results in heavily fragmented sheet music cluttered with excessive 64th notes, micro-rests, and complex ties. To make these usable for musicians, we need to convert floating-point seconds into musical beats, track rubato (tempo fluctuations), clean up messy overlaps (pedal blur, ringing strings), and distribute the notes across the appropriate staves and clefs for the target instrument.

*   **Goals:**
    *   Provide a pipeline to clean, quantize, and voice raw note events.
    *   Support dynamic tempo tracking via a Phase-Locked Loop (PLL) to handle rubato.
    *   Output standard, readable MusicXML.
*   **Non-Goals:**
    *   Pitch detection from raw audio (delegated to `basic-pitch`).
    *   Rendering sheet music to PDF (delegated to standard notation software like MuseScore).
*   **Prior Art & Glossary:**
    *   `basic-pitch`: ML model for audio-to-MIDI.
    *   `music21`: Python library for computer-aided musicology.
    *   **IR:** Intermediate Representation (specifically `ScoreIR` in this codebase).

## 2. Requirements
*   **Functional:** The script must take an audio file, a MIDI file, or a JSON list of note events, run a 5-stage cleaning and quantization pipeline, and output a valid `.musicxml` file.
*   **Latency & Throughput:** Must process a typical 3-5 minute song in a few seconds on a standard laptop CPU.

## 3. Capacity & Scale Expectations
*   **Traffic/Users:** N/A 
*   **Read/Write Ratio:** N/A
*   **Data Volume:** N/A 
*   **Bandwidth:** N/A

## 4. Proposed Architecture
*   **High-Level Design:** 
    1.  **Input Adapter:** Reads JSON, MIDI, or runs `basic-pitch` on audio.
    2.  **Stage 1 (Clean):** De-noise, merge unisons, cap legato overlaps, and clean up pedal blur.
    3.  **Stage 2 (Tempo):** Estimate IOI (Inter-Onset Intervals) via log-domain KDE, build a PLL tempo map, detect time signature and downbeats.
    4.  **Stage 3 (Quantize):** Map seconds to beats, snap to grid (e.g., 16th notes).
    5.  **Stage 4 (Staves & Voices):** Split pitches into treble/bass (static threshold or contour-based), group into chords, assign to polyphonic voices, calculate rests.
    6.  **Stage 5 (Export):** Assemble `ScoreIR` and write out via custom XML builder or `music21`.
*   **Architecture Diagram:** N/A
*   **Core Components:**
    *   `Config`: Dataclass holding all heuristics and thresholds.
    *   `TempoMap`: Monotone piecewise-linear map translating seconds to beats.
    *   `assign_staves` & `build_voices`: Greedy interval coloring algorithms for notation layout.

## 5. System Interface
*   **HTTP/REST/gRPC Endpoints:** N/A
*   **Event/Message Schemas:** N/A
*   **Internal Methods/SDKs:**
    *   `run_pipeline(notes: list[Note], cfg: Config) -> tuple[ScoreIR, Report]`
    *   `export(ir: ScoreIR, path: str, backend: str) -> str`
*   **CLI Interface:** 
    *   `input`: Filepath (.wav, .mp3, .mid, .json).
    *   Flags: `--bpm`, `--grid`, `--split`, `--staff-mode`, `--max-voices`, `--key-sharps`, `--detect-pickup`.
*   **Versioning & Compatibility:** N/A

## 6. Data Design
*   **Storage Choices:** N/A (In-memory execution only).
*   **Schema:** 
    *   `Note`: Raw unquantized event (start, end, pitch, velocity).
    *   `QNote`: Quantized event (start/end in quarter-lengths).
    *   `Ev`: Chord/note event within one staff.
    *   `Piece`: Measure-bound, notatable slice of music (handles ties across barlines).
    *   `ScoreIR`: The structured intermediate representation containing measures, staves, and voices.
*   **Indexes & Access Patterns:** N/A
*   **Data Lifecycle:** Ephemeral; memory is freed when the script terminates.

## 7. Scaling Strategy
*   **Caching:** N/A
*   **Partitioning/Sharding:** N/A
*   **Replication & Load Balancing:** N/A
*   **Async Work:** N/A
*   **Bottlenecks:** Running the `basic-pitch` ML model (if passed an audio file) is the primary compute bottleneck, but this is expected for local ML inference.

## 8. Consistency & Concurrency
*   **Conflict Handling:** N/A (Single-threaded).
*   **Idempotency:** Re-running the script with the same input and seed/config guarantees the exact same MusicXML output.
*   **Ordering & Delivery Guarantees:** N/A
*   **Transactions:** N/A

## 9. Alternatives Considered
*   **Alternative 1: Using `music21` for all quantization and voice separation.**
    *   *Rejected because:* `music21` is designed for analyzing structured, symbolic music rather than processing raw ML audio outputs. Relying on it directly introduces three main limitations for this pipeline:
        *   **Tempo tracking:** It offers basic grid quantization but assumes a steady tempo, lacking the Phase-Locked Loop (PLL) algorithms required to track natural human rubato.
        *   **Acoustic cleanup:** It operates under the assumption that note start and end times are intentional musical choices. It provides no built-in heuristics to filter out acoustic artifacts, like ringing strings or sustain pedal blur, prior to quantization.
        *   **Staff distribution:** It lacks native support for algorithmic staff splitting, such as dividing a single note stream across appropriate staves based on hand contour.
    *   Implementing a custom Intermediate Representation (IR) directly addresses these specific edge cases while keeping the core logic lightweight and dependency-free.
*   **Alternative 2: Outputting MIDI instead of MusicXML.**
    *   *Rejected because:* MIDI lacks formatting concepts like staves, left/right hand splits, key signatures, and specific enharmonic spelling (C# vs Db). MusicXML is required for readable sheet music.

## 10. Dependencies & Integrations
*   **Libraries:**
    *   `numpy` / `scipy`: Required for core math (KDE, peak finding, PLL).
    *   `basic-pitch`: Optional (required only if passing raw audio).
    *   `pretty_midi`: Optional (required only if passing `.mid` files).
    *   `music21`: Optional (fallback backend for MusicXML generation).

## 11. Operational Considerations
*   **Security & Privacy:** Local execution only; no audio or data is sent to the cloud.
*   **Observability:** The script prints a `Report` to `stdout` detailing dropped short notes, truncated legato overlaps, estimated BPM, and key signature.
*   **Failure Scenarios:** Bad audio resulting in no notes transcribed will throw a `ValueError("no notes left after cleanup")`.
*   **Graceful Degradation:** If `music21` is not installed, the `export()` function gracefully falls back to the custom `write_musicxml_basic()` dependency-free XML writer.
*   **Cost:** Free (local compute).

## 12. Rollout, Migration & Rollback
*   **Deployment Strategy:** Distributed via Git repository.
*   **Rollback Plan:** Revert to a previous Git commit if a bug is introduced.

## 13. Testing Strategy
*   **Unit & Integration Tests:** 
    *   Stages 1-4 can be unit tested purely with JSON input (using the `--dump-notes` feature to cache ML output) to ensure `numpy` math, quantization logic, and tie-splitting (`split_notatable`) work without requiring audio processing or `basic-pitch` setup.
*   **Load & Stress Testing:** N/A
*   **Failure Testing:** N/A

## 14. Risks & Open Questions
-   **Risks:** 
    *   **Anacrusis detection:** The pickup measure detection is highly experimental and will likely fail on heavily syncopated tracks. 
    *   **Physical playability:** The `contour` staff-splitting algorithm evaluates pitch proximity rather than instrument mechanics. Applying this to guitar or ukulele might produce physically unplayable chord voicings or ignore string-spanning constraints.
    *   **Clef and register bias:** Current heuristics (like splitting at MIDI 60 / Middle C) are biased toward piano. For instruments like a guitar, which is a transposing instrument written an octave higher than it sounds, this logic will generate incorrect or heavily ledger-lined sheet music.
-   **Open Questions:** 
    *   **Compound meters:** Should the pipeline support ternary meters (e.g., 6/8, 12/8)? 
    *   **Instrument routing:** How should the pipeline determine the target instrument's notation rules? Does this require explicit CLI flags (e.g., `--instrument=guitar`), or can it be inferred?
    *   **Tablature support:** Since standard MusicXML supports tablature, should the output generation be expanded to calculate string and fret assignments for guitar and ukulele?
-   **Assumptions:** 
    *   **Single-instrument audio:** The pipeline assumes the input audio contains a single polyphonic instrument. Feeding it mixed ensemble audio (e.g., a full band) will collapse all instruments into a single, chaotic note stream.
    *   **ML transcription accuracy:** The pipeline assumes the upstream ML model (`basic-pitch`) outputs reasonably accurate pitch and onset data. It does not attempt to correct fundamental pitch-detection errors made by the model.

## 15. Timeline & Phases
*   **Phases:** 
    *   *Phase 1:* Core pipeline logic (Stages 1-4) and JSON/MIDI adapters.
    *   *Phase 2:* Custom, dependency-free MusicXML writer (`write_musicxml_basic`).
    *   *Phase 3:* Integration with `basic-pitch` for end-to-end audio transcription.
