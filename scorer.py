import argparse
import sys

from basic_pitch.inference import predict
from dataclasses import dataclass
from music21 import stream, note as m21_note
from typing import List

@dataclass
class Note:
    """Represents a single musical note event from Basic Pitch output."""
    start: float      # Start time in seconds
    end: float        # End time in seconds
    pitch: int        # MIDI pitch (0-127)
    velocity: float   # Velocity/amplitude (0.0 to 1.0)

    @property
    def duration(self) -> float:
        return self.end - self.start

class Preprocessor:
    """Pre-processing pipeline for Basic Pitch output to clean up noise."""
    def __init__(
        self,
        unison_gap_threshold: float = 0.030,  
        min_duration: float = 0.080,          
        min_velocity: float = 0.15   
    ):
        self.unison_gap_threshold = unison_gap_threshold
        self.min_duration = min_duration
        self.min_velocity = min_velocity

    def predict_audio_to_notes(self, audio_path: str) -> List[Note]:
        """Runs Spotify's Basic Pitch on an audio file and converts output to Note objects."""
        # Predict returns: (model_output, midi_data, note_events)
        _, _, note_events = predict(audio_path)
        print(f"Predicting midi for {audio_path}...")

        return [
            Note(
                start=float(start),
                end=float(end),
                pitch=int(round(pitch)),
                velocity=float(amplitude),
            )
            for start, end, pitch, amplitude, _ in note_events
        ]

    def sanitize_notes(self, notes: List[Note]) -> List[Note]:
        """
        Validates and sanitizes raw note events before processing.
        
        Checks for:
        - None / empty input
        - Out-of-bounds MIDI pitches (0-127) and float/NaN pitches
        - Inverted or zero-length durations (end <= start)
        - Negative timestamps
        - Output velocity is strictly 0.0 to 1.0 float
        """

        if not notes:
            return []

        sanitized = []
        
        for note in notes:
            if note is None:
                continue

            try:
                pitch = int(round(note.pitch))
            except (ValueError, TypeError):
                continue 
                
            if not (0 <= pitch <= 127):
                continue 

            start = max(0.0, float(note.start))
            end = float(note.end)
            
            if end <= start:
                continue 

            vel = float(note.velocity)

            vel = max(0.0, min(1.0, vel))  

            if vel == 0.0:
                continue

            sanitized.append(Note(start=start, end=end, pitch=pitch, velocity=vel))

        return sanitized

    def merge_unisons(self, notes: List[Note]) -> List[Note]:
        """
        Merges same-pitch notes that trigger in rapid succession (< 30ms gap).
        This helps to correct for split notes caused by Basic Pitch's sensitivity.
        """

        sorted_notes = sorted(notes, key=lambda n: (n.pitch, n.start))
    
        merged_notes = [
            Note(
                start=sorted_notes[0].start,
                end=sorted_notes[0].end,
                pitch=sorted_notes[0].pitch,
                velocity=sorted_notes[0].velocity
            )
        ]

        for next_note in sorted_notes[1:]:
            last_note = merged_notes[-1]

            if (next_note.pitch == last_note.pitch and 
                (next_note.start - last_note.end) < self.unison_gap_threshold):
                
                last_note.end = max(last_note.end, next_note.end)
                last_note.velocity = max(last_note.velocity, next_note.velocity)
            else:
                merged_notes.append(
                    Note(
                        start=next_note.start,
                        end=next_note.end,
                        pitch=next_note.pitch,
                        velocity=next_note.velocity
                    )
                )

        return sorted(merged_notes, key=lambda n: (n.start, n.pitch))

    def filter_noise_and_ghosts(self, notes: List[Note]) -> List[Note]:
        """
        Filters out accidental grazes, acoustic string buzz, and overtone glitches
        that are BOTH low velocity AND short duration.
        """

        # Preserves soft long sustained notes and fast loud staccatos by evaluating both duration AND velocity.
        cleaned = [note for note in notes if not (note.duration < self.min_duration and note.velocity < self.min_velocity)]
            
        return cleaned

    def export_to_musicxml(self, notes: List[Note], output_path: str):
        score = stream.Score()
        part = stream.Part()
        
        BPM = 120
        QUARTER_NOTES_PER_SECOND = BPM / 60.0
        GRID_STEP = 0.25

        for n in notes:
            m_note = m21_note.Note(n.pitch)
            
            raw_offset = n.start * QUARTER_NOTES_PER_SECOND
            raw_duration = n.duration * QUARTER_NOTES_PER_SECOND
            
            offset = round(raw_offset / GRID_STEP) * GRID_STEP
            duration = max(GRID_STEP, round(raw_duration / GRID_STEP) * GRID_STEP)
            
            m_note.quarterLength = duration
            part.insert(offset, m_note)
            
        score.append(part.makeMeasures())
        score.write("musicxml", fp=output_path)
        print(f"Sheet music exported to {output_path}")

    def process(self, audio_path: List[Note], output_path: str="output.musicxml") -> List[Note]:
        """Runs the complete pre-processing pipeline."""

        raw_notes = self.predict_audio_to_notes(audio_path)
        sanitized = self.sanitize_notes(raw_notes)
        merged = self.merge_unisons(sanitized)
        cleaned = self.filter_noise_and_ghosts(merged)
        self.export_to_musicxml(cleaned, output_path=output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polyphonic Scorer CLI")
    
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Path to input audio file (.wav, .mp3)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output.musicxml",
        help="Path for the exported MusicXML file (default: output.musicxml)"
    )

    args = parser.parse_args()

    preprocessor = Preprocessor()
    result = preprocessor.process(audio_path=args.input, output_path=args.output)