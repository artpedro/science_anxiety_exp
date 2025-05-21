
import os
import random
import wave
from pathlib import Path
from typing import List, Dict
from collections import Counter


def get_wav_duration(file_path: str) -> float:
    """Return duration of a WAV file in seconds."""
    with wave.open(file_path, 'rb') as wf:
        return wf.getnframes() / float(wf.getframerate())


def load_science_questions(base_dir: str = "data/science_questions"):
    """
    Walks:
      data/science_questions/
        control/{false,true}/
        high_complexity/{biology,chemistry,physics}/{false,true}/
        low_complexity/{biology,chemistry,physics}/{false,true}/
    Returns:
      control_qs: List[Dict]
      high_qs: Dict[str, List[Dict]]
      low_qs:  Dict[str, List[Dict]]

    Each question dict has: path, answer (0/1), duration.
    """
    base = Path(base_dir)
    control_qs = []
    high_qs = {subj: [] for subj in ("biology", "chemistry", "physics")}
    low_qs  = {subj: [] for subj in ("biology", "chemistry", "physics")}

    # Control questions
    for ans in ("false", "true"):
        folder = base / "control" / ans
        for wav in folder.glob("*.wav"):
            control_qs.append({
                "path": str(wav),
                "answer": 1 if ans == "true" else 0,
                "duration": get_wav_duration(str(wav))
            })
    random.shuffle(control_qs)

    # High and low complexity
    for complexity, pool in (("high_complexity", high_qs), ("low_complexity", low_qs)):
        for subj in ("biology", "chemistry", "physics"):
            for ans in ("false", "true"):
                folder = base / complexity / subj / ans
                for wav in folder.glob("*.wav"):
                    pool[subj].append({
                        "path": str(wav),
                        "answer": 1 if ans == "true" else 0,
                        "duration": get_wav_duration(str(wav))
                    })
            random.shuffle(pool[subj])

    return control_qs, high_qs, low_qs


def generate_control_block(control_qs: List[Dict], min_duration: float = 360.0) -> List[Dict]:
    """
    Return shuffled control questions until total duration >= min_duration.
    Wraps around if list is exhausted.
    """
    seq = []
    total = 0.0
    idx = 0
    pool = control_qs.copy()
    random.shuffle(pool)
    while total < min_duration:
        q = pool[idx % len(pool)]
        seq.append(q)
        total += q['duration']
        idx += 1
    return seq


def generate_complexity_block(
    pool: Dict[str, List[Dict]],
    min_duration: float = 360.0
) -> List[Dict]:
    """
    pool: {'biology': [...], 'chemistry': [...], 'physics': [...]}
    Round-robin biology→chemistry→physics until >= min_duration,
    then append extra to equalize counts.
    """
    subjects = ['biology', 'chemistry', 'physics']
    pools = {subj: pool[subj].copy() for subj in subjects}
    for subj in subjects:
        random.shuffle(pools[subj])

    seq = []
    total = 0.0
    idx = {subj: 0 for subj in subjects}
    counts = Counter()

    # 1) Round-robin fill
    while total < min_duration:
        for subj in subjects:
            qlist = pools[subj]
            q = qlist[idx[subj] % len(qlist)]
            idx[subj] += 1
            seq.append(q)
            total += q['duration']
            counts[subj] += 1
            if total >= min_duration:
                break

    # 2) Balance counts
    max_count = max(counts.values())
    for subj in subjects:
        while counts[subj] < max_count:
            qlist = pools[subj]
            q = qlist[idx[subj] % len(qlist)]
            idx[subj] += 1
            seq.append(q)
            counts[subj] += 1

    return seq


def prepare_all_blocks(
    control_qs: List[Dict],
    high_qs: Dict[str, List[Dict]],
    low_qs: Dict[str, List[Dict]],
    min_duration: float = 360.0
) -> List[Dict]:
    """
    Returns 4 blocks in one of two sequences:
      1) High → Control → Low → Control
      2) Low  → Control → High → Control
    Each block: {'type': str, 'questions': List[Dict]}
    """
    configs = [
        ['high_complexity','control','low_complexity','control'],
        ['low_complexity','control','high_complexity','control'],
    ]
    sequence = random.choice(configs)

    blocks = []
    for btype in sequence:
        if btype == 'control':
            qs = generate_control_block(control_qs, min_duration)
        elif btype == 'high_complexity':
            qs = generate_complexity_block(high_qs, min_duration)
        else:
            qs = generate_complexity_block(low_qs, min_duration)
        blocks.append({'type': btype, 'questions': qs})
    return blocks