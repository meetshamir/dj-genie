"""
Audio Analysis Service - Detects high-energy segments in songs.

Uses librosa for:
- Energy (RMS) analysis
- BPM detection
- Spectral analysis
- Segment detection
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import librosa
except ImportError:
    librosa = None

from config import settings


@dataclass
class DetectedSegment:
    """Represents a detected high-energy segment."""
    start_time: float  # seconds
    end_time: float    # seconds
    duration: float    # seconds
    energy_score: float  # 0-100
    is_primary: bool   # highest energy segment
    label: str         # 'segment_1', 'chorus', etc.


@dataclass 
class AnalysisResult:
    """Complete analysis result for a song."""
    bpm: float
    overall_energy: float  # 0-100
    segments: List[DetectedSegment]
    energy_curve: Optional[np.ndarray] = None


def calculate_energy_curve(y: np.ndarray, sr: int, hop_length: int = 512) -> np.ndarray:
    """
    Compute composite energy score across time.
    Combines RMS (volume), spectral centroid (brightness), and onset strength (punch).
    
    Returns array of energy values (0-1) per audio frame.
    """
    # Volume envelope (how loud)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    
    # Spectral centroid (how bright/exciting) 
    spectral = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    
    # Onset strength (how punchy/rhythmic)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    
    # Normalize each to 0-1
    def normalize(arr):
        arr_min, arr_max = arr.min(), arr.max()
        if arr_max - arr_min < 1e-8:
            return np.zeros_like(arr)
        return (arr - arr_min) / (arr_max - arr_min)
    
    rms_norm = normalize(rms)
    spec_norm = normalize(spectral)
    onset_norm = normalize(onset)
    
    # Resample to same length (use shortest)
    length = min(len(rms_norm), len(spec_norm), len(onset_norm))
    
    # Weighted combination: RMS is most important for "energy"
    energy = (
        0.4 * rms_norm[:length] +
        0.3 * spec_norm[:length] +
        0.3 * onset_norm[:length]
    )
    
    # Smooth the curve to reduce noise
    if len(energy) > 10:
        kernel_size = min(21, len(energy) // 5)
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = np.ones(kernel_size) / kernel_size
        energy = np.convolve(energy, kernel, mode='same')
    
    return energy


def find_peak_segments(
    energy: np.ndarray,
    sr: int,
    hop_length: int = 512,
    min_duration: int = 45,
    max_duration: int = 90,
    max_segments: int = 3,
    min_gap: int = 30
) -> List[DetectedSegment]:
    """
    Find high-energy windows in the song.
    
    Args:
        energy: Energy curve array
        sr: Sample rate
        hop_length: Hop length used for analysis
        min_duration: Minimum segment duration in seconds
        max_duration: Maximum segment duration in seconds
        max_segments: Maximum number of segments to return
        min_gap: Minimum gap between segments in seconds
    
    Returns:
        List of DetectedSegment objects, sorted by start time
    """
    frames_per_second = sr / hop_length
    min_frames = int(min_duration * frames_per_second)
    max_frames = int(max_duration * frames_per_second)
    gap_frames = int(min_gap * frames_per_second)
    
    # Use a window size in the middle of min/max
    window_frames = int((min_frames + max_frames) / 2)
    step_frames = window_frames // 4  # 75% overlap for better coverage
    
    # Sliding window to find candidate regions
    candidates = []
    for start in range(0, len(energy) - min_frames, step_frames):
        # Try to extend the window up to max_frames while energy stays high
        best_end = start + min_frames
        best_energy = np.mean(energy[start:best_end])
        
        for end in range(start + min_frames, min(start + max_frames + 1, len(energy)), step_frames // 2):
            window_energy = np.mean(energy[start:end])
            if window_energy >= best_energy * 0.95:  # Allow slight decrease
                best_end = end
                best_energy = window_energy
        
        candidates.append({
            'start_frame': start,
            'end_frame': best_end,
            'energy': np.mean(energy[start:best_end])
        })
    
    # Sort by energy (highest first)
    candidates.sort(key=lambda x: x['energy'], reverse=True)
    
    # Select non-overlapping segments
    selected = []
    for candidate in candidates:
        if len(selected) >= max_segments:
            break
        
        # Check for overlap with already selected
        overlaps = False
        for seg in selected:
            # Check if segments are too close
            if not (candidate['end_frame'] + gap_frames < seg['start_frame'] or
                    candidate['start_frame'] - gap_frames > seg['end_frame']):
                overlaps = True
                break
        
        if not overlaps:
            selected.append(candidate)
    
    # Convert to DetectedSegment objects, sorted by start time
    segments = []
    selected_sorted = sorted(selected, key=lambda x: x['start_frame'])
    
    # Find the primary (highest energy) segment
    max_energy_idx = 0
    max_energy = 0
    for i, seg in enumerate(selected_sorted):
        if seg['energy'] > max_energy:
            max_energy = seg['energy']
            max_energy_idx = i
    
    for i, seg in enumerate(selected_sorted):
        start_time = seg['start_frame'] / frames_per_second
        end_time = seg['end_frame'] / frames_per_second
        
        segments.append(DetectedSegment(
            start_time=round(start_time, 2),
            end_time=round(end_time, 2),
            duration=round(end_time - start_time, 2),
            energy_score=round(seg['energy'] * 100, 1),
            is_primary=(i == max_energy_idx),
            label=f'segment_{i + 1}'
        ))
    
    return segments


def detect_bpm(y: np.ndarray, sr: int) -> float:
    """Detect the BPM (tempo) of the audio."""
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        # tempo might be an array in some versions
        if hasattr(tempo, '__len__'):
            return float(tempo[0]) if len(tempo) > 0 else 120.0
        return float(tempo)
    except Exception as e:
        print(f"BPM detection error: {e}")
        return 120.0  # Default BPM


def analyze_audio_file(
    audio_path: str,
    min_segment_duration: int = None,
    max_segment_duration: int = None,
    max_segments: int = None
) -> AnalysisResult:
    """
    Analyze an audio file to detect BPM, energy, and high-energy segments.
    
    Args:
        audio_path: Path to audio file (MP3, WAV, etc.)
        min_segment_duration: Minimum segment length (seconds)
        max_segment_duration: Maximum segment length (seconds)
        max_segments: Maximum number of segments to detect
    
    Returns:
        AnalysisResult with BPM, energy score, and detected segments
    """
    if librosa is None:
        raise ImportError("librosa is required for audio analysis")
    
    # Use settings defaults if not specified
    min_segment_duration = min_segment_duration or settings.min_segment_duration
    max_segment_duration = max_segment_duration or settings.max_segment_duration
    max_segments = max_segments or settings.max_segments_per_song
    
    print(f"  Loading audio: {audio_path}")
    
    # Load audio file
    # Use a lower sample rate for faster processing
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    
    print(f"  Detecting BPM...")
    bpm = detect_bpm(y, sr)
    
    print(f"  Calculating energy curve...")
    hop_length = 512
    energy_curve = calculate_energy_curve(y, sr, hop_length)
    
    overall_energy = float(np.mean(energy_curve) * 100)
    
    print(f"  Finding high-energy segments...")
    segments = find_peak_segments(
        energy_curve,
        sr,
        hop_length,
        min_duration=min_segment_duration,
        max_duration=max_segment_duration,
        max_segments=max_segments,
        min_gap=settings.min_segment_gap
    )
    
    print(f"  Found {len(segments)} segments, BPM: {bpm:.1f}")
    
    return AnalysisResult(
        bpm=round(bpm, 1),
        overall_energy=round(overall_energy, 1),
        segments=segments,
        energy_curve=energy_curve
    )


# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analysis.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    if not os.path.exists(audio_file):
        print(f"File not found: {audio_file}")
        sys.exit(1)
    
    print(f"Analyzing: {audio_file}")
    result = analyze_audio_file(audio_file)
    
    print(f"\nResults:")
    print(f"  BPM: {result.bpm}")
    print(f"  Overall Energy: {result.overall_energy}")
    print(f"  Segments: {len(result.segments)}")
    
    for seg in result.segments:
        print(f"    {seg.label}: {seg.start_time:.1f}s - {seg.end_time:.1f}s "
              f"({seg.duration:.1f}s) - Energy: {seg.energy_score:.1f}%"
              f"{' [PRIMARY]' if seg.is_primary else ''}")
