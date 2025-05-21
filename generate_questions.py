import pandas as pd
import glob
import os
import numpy as np
import random
import torch
import gc
from TTS.api import TTS

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


def aggregate_question_bank(data_dir='data/question_bank'):
    """Load all CSVs from data_dir into a DataFrame and add a UID column."""
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))
    print(f"Found {len(csv_files)} CSV files in '{data_dir}'")
    df_list = [pd.read_csv(f) for f in csv_files]
    question_bank = pd.concat(df_list, ignore_index=True)
    question_bank['UID'] = question_bank['Número']
    print(f"Aggregated {len(question_bank)} questions into DataFrame")
    return question_bank

def create_audio_pipeline(data_root='data'):
    """Generate audio files for each question in the aggregated question bank."""
    # Aggregate CSVs into DataFrame
    qb = aggregate_question_bank(data_dir=os.path.join(data_root, 'question_bank'))
    # Load TTS model once without GPU to save memory
    tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    total = len(qb)
    print("Starting audio pipeline...")
    print(f"Total questions to process: {total}")
    # Mapping Portuguese terms to directory names
    comp_map = {'Baixa': 'low_complexity', 'Alta': 'high_complexity'}
    subject_map = {'Química': 'chemistry', 'Física': 'physics', 'Biologia': 'biology', 'Controle': 'control'}
    cond_map = {1: 'true', 0: 'false'}

    for count, (_, row) in enumerate(qb.iterrows(), start=1):
        uid = row['UID']

        print(f"[{count}/{total}] Processing UID {uid}")
        subj = subject_map.get(row['Área'], row['Área'].lower())
        cond = cond_map.get(row['Condição'], str(row['Condição']).lower())

        # Determine output path and filename
        if subj == 'control':
            out_dir = os.path.join(data_root, 'science_questions', 'control', cond)
            fname = f"{uid:03d}_{subj}_{cond}.wav"
        else:
            comp = comp_map.get(row['Complexidade'], row['Complexidade'].lower())
            out_dir = os.path.join(data_root, 'science_questions', comp, subj, cond)
            fname = f"{uid:03d}_{comp}_{subj}_{cond}.wav"
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, fname)
        print(f"Generating audio -> {output_path}")
        # Skip generation if file already exists
        if os.path.exists(output_path):
            print(f"Skipping existing audio: {output_path}")
            continue
        generate_audio(text=row['Tarefa'], tts_model=tts_model, speaker='Damjan Chapman', language='pt', output_path=output_path)
    print("Audio pipeline completed.")

# Example usage:
if __name__ == '__main__':
    create_audio_pipeline()
