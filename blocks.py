import os
import shutil
import pandas as pd
from datetime import datetime
from pathlib import Path

from psychopy import visual, event, core
import winsound
from winsound import PlaySound as playsound
from pylsl import StreamInfo, StreamOutlet

from config import Config
from utils import load_science_questions, prepare_all_blocks

def send_marker(tag, outlet):
    """Push an LSL marker with ISO timestamp + tag."""
    ts = datetime.now().isoformat(timespec='microseconds')
    outlet.push_sample([f"{ts}/{tag}"])
    print(f"\n##### MARKER → {ts}/{tag} #####\n")


def run_blocks(pipe, subject_id):
    cfg = Config()

    # ── 1) Load question pools & prepare 4 blocks ─────────────────────────────────
    sci_base = Path(cfg.GLOBAL_QUESTIONS_DIR).parent / "science_questions"
    control_qs, high_qs, low_qs = load_science_questions(str(sci_base))
    blocks = prepare_all_blocks(control_qs, high_qs, low_qs, min_duration=360.0)

    # Diagnostic
    print("\n" + "#"*80)
    print(f"*** BLOCK SEQUENCE: {[b['type'] for b in blocks]}")
    print("#"*80 + "\n")

    win = visual.Window(
        size=cfg.WINDOW_SIZE,       
        color=cfg.WINDOW_COLOR,
        units='norm',
        fullscr=cfg.FULLSCREEN
    )
    stim = visual.TextStim(
        win,
        text=cfg.STIM_TEXT,
        color=cfg.STIM_COLOR,
        height=cfg.STIM_HEIGHT
    )
    start_text = visual.TextStim(
        win,
        text=cfg.START_TEXT,
        color=cfg.STIM_COLOR,
        height=cfg.START_TEXT_HEIGHT
    )

    # ── 3) LSL outlet for markers ──────────────────────────────────────────────────
    info   = StreamInfo('ExpMarker', 'Markers', 1, 0, 'string', 'exp1234')
    outlet = StreamOutlet(info)

    # ── 4) Wait for SPACE to begin ────────────────────────────────────────────────
    start_text.draw()
    win.flip()
    show_stim = lambda dur: (stim.draw(), win.flip())
    event.waitKeys(keyList=['space'])
    show_stim(22)
 
    win.flip()

    results = []

    # Block loop
    for blk_idx, block in enumerate(blocks, start=1):
        block_folder = cfg.BASE_DATA_DIR / subject_id / f"block_{blk_idx:02d}"
        questions_sub = block_folder / "questions"
        os.makedirs(questions_sub, exist_ok=True)
        show_stim(100000)

        pd.DataFrame(block['questions']).to_csv(block_folder / "metadata.csv", index=False)

        # Notify collector & mark start
        send_marker(f"start_block_{blk_idx:02d}", outlet)
        pipe.send({'cmd':'start','folder': str(block_folder)})

        # Dynamic question loop
        total_audio = 0.0
        answer_counts = {'biology':0, 'chemistry':0, 'physics':0}
        idx = 0

        while True:
            print(answer_counts)
            show_stim(10000)

            results_block = []

            q = block['questions'][idx % len(block['questions'])]
            print(q)
            idx += 1
            subject = q.get('subject')

            # Onset
            tag = f"blk{blk_idx:02d}_q{idx:02d}_{Path(q['path']).stem}"
            print(f"*** QUESTION: {tag} ({subject})")
            send_marker(f"{tag}_onset", outlet)
            
            # Play and wait duration
            playsound(q['path'], winsound.SND_FILENAME)
            total_audio += q['duration']
            event.clearEvents(eventType='keyboard')
            
            # Answer window
            answer = -1
            clk = core.Clock()
            while clk.getTime() < 10.0:
                print(clk.getTime(),end='\r')
                keys = event.getKeys(keyList=['left','right'])
                if keys:
                    answer = keys[0]
                    print(answer)
                    if answer == 'left':
                        answer = 0
                        print(answer)
                    else:
                        answer = 1
                        print(answer)
                    total_audio += clk.getTime()
                    send_marker(f"{tag}_answered_{answer}", outlet)
                    break

            if answer == -1:
                total_audio += clk.getTime()
                send_marker(f"{tag}_no_response", outlet)

            # Track counts for complexity blocks
            if subject in answer_counts:
                    answer_counts[subject] += 1

            results_block.append({
                'block': blk_idx,
                'question': tag,
                'subject': subject,
                'response': answer,
                'expected_answer': q.get('answer'),
                'score': 1 if answer == q.get('answer') else 0,
                'time': datetime.now().isoformat()
            })
            print(total_audio)
            # Check end criteria
            if total_audio >= 60.0:
                if block['type'] == 'control':
                    pd.DataFrame(results_block).to_csv(questions_sub,index=False)
                    break
                # complexity blocks: equal counts and at least one per subject
                counts = [answer_counts[s] for s in ('biology','chemistry','physics')]
                if len(set(counts)) == 1 and counts[0] > 0:
                    break

        # End block
        send_marker(f"stop_block_{blk_idx:02d}", outlet)
        pipe.send({'cmd':'stop','folder': str(block_folder)})

    # Finish experiment
    send_marker("experiment_complete", outlet)
    pipe.send({'cmd':'shutdown','folder':''})

    # Save results
    pd.DataFrame(results).to_csv(cfg.BASE_DATA_DIR / subject_id / "results.csv", index=False)
    print(f"Saved results for {subject_id}")

    win.close(); core.quit()