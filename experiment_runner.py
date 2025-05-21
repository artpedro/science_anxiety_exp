from multiprocessing import Process, Pipe
from data_collector import collector_loop
from blocks import run_blocks

if __name__ == "__main__":
    # Collect subject ID in main process
    subject_id = input("Enter patient ID: ").strip()

    parent_conn, child_conn = Pipe()

    p_collector = Process(target=collector_loop, args=(child_conn,))
    p_blocks    = Process(target=run_blocks,      args=(parent_conn, subject_id))

    p_collector.start()
    p_blocks.start()

    p_blocks.join()
    parent_conn.send({"cmd": "shutdown"})
    p_collector.join()