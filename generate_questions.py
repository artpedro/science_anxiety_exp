import pandas as pd
import glob
import os
import numpy as np
import random
import torch
import gc
from TTS.api import TTS
import shutil

def generate_audio(text, tts_model, speaker='test', speaker_wav=None, language='pt', output_path=None, seed=12):
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False 

    print(f"Generating audio for: {text}")
    print(f"Saving to: {output_path}")
    # Model is loaded externally; no re-initialization here
    # Disable gradient tracking and reduce memory footprint
    
    with torch.no_grad():
        if speaker_wav:
            tts_model.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,
                language=language,
                split_sentences=True
            )
        else:
            tts_model.tts_to_file(
                text=text,
                file_path=output_path,
                speaker=speaker,
                language=language,
                split_sentences=True
            )
    # Clear caches to free memory
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    return 1


def aggregate_question_bank(
    data_dir='data/question_bank',
    output_csv='data/question_bank/concatenated_questions.csv'
    ):
    """
    1) Load all CSVs from data_dir
    2) Concatenate into one DataFrame
    3) Assign a new sequential UID (1,2,3,...)
    4) Write the full DataFrame to output_csv
    """
    # find all CSVs
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))
    print(f"Found {len(csv_files)} CSV files in '{data_dir}'")

    # read and concat
    df_list = [pd.read_csv(f) for f in csv_files]
    question_bank = pd.concat(df_list, ignore_index=True)
    print(f"Aggregated {len(question_bank)} rows into a single DataFrame")

    # assign new UID as 1,2,3,...
    question_bank.reset_index(drop=True, inplace=True)
    question_bank['UID'] = question_bank.index + 1440 + 1
    print(f"Assigned new UID starting from 1441: {question_bank['UID'].min()} to {question_bank['UID'].max()}")

    # write out the full concatenated CSV
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    question_bank.to_csv(output_csv, index=False)
    print(f"Wrote concatenated CSV with new UID to: {output_csv}")

    return question_bank

def create_audio_pipeline(data_root='data'):
    """Generate audio files for each question, but stop if free disk ≤1 GB every 10 items."""
    qb = aggregate_question_bank(data_dir=os.path.join(data_root, 'question_bank'))
    tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    total = len(qb)

    comp_map    = {'Baixa': 'low_complexity', 'Alta': 'high_complexity'}
    subject_map = {
        'Química': 'chemistry', 'Física': 'physics',
        'Biologia': 'biology', 'Controle': 'control',
        'MatCon': 'matcon', 'Matemática': 'math'
    }
    cond_map    = {1: 'true', 0: 'false'}

    for count, (_, row) in enumerate(qb.iterrows(), start=1):
        # Every 10 questions, check free disk space
        if count % 10 == 0:
            usage = shutil.disk_usage(data_root)
            free_gb = usage.free / (1024**3)
            print(free_gb," GB free on disk")
            if free_gb <= 1:
                print(f"[{count}/{total}] Low disk space: only {free_gb:.2f} GB free. Stopping pipeline.")
                break

        uid  = row['UID']
        subj = subject_map.get(row['Área'], row['Área'].lower())
        cond = cond_map.get(row['Condição'], str(row['Condição']).lower())

        # Routing logic
        if subj == 'math':
            comp    = comp_map.get(row['Complexidade'], row['Complexidade'].lower())
            out_dir = os.path.join(data_root,'math_questions',comp,cond)
            fname = f"{uid:03d}_{subj}_{cond}.wav"
            
        elif subj == 'matcon':
            out_dir = os.path.join(data_root, 'math_questions', 'control', cond)
            fname   = f"{uid:03d}_control_{cond}.wav"
        
        elif subj == 'control':
            out_dir = os.path.join(data_root, 'science_questions', 'control', cond)
            fname   = f"{uid:03d}_{subj}_{cond}.wav"

        else:
            comp    = comp_map.get(row['Complexidade'], row['Complexidade'].lower())
            out_dir = os.path.join(data_root, 'science_questions', comp, subj, cond)
            fname   = f"{uid:03d}_{comp}_{subj}_{cond}.wav"

        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, fname)

        if os.path.exists(output_path):
            print(f"[{count}/{total}] Skipping existing: {output_path}")
            continue

        print(f"[{count}/{total}] Generating → {output_path}")
        generate_audio(
            text=row['Tarefa'],
            tts_model=tts_model,
            speaker='Damjan Chapman',
            language='pt',
            output_path=output_path
        )

    print("Audio pipeline completed (or stopped due to low disk).")

# Example usage:
if __name__ == '__main__':
    create_audio_pipeline()
