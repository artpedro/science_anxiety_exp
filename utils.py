import random
import wave
import os
import glob
from typing import List, Dict
from collections import Counter
import time

def get_wav_duration(file_path: str) -> float:
    """Return duration of a WAV file in seconds."""
    with wave.open(file_path, 'rb') as wf:
        return wf.getnframes() / float(wf.getframerate())


def load_science_questions(base_dir='science'):
    """
    Walks the folder hierarchy and returns three pools with subject tags:
      - control_qs: List of {path, answer, duration, subject='control'}
      - high_qs: dict of subject->list of {path, answer, duration, subject}
      - low_qs: same as high_qs
    """
    if base_dir == 'math':
        base = os.path.join('data', 'math_questions')
    else:
        base = os.path.join('data', 'science_questions')  # in case base_dir is a custom path

    control_qs = []

    if base_dir == "science":
        subjects = ("biology", "chemistry", "physics")
        high_qs = {subj: [] for subj in subjects}
        low_qs = {subj: [] for subj in subjects}
    else:
        subjects = ("math",)
        high_qs = {'math': []}
        low_qs = {'math': []}

    # Control questions
    for ans in ("false", "true"):
        folder = os.path.join(base, "control", ans)
        for wav_path in glob.glob(os.path.join(folder, "*.wav")):
            control_qs.append({
                "path": wav_path,
                "answer": 1 if ans == "true" else 0,
                "duration": get_wav_duration(wav_path),
                "subject": "control"
            })
    random.shuffle(control_qs)

    control_qs1 = control_qs[:len(control_qs)//2]
    control_qs2 = control_qs[len(control_qs)//2:]

    if base_dir == 'science':
        # High and low complexity questions
        for complexity_label, pool in (("high_complexity", high_qs), ("low_complexity", low_qs)):
            for subj in subjects:
                for ans in ("false", "true"):
                    folder = os.path.join(base, complexity_label, subj, ans)
                    for wav_path in glob.glob(os.path.join(folder, "*.wav")):
                        pool[subj].append({
                            "path": wav_path,
                            "answer": 1 if ans == "true" else 0,
                            "duration": get_wav_duration(wav_path),
                            "subject": subj
                        })
                random.shuffle(pool[subj])
    else:
        for complexity_label, pool in (("high_complexity", high_qs), ("low_complexity", low_qs)):
            for ans in ("false", "true"):
                folder = os.path.join(base, complexity_label, ans)
                for wav_path in glob.glob(os.path.join(folder, "*.wav")):
                    pool['math'].append({
                        "path": wav_path,
                        "answer": 1 if ans == "true" else 0,
                        "duration": get_wav_duration(wav_path)
                    })
            random.shuffle(pool['math'])

    return control_qs1,control_qs2, high_qs, low_qs


def generate_control_block(control_qs: List[Dict], min_duration: float = 360.0) -> List[Dict]:
    """
    Return shuffled control questions until total duration >= min_duration.
    Wrap around if necessary.
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
    pool: dict of subject->[question dicts]
    Round-robin by subject until total audio >= min_duration, then equalize question counts.
    """
    subjects = list(pool.keys())
    pools = {subj: pool[subj].copy() for subj in subjects}
    for subj in subjects:
        random.shuffle(pools[subj])

    seq = []
    total = 0.0
    idx = {subj: 0 for subj in subjects}
    counts = Counter()

    # Fill until min_duration
    while total < min_duration:
        for subj in subjects:
            q = pools[subj][idx[subj] % len(pools[subj])]
            idx[subj] += 1
            seq.append(q)
            counts[subj] += 1
            total += q['duration']
            if total >= min_duration:
                break

    # Ensure equal count per subject
    max_count = max(counts.values())
    for subj in subjects:
        while counts[subj] < max_count:
            q = pools[subj][idx[subj] % len(pools[subj])]
            idx[subj] += 1
            seq.append(q)
            counts[subj] += 1

    return seq


def prepare_all_blocks(
    control_qs1: List[Dict],
    control_qs2: List[Dict],
    high_qs: Dict[str, List[Dict]],
    low_qs: Dict[str, List[Dict]],
    min_duration: float = 360.0
) -> List[Dict]:
    """
    Returns 4 blocks in one of two fixed sequences:
      High → Control → Low → Control
      or Low → Control → High → Control
    """
    configs = [
        ['high_complexity', 'control1', 'low_complexity', 'control2'],
        ['low_complexity', 'control1', 'high_complexity', 'control2'],
    ]
    sequence = random.choice(configs)

    blocks = []
    for btype in sequence:
        if btype == 'control1':
            qs = generate_control_block(control_qs1, min_duration)
        elif btype == 'control2':
            qs = generate_control_block(control_qs2, min_duration)
        elif btype == 'high_complexity':
            qs = generate_complexity_block(high_qs, min_duration)
        else:
            qs = generate_complexity_block(low_qs, min_duration)
        blocks.append({'type': btype, 'questions': qs})
    return blocks

def prepare_test_block(min_duration):
    control_qs1,_, _, _ = load_science_questions('math')
    qs = generate_control_block(control_qs1, min_duration)
    return [{'type': 'control1', 'questions':qs}]


    
