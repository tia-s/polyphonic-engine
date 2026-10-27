import pytest
from scorer import Note, Preprocessor


@pytest.fixture
def preprocessor():
    return Preprocessor()


def test_sanitize_notes(preprocessor):
    raw = [
        None,
        # Clamps negative start to 0.0, rounds floating MIDI pitch, clamps velocity to 1.0 max
        Note(start=-0.5, end=0.5, pitch=60.4, velocity=1.5),
        # Out-of-bounds MIDI pitch (< 0) -> discarded
        Note(start=0.0, end=0.5, pitch=-1, velocity=0.8),
        # Out-of-bounds MIDI pitch (> 127) -> discarded
        Note(start=0.0, end=0.5, pitch=128, velocity=0.8),
        # Inverted duration (end <= start) -> discarded
        Note(start=0.5, end=0.2, pitch=60, velocity=0.8),
        # Zero velocity event -> discarded
        Note(start=0.0, end=0.5, pitch=60, velocity=0.0),
    ]
    sanitized = preprocessor.sanitize_notes(raw)
    assert len(sanitized) == 1
    assert sanitized[0].start == 0.0
    assert sanitized[0].pitch == 60
    assert sanitized[0].velocity == 1.0


def test_merge_unisons(preprocessor):
    raw = [
        # Rapid double-trigger of G4 (< 30ms gap) -> merged into a single continuous event
        Note(start=0.50, end=0.72, pitch=67, velocity=0.7),
        Note(start=0.73, end=1.00, pitch=67, velocity=0.6),
        # Distinct articulation on G4 (> 30ms gap) -> preserved as an independent note
        Note(start=1.10, end=1.50, pitch=67, velocity=0.8),
    ]
    merged = preprocessor.merge_unisons(raw)
    assert len(merged) == 2
    assert merged[0].start == 0.50
    assert merged[0].end == 1.00
    assert merged[0].velocity == 0.7
    assert merged[1].start == 1.10


def test_filter_noise_and_ghosts(preprocessor):
    notes = [
        # Standard note event -> preserved
        Note(start=0.0, end=0.50, pitch=60, velocity=0.8),
        # Acoustic noise artifact (< 80ms duration AND < 0.15 velocity) -> filtered out
        Note(start=1.2, end=1.25, pitch=61, velocity=0.08),
        # Soft sustained note -> preserved due to long duration
        Note(start=1.5, end=2.50, pitch=48, velocity=0.10),
        # Fast staccato note -> preserved due to high velocity
        Note(start=2.6, end=2.65, pitch=72, velocity=0.85),
    ]
    cleaned = preprocessor.filter_noise_and_ghosts(notes)
    assert len(cleaned) == 3
    assert [n.pitch for n in cleaned] == [60, 48, 72]


def test_pipeline_sample_data_sanity_check(preprocessor):
    """End-to-end evaluation of synthetic note data passing through all cleaning stages."""
    sample_data = [
        Note(start=0.0, end=0.50, pitch=60, velocity=0.8),
        Note(start=0.5, end=0.72, pitch=67, velocity=0.7),
        Note(start=0.73, end=1.00, pitch=67, velocity=0.6),
        Note(start=1.2, end=1.25, pitch=61, velocity=0.08),
        Note(start=1.5, end=2.50, pitch=48, velocity=0.10),
        Note(start=2.6, end=2.65, pitch=72, velocity=0.85),
    ]

    sanitized = preprocessor.sanitize_notes(sample_data)
    merged = preprocessor.merge_unisons(sanitized)
    cleaned = preprocessor.filter_noise_and_ghosts(merged)

    assert len(sample_data) == 6
    assert len(cleaned) == 4
    assert [n.pitch for n in cleaned] == [60, 67, 48, 72]