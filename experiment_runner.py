#from multiprocessing import Process, Pipe

#from data_collector import collector_loop
from blocks import run_blocks

if __name__ == "__main__":
    # Collect subject ID in main process
    subject_id = input("Enter patient ID: ").strip()

    # 4) Run the PsychoPy stimulus + pipe.send() logic in MAIN
    run_blocks(subject_id)