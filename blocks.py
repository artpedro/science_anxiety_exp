# blocks.py

import os
import shutil
import pandas as pd
from datetime import datetime
from pathlib import Path
from pylsl import StreamInfo, StreamOutlet
from config import Config
from utils import load_science_questions, prepare_all_blocks, wait_for_streams
from psychopy import visual, event, core
import sys
if sys.platform.startswith("win"):
    import winsound
    from winsound import Playsound as playsound
    print('importing winsound for audio playback')
    def play_audio(path: str):
        """Windows: use winsound, then sleep the known duration."""
        playsound(path, winsound.SND_FILENAME)
else:
    print('importing playsound for linux')
    from playsound import playsound
    def play_audio(path: str):
        """Linux (and Mac): use playsound, then sleep the known duration."""
        playsound(str(Path(path).absolute()))
        
# Try to import winsound if on Windows, otherwise fall back:
if sys.platform.startswith("win"):
    def play_audio(path: str):
        """Windows: use winsound, then sleep the known duration."""
        winsound.PlaySound(path, winsound.SND_FILENAME)
else:
    def play_audio(path: str):
        """Linux (and Mac): use PsychoPy’s sound module."""
        playsound(path)
        
def send_marker(tag, outlet):
    """Push an LSL marker with ISO timestamp + tag."""
    ts = datetime.now().isoformat(timespec='microseconds')
    outlet.push_sample([f"{ts}/{tag}"])
    print(f"\n##### MARKER → {ts}/{tag} #####\n")

def run_blocks(pipe, subject_id):
    cfg = Config()

    # ── Optional barrier: wait until all streams exist ─────────
    if cfg.WAIT_FOR_STREAMS:
        print("\n" + "#"*60)
        print("🔍  Awaiting all LSL streams before starting experiment …")
        print("#"*60 + "\n")
        wait_for_streams(
            cfg.STREAM_NAMES,
            timeout=cfg.STREAM_CHECK_TIMEOUT,
            retry_interval=cfg.STREAM_CHECK_INTERVAL
        )

    # ── Then proceed with PsychoPy setup & SPACE prompt ─────────
    # ── 1) Load question pools & prepare 4 blocks ─────────────────────────────────
    sci_base     = Path(cfg.GLOBAL_QUESTIONS_DIR).parent / "science_questions"
    control_qs, high_qs, low_qs = load_science_questions(str(sci_base))
    blocks       = prepare_all_blocks(control_qs, high_qs, low_qs, min_duration=360.0)

    # Diagnostic: show chosen block order
    print("\n" + "#"*80)
    print(f"*** BLOCK SEQUENCE: {[b['type'] for b in blocks]}")
    print("#"*80 + "\n")

    # ── 2) PsychoPy setup ───────────────────────────────────────────────────────────
    # PsychoPy window
    win = visual.Window(
        size=cfg.WINDOW_SIZE,
        fullscr=cfg.FULLSCREEN,
        color=cfg.WINDOW_COLOR,
        units='norm'
    )
    # Gray background with black cross
    stim = visual.TextStim(win, text=cfg.STIM_TEXT,
                           color=cfg.STIM_COLOR, height=cfg.STIM_HEIGHT)
    start_text = visual.TextStim(win, text=cfg.START_TEXT,
                                 color=cfg.STIM_COLOR, height=cfg.START_TEXT_HEIGHT)
    # A helper to show the fixation cross
    show_stim = lambda: (stim.draw(), win.flip())
    show_stim()
    # ── 3) LSL outlet for markers ──────────────────────────────────────────────────
    info   = StreamInfo('ExpMarker', 'Markers', 1, 0, 'string', 'exp1234')
    outlet = StreamOutlet(info)

    # ── 4) Wait for SPACE to begin ────────────────────────────────────────────────
    start_text.draw()
    win.flip()
    event.waitKeys(keyList=['space'])
    show_stim()
    win.flip()

    # ── 5) Loop over each of the four blocks ────────────────────────────────────────
    for blk_idx, block in enumerate(blocks, start=1):
        # Prepare block folder and metadata container
        block_folder    = cfg.BASE_DATA_DIR / subject_id / f"block_{blk_idx:02d}"
        os.makedirs(block_folder, exist_ok=True)
        
        # List to accumulate metadata rows for this block
        block_metadata = []

        # Notify collector & mark block start
        send_marker(f"start_block_{blk_idx:02d}", outlet)
        pipe.send({'cmd':'start','folder': str(block_folder)})

        # Variables to enforce the "≥6 min of audio" + balancing
        total_audio   = 0.0
        answer_counts = {'biology': 0, 'chemistry': 0, 'physics': 0}
        idx           = 0

        # ── 6) Dynamic question loop ────────────────────────────────────────────────
        while True:
            # Show fixation during the inter‐question period
            show_stim()

            # Select next question (wrap around if needed)
            q = block['questions'][idx % len(block['questions'])]
            idx += 1
            subject = q.get('subject')

            # Build a unique tag for LSL markers
            tag = f"blk{blk_idx:02d}_q{idx:02d}_{Path(q['path']).stem}"
            print(f"*** QUESTION: {tag} ({subject})")

            # ── 6a) Question onset & playback ───────────────────────────────
            send_marker(f"{tag}_onset", outlet)
            play_audio(q['path'])
            total_audio += q['duration']

            # Flush any keys pressed during audio
            event.clearEvents(eventType='keyboard')

            # ── 6b) Up to 5 s answer window, break early on response ────────
            response = None
            clk      = core.Clock()
            while clk.getTime() < 10.0:
                keys = event.getKeys(keyList=['left','right'])
                if keys:
                    key = keys[0]
                    response = 1 if key == 'right' else 0
                    total_audio += clk.getTime()
                    send_marker(f"{tag}_answered_{response}", outlet)
                    break

            # No response within 5 s
            if response is None:
                total_audio += clk.getTime()
                send_marker(f"{tag}_no_response", outlet)

            # ── 6c) Compute score & track subject counts ───────────────────
            expected = q['answer']               # from your pool
            score    = 1 if (response == expected) else 0

            if subject in answer_counts:
                answer_counts[subject] += 1

            # Record this question’s metadata row
            block_metadata.append({
                'question':        tag,
                'subject':         subject,
                'response':        response if response is not None else -1,
                'expected_answer': expected,
                'score':           score
            })

            print(f" Total audio so far: {total_audio:.1f}s — Counts: {answer_counts}")

            # ── 6d) Check end‐of‐block criteria ─────────────────────────────
            # Must have at least 360 s of audio...
            if total_audio >= 10.0:
                if block['type'] == 'control':
                    break
                # Complexity blocks need equal counts and at least one of each
                counts = [answer_counts[s] for s in ('biology','chemistry','physics')]
                if min(counts) > 0 and len(set(counts)) == 1:
                    break
        core.wait(10)

        # ── 7) End of block: write metadata, stop collector, send marker ─────
        metadata_path = block_folder / "metadata.csv"
        pd.DataFrame(block_metadata).to_csv(metadata_path, index=False)
        print(f"Saved block metadata → {metadata_path}")

        send_marker(f"stop_block_{blk_idx:02d}", outlet)
        pipe.send({'cmd':'stop','folder': str(block_folder)})

    # ── 8) Experiment complete ────────────────────────────────────────────────
    send_marker("experiment_complete", outlet)
    pipe.send({'cmd':'shutdown','folder': ''})

    # ── 9) Cleanup ─────────────────────────────────────────────────────────────
    win.close()
    core.quit()
