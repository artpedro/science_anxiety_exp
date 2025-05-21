
import os
import shutil
import pandas as pd
from datetime import datetime
from pathlib import Path

from psychopy import visual, event, core
from winsound import PlaySound as playsound
from pylsl import StreamInfo, StreamOutlet

from config import Config
from utils import load_science_questions, prepare_all_blocks


def send_marker(tag, outlet):
    ts = datetime.now().isoformat(timespec='microseconds')
    outlet.push_sample([f"{ts}/{tag}"])
    print(f"MARKER → {ts}/{tag}")


def run_blocks(pipe, subject_id):
    cfg = Config()

    # Load and partition the 4 blocks
    base_dir = str(Path(cfg.GLOBAL_QUESTIONS_DIR).parent / "science_questions")
    control_qs, high_qs, low_qs = load_science_questions(base_dir)
    blocks = prepare_all_blocks(control_qs, high_qs, low_qs, min_duration=360.0)

    # PsychoPy setup
    win = visual.Window(size=cfg.WINDOW_SIZE,
                        color=cfg.WINDOW_COLOR,
                        units='norm')
    start_text = visual.TextStim(win,
                                 text=cfg.START_TEXT,
                                 color=cfg.STIM_COLOR,
                                 height=cfg.START_TEXT_HEIGHT)

    # LSL outlet
    info   = StreamInfo('ExpMarker','Markers',1,0,'string','exp1234')
    outlet = StreamOutlet(info)

    # Wait to start
    start_text.draw()
    win.flip()
    event.waitKeys(['space'])
    win.flip()

    results = []

    # Iterate 4 blocks
    for blk_idx, block in enumerate(blocks, start=1):
        block_folder = cfg.BASE_DATA_DIR / subject_id / f"block_{blk_idx:02d}"
        questions_sub = block_folder / "questions"
        os.makedirs(questions_sub, exist_ok=True)

        # Copy audio and save metadata
        for q in block['questions']:
            dst = questions_sub / Path(q['path']).name
            shutil.copy(q['path'], dst)
            q['path'] = str(dst)
        pd.DataFrame(block['questions']).to_csv(
            block_folder / "metadata.csv", index=False)

        # Start block
        send_marker(f"start_block_{blk_idx:02d}", outlet)
        pipe.send({'cmd':'start','folder': str(block_folder)})

        # Question loop
        for q_idx, q in enumerate(block['questions'], start=1):
            tag_base = f"blk{blk_idx:02d}_q{q_idx:02d}_{Path(q['path']).stem}"

            # Onset
            send_marker(f"{tag_base}_onset", outlet)
            playsound(q['path'], winsound.SND_FILENAME)
            core.wait(q['duration'])

            # Answer window (max 5s)
            answer = None
            clock = core.Clock()
            while clock.getTime() < 5.0:
                keys = event.getKeys(keyList=['left','right'])
                if keys:
                    answer = keys[0]
                    send_marker(f"{tag_base}_answered_{answer}", outlet)
                    break

            if answer is None:
                send_marker(f"{tag_base}_no_response", outlet)

            results.append({
                'block': blk_idx,
                'question_tag': tag_base,
                'response': answer or 'none',
                'timestamp': datetime.now().isoformat()
            })

        # End block
        send_marker(f"stop_block_{blk_idx:02d}", outlet)
        pipe.send({'cmd':'stop','folder': str(block_folder)})

    # Experiment complete
    send_marker("experiment_complete", outlet)
    pipe.send({'cmd':'shutdown','folder': ''})

    # Save results
    results_df = pd.DataFrame(results)
    out_path = cfg.BASE_DATA_DIR / subject_id / "results.csv"
    results_df.to_csv(out_path, index=False)
    print(f"Saved results to {out_path}")

    win.close()
    core.quit()
