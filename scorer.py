from dataclasses import dataclass
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

    def merge_unisons(self, notes: List[Note]) -> List[Note]:
        """
        Merges same-pitch notes that trigger in rapid succession (< 30ms gap).
        This helps to correct for split notes caused by Basic Pitch's sensitivity.
        """

        if not notes:
            return []

        by_pitch = {}
        for note in sorted(notes, key=lambda n: (n.pitch, n.start)):
            by_pitch.setdefault(note.pitch, []).append(note)

        merged_notes = []
        for _, pitch_notes in by_pitch.items():
            current_group = pitch_notes[0]
            
            for next_note in pitch_notes[1:]:
                gap = next_note.start - current_group.end
                if gap < self.unison_gap_threshold:
                    current_group.end = max(current_group.end, next_note.end)
                    # Retain the highest velocity in the merged group to ensure the note's prominence is preserved
                    current_group.velocity = max(current_group.velocity, next_note.velocity)
                else:
                    merged_notes.append(current_group)
                    current_group = next_note
                    
            merged_notes.append(current_group)

        return sorted(merged_notes, key=lambda n: (n.start, n.pitch))

    def filter_noise_and_ghosts(self, notes: List[Note]) -> List[Note]:
        """
        Filters out accidental grazes, acoustic string buzz, and overtone glitches
        that are BOTH low velocity AND short duration.
        """

        cleaned = []
        for note in notes:   
            # Preserves soft long sustained notes and fast loud staccatos
            if note.duration < self.min_duration and note.velocity < self.min_velocity:
                continue
                
            cleaned.append(note)
            
        return cleaned

    def process(self, raw_notes: List[Note]) -> List[Note]:
        """Runs the complete pre-processing pipeline."""
        # Step 1: Fix split notes first so fragments aren't accidentally deleted
        merged = self.merge_unisons(raw_notes)
        
        # Step 2: Clean up acoustic noise and ghost notes
        cleaned = self.filter_noise_and_ghosts(merged)
        
        return cleaned



if __name__ == "__main__":
    # Sample raw note events from Basic Pitch output
    sample_data = [
        # 1. Normal note (Middle C)
        Note(start=0.0, end=0.50, pitch=60, velocity=0.8),
        
        # 2. Glitch: Rapid double-trigger of G4 (should be merged into one ~0.5s note)
        Note(start=0.5, end=0.72, pitch=67, velocity=0.7),
        Note(start=0.73, end=1.00, pitch=67, velocity=0.6), # 10ms gap (< 30ms)
        
        # 3. Acoustic Ghost Note / Fret Buzz (should be dropped: < 80ms AND < 0.15 vel)
        Note(start=1.2, end=1.25, pitch=61, velocity=0.08),
        
        # 4. Soft sustained note (should be KEPT: soft, but long duration)
        Note(start=1.5, end=2.50, pitch=48, velocity=0.10),
        
        # 5. Fast loud staccato (should be KEPT: short, but loud velocity)
        Note(start=2.6, end=2.65, pitch=72, velocity=0.85),
    ]

    preprocessor = Preprocessor()
    result = preprocessor.process(sample_data)

    print(f"Raw Input Notes Count: {len(sample_data)}")
    print(f"Cleaned Notes Count:   {len(result)}\n")
    print("Cleaned Notes Output:")
    for n in result:
        print(f"  Pitch: {n.pitch} | Start: {n.start:.2f}s | End: {n.end:.2f}s | Dur: {n.duration:.2f}s | Vel: {n.velocity:.2f}")