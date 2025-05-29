# lsl_to_edf_reader.py

import threading
import time
import numpy as np
import os
import csv
from pylsl import StreamInlet, resolve_byprop
import pyedflib

class LSLToEdfReader(threading.Thread):
    """
    Thread that pulls from one LSL stream and, upon stop(), writes an EDF+ file.
    Uses resolve_byprop() to find streams by their 'name'.
    """
    def __init__(self, stream_name, out_edf_path):
        super().__init__(daemon=True)
        self.stream_name = stream_name
        self.out_edf     = out_edf_path
        self._running    = threading.Event()
        self._running.set()
        self.samples, self.times = [], []

    def run(self):
        inlet = None
        while self._running.is_set():
            # If we don't have a valid inlet yet, try to resolve it
            if inlet is None:
                try:
                    streams = resolve_byprop(
                            prop='name',
                            value=self.stream_name,
                            minimum=1,
                            timeout=2.0
                        )
                    inlet = StreamInlet(streams[0])
                    print(f"\n{'*'*10} ★ Connected to LSL stream: {self.stream_name} ★ {'*'*10}\n")
                except Exception as e:
                    print(f"\n{'!'*10} Failed to resolve {self.stream_name}: {e}. Retrying in 1s. {'!'*10}\n")
                    time.sleep(1.0)
                    continue

            # Try to pull a sample
            try:
                sample, ts = inlet.pull_sample(timeout=1.0)
                if sample:
                    self.samples.append(sample)
                    self.times.append(ts)
            except Exception as e:
                print(f"\n{'!'*10} Lost connection to {self.stream_name}: {e}. Will reconnect. {'!'*10}\n")
                inlet = None  # force a reconnect

        # Once stopped, write out the EDF file (if any data)
        self._write_edf()

    def stop(self):
        # Signal to end collection, wait for thread to finish
        self._running.clear()
        self.join()

    def _write_edf(self):
        # Turn buffered samples into an array: shape (n_channels, n_samples)
        data = np.array(self.samples).T

        # If this is the marker stream (string data), write CSV instead
        if data.dtype.kind in {'U', 'S'}:
            csv_path = os.path.splitext(self.out_edf)[0] + ".csv"
            print(f"\n{'*'*10} Writing marker CSV → {csv_path} {'*'*10}\n")
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['lsl_timestamp', 'marker'])
                # self.samples is a list of 1-element lists [marker_str]
                for sample, ts in zip(self.samples, self.times):
                    writer.writerow([ts, sample[0]])
            return

        # --- Numeric stream path: write EDF+ ---
        # Need at least two timestamps to compute a sampling interval
        if len(self.times) < 2:
            print(f"\n{'!'*10} Too few samples for {self.stream_name}; skipping EDF. {'!'*10}\n")
            return

        # Estimate sample rate
        dt = np.median(np.diff(self.times))
        if np.isnan(dt) or dt <= 0:
            print(f"\n{'!'*10} Invalid dt={dt} for {self.stream_name}; skipping EDF. {'!'*10}\n")
            return
        fs = int(round(1.0 / dt))

        # Build channel headers
        n_ch = data.shape[0]
        headers = []
        for ch in range(n_ch):
            headers.append({
                'label':        f'ch{ch}',
                'dimension':    '',
                'sample_rate':  fs,
                'physical_min': float(np.min(data[ch])),
                'physical_max': float(np.max(data[ch])),
                'digital_min':  -32768,
                'digital_max':  32767,
                'transducer':   '',
                'prefilter':    ''
            })

        # Write EDF+
        with pyedflib.EdfWriter(self.out_edf, n_ch, file_type=pyedflib.FILETYPE_EDFPLUS) as writer:
            writer.setSignalHeaders(headers)
            writer.writeSamples(data)

            # If you have annotations buffered (e.g. markers in a separate list),
            # you can also call:
            # writer.writeAnnotations(onset_times, durations, texts)

        print(f"\n{'*'*10} ★ Wrote EDF for {self.stream_name} → {self.out_edf} ★ {'*'*10}\n")