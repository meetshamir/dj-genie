"""
Intelligent Mixing Service - Optimizes playlist ordering for smooth transitions and variety.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import random


@dataclass
class MixableSegment:
    """A segment with metadata for mixing."""
    id: str
    song_id: str
    song_title: str
    language: str
    bpm: Optional[float]
    energy_score: float
    start_time: float
    end_time: float
    duration: float
    
    
@dataclass
class MixResult:
    """Result of an intelligent mix operation."""
    segments: List[MixableSegment]
    transitions: List[Dict]  # Info about each transition
    quality_score: float  # 0-100 rating of mix quality
    notes: List[str]  # Any warnings or notes


def calculate_bpm_distance(bpm1: Optional[float], bpm2: Optional[float]) -> float:
    """
    Calculate the BPM distance between two tracks.
    Returns 0 if BPMs are identical, higher values for larger differences.
    Accounts for harmonic relationships (half/double time).
    """
    if bpm1 is None or bpm2 is None:
        return 10.0  # Default penalty for unknown BPM
    
    direct_diff = abs(bpm1 - bpm2)
    
    # Check for half/double time matches (e.g., 80 BPM and 160 BPM)
    half_diff = abs(bpm1 - bpm2 / 2) if bpm2 > bpm1 else abs(bpm2 - bpm1 / 2)
    double_diff = abs(bpm1 * 2 - bpm2) if bpm1 < bpm2 else abs(bpm2 * 2 - bpm1)
    
    # Return the smallest difference
    return min(direct_diff, half_diff * 1.5, double_diff * 1.5)


def calculate_energy_transition(energy1: float, energy2: float) -> float:
    """
    Calculate how smooth an energy transition is.
    Smaller changes are smoother. Returns 0-1 where 0 is identical.
    """
    return abs(energy1 - energy2)


def optimize_bpm_order(segments: List[MixableSegment]) -> List[MixableSegment]:
    """
    Reorder segments to minimize BPM jumps.
    Uses nearest-neighbor algorithm.
    """
    if len(segments) <= 2:
        return segments
    
    # Start with a middle-energy segment
    segments_copy = segments.copy()
    energies = [s.energy_score for s in segments_copy]
    avg_energy = sum(energies) / len(energies)
    
    # Find segment closest to average energy
    closest_idx = min(range(len(segments_copy)), 
                      key=lambda i: abs(segments_copy[i].energy_score - avg_energy))
    
    ordered = [segments_copy.pop(closest_idx)]
    
    # Greedily add nearest BPM neighbor
    while segments_copy:
        last = ordered[-1]
        
        # Find segment with minimum BPM distance
        best_idx = min(range(len(segments_copy)),
                      key=lambda i: calculate_bpm_distance(last.bpm, segments_copy[i].bpm))
        
        ordered.append(segments_copy.pop(best_idx))
    
    return ordered


def ensure_language_variety(segments: List[MixableSegment], max_consecutive: int = 2) -> List[MixableSegment]:
    """
    Reorder to ensure no more than max_consecutive segments of the same language.
    Tries to maintain BPM order while ensuring variety.
    """
    if len(segments) <= max_consecutive:
        return segments
    
    result = []
    remaining = segments.copy()
    last_languages = []
    
    while remaining:
        # Find valid candidates (not violating language constraint)
        valid = []
        for i, seg in enumerate(remaining):
            # Count how many of this language are at the end
            lang_count = sum(1 for lang in last_languages[-max_consecutive+1:] if lang == seg.language)
            if lang_count < max_consecutive - 1:
                valid.append(i)
        
        if not valid:
            # No valid candidates, just take the first one with different language if possible
            for i, seg in enumerate(remaining):
                if not last_languages or seg.language != last_languages[-1]:
                    valid.append(i)
                    break
            if not valid:
                valid = [0]  # Fallback to first
        
        # Among valid candidates, prefer the one with closest BPM to last segment
        if result:
            last_bpm = result[-1].bpm
            best_idx = min(valid, key=lambda i: calculate_bpm_distance(last_bpm, remaining[i].bpm))
        else:
            best_idx = valid[0]
        
        seg = remaining.pop(best_idx)
        result.append(seg)
        last_languages.append(seg.language)
    
    return result


def build_energy_curve(segments: List[MixableSegment], curve_type: str = "peak_middle") -> List[MixableSegment]:
    """
    Reorder segments to follow an energy curve.
    
    Curve types:
    - "peak_middle": Start medium, peak in middle, wind down (party flow)
    - "ascending": Build up throughout
    - "descending": Start hot, cool down
    - "wave": Multiple peaks
    """
    if len(segments) <= 3:
        return segments
    
    # Sort by energy
    sorted_by_energy = sorted(segments, key=lambda s: s.energy_score)
    
    if curve_type == "peak_middle":
        # Split into low, mid, high energy groups
        n = len(sorted_by_energy)
        third = n // 3
        
        low = sorted_by_energy[:third]
        mid = sorted_by_energy[third:2*third]
        high = sorted_by_energy[2*third:]
        
        # Shuffle within groups for variety
        random.shuffle(low)
        random.shuffle(mid)
        random.shuffle(high)
        
        # Build: mid -> high -> mid+low
        result = []
        
        # Opening: medium energy
        if mid:
            result.append(mid.pop(0))
        
        # Build up: remaining mid + high
        buildup = mid + high
        random.shuffle(buildup)
        result.extend(buildup)
        
        # Cool down: low energy
        result.extend(low)
        
        return result
    
    elif curve_type == "ascending":
        return sorted_by_energy
    
    elif curve_type == "descending":
        return list(reversed(sorted_by_energy))
    
    elif curve_type == "wave":
        # Create peaks every N segments
        n = len(sorted_by_energy)
        wave_length = max(3, n // 3)
        
        result = []
        low_high = list(zip(sorted_by_energy[:n//2], reversed(sorted_by_energy[n//2:])))
        for low, high in low_high:
            result.extend([low, high])
        
        # Add any remaining
        if len(sorted_by_energy) % 2:
            result.append(sorted_by_energy[n//2])
        
        return result
    
    return segments


def intelligent_mix(
    segments: List[MixableSegment],
    strategy: str = "balanced",
    energy_curve: str = "peak_middle",
    max_same_language: int = 2
) -> MixResult:
    """
    Apply intelligent mixing to optimize playlist order.
    
    Strategies:
    - "bpm_smooth": Prioritize smooth BPM transitions
    - "language_variety": Prioritize language variety
    - "energy_curve": Follow an energy curve pattern
    - "balanced": Balance all factors (default)
    
    Returns optimized segment order with transition info.
    """
    if len(segments) == 0:
        return MixResult(segments=[], transitions=[], quality_score=0, notes=["Empty playlist"])
    
    if len(segments) == 1:
        return MixResult(segments=segments, transitions=[], quality_score=100, notes=["Single segment"])
    
    notes = []
    
    # Apply mixing strategy
    if strategy == "bpm_smooth":
        mixed = optimize_bpm_order(segments)
        notes.append("Optimized for BPM transitions")
        
    elif strategy == "language_variety":
        mixed = ensure_language_variety(segments, max_same_language)
        notes.append(f"Ensured max {max_same_language} consecutive same-language segments")
        
    elif strategy == "energy_curve":
        mixed = build_energy_curve(segments, energy_curve)
        notes.append(f"Applied {energy_curve} energy curve")
        
    elif strategy == "balanced":
        # Apply all strategies in order
        # 1. First apply energy curve
        mixed = build_energy_curve(segments, energy_curve)
        
        # 2. Then ensure language variety
        mixed = ensure_language_variety(mixed, max_same_language)
        
        notes.append(f"Balanced mix: {energy_curve} curve, language variety")
    else:
        mixed = segments
        notes.append("No optimization applied")
    
    # Calculate transition info
    transitions = []
    for i in range(len(mixed) - 1):
        curr = mixed[i]
        next_seg = mixed[i + 1]
        
        bpm_diff = calculate_bpm_distance(curr.bpm, next_seg.bpm)
        energy_diff = calculate_energy_transition(curr.energy_score, next_seg.energy_score)
        same_language = curr.language == next_seg.language
        
        # Rate transition smoothness
        smoothness = 100 - (bpm_diff * 2) - (energy_diff * 50)
        smoothness = max(0, min(100, smoothness))
        
        transitions.append({
            "from_segment": curr.id,
            "to_segment": next_seg.id,
            "bpm_diff": round(bpm_diff, 1),
            "energy_diff": round(energy_diff, 2),
            "same_language": same_language,
            "smoothness_score": round(smoothness, 1)
        })
    
    # Calculate overall quality score
    if transitions:
        avg_smoothness = sum(t["smoothness_score"] for t in transitions) / len(transitions)
        
        # Penalize consecutive same-language
        language_penalty = 0
        for i in range(len(mixed) - max_same_language):
            if all(mixed[i+j].language == mixed[i].language for j in range(max_same_language + 1)):
                language_penalty += 5
        
        quality_score = max(0, avg_smoothness - language_penalty)
    else:
        quality_score = 100
    
    return MixResult(
        segments=mixed,
        transitions=transitions,
        quality_score=round(quality_score, 1),
        notes=notes
    )


def suggest_next_segment(
    current: MixableSegment,
    candidates: List[MixableSegment],
    recent_languages: List[str] = None
) -> List[Tuple[MixableSegment, float]]:
    """
    Suggest the best next segments given the current one.
    Returns list of (segment, score) tuples, sorted by score descending.
    """
    if not candidates:
        return []
    
    recent_languages = recent_languages or []
    
    scored = []
    for seg in candidates:
        # Start with base score
        score = 50.0
        
        # BPM similarity bonus (up to +30)
        bpm_diff = calculate_bpm_distance(current.bpm, seg.bpm)
        bpm_score = max(0, 30 - bpm_diff)
        score += bpm_score
        
        # Energy similarity bonus (up to +20)
        energy_diff = calculate_energy_transition(current.energy_score, seg.energy_score)
        energy_score = max(0, 20 - energy_diff * 40)
        score += energy_score
        
        # Language variety bonus
        if seg.language != current.language:
            score += 10
        if seg.language not in recent_languages:
            score += 5
        
        scored.append((seg, score))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    
    return scored
