import os
from datetime import datetime
from config import Config
from lsl_to_edf_reader import LSLToEdfReader


def collector_loop(pipe):
    readers = []
    block_timestamp = None

    while True:
        msg = pipe.recv()
        cmd = msg.get("cmd")

        if cmd == "start":
            active_folder = msg["folder"]
            os.makedirs(active_folder, exist_ok=True)

            block_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            block_tag       = os.path.basename(active_folder)

            print("\n" + "="*60)
            print(f"*** DATA COLLECTOR: Starting block {block_tag} at {block_timestamp}")
            print(f"*** Streams: {Config.STREAM_NAMES}")
            print("="*60 + "\n")

            readers = []
            for stream_name in Config.STREAM_NAMES:
                sensor_name = stream_name.lower().replace(' ', '_')
                fname       = f"{block_tag}_{block_timestamp}_{sensor_name}.edf"
                out_path    = os.path.join(active_folder, fname)

                reader = LSLToEdfReader(stream_name, out_path)
                reader.start()
                print(stream_name + " started")
                readers.append(reader)

        elif cmd == "stop":
            for r in readers:
                r.stop()
            readers = []
            block_timestamp = None

        elif cmd == "shutdown":
            for r in readers:
                r.stop()
            break