from multiprocessing import Process, Pipe
from data_collector import collector_loop
from blocks import run_blocks

if __name__ == "__main__":
    # Collect subject ID in main process
    subject_id = input("Enter patient ID: ").strip()


    # 2) Create the control Pipe
    parent_conn, child_conn = Pipe()

    # 3) Spawn only the data collector
    p_collector = Process(target=collector_loop, args=(child_conn,))
    p_collector.start()

    # 4) Run the PsychoPy stimulus + pipe.send() logic in MAIN
    run_blocks(parent_conn, subject_id)

    # 5) When that returns, shut down collector
    parent_conn.send({"cmd": "shutdown"})
    p_collector.join()