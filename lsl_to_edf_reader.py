import threading
import numpy as np
from pylsl import StreamInlet, resolve_byprop
import pyedflib

class LSLToEdfReader(threading.Thread):
    def __init__(self, stream_name, out_edf_path):
        super().__init__(daemon=True)
        self.stream_name = stream_name
        self.out_edf     = out_edf_path
        self._running    = threading.Event()
        self._running.set()
        self.samples     = []
        self.times       = []

    def run(self):
        streams = resolve_byprop('name', self.stream_name)
        print("\n" + "*"*60)
        print(f"*** LSLToEdfReader: Connected to '{self.stream_name}' ({len(streams)} streams). Writing to {self.out_edf}.")
        print("*"*60 + "\n")
        inlet   = StreamInlet(streams[0])
        while self._running.is_set():
            sample, ts = inlet.pull_sample(timeout=1.0)
            if sample:
                self.samples.append(sample)
                self.times.append(ts)

    def stop(self):
        self._running.clear()
        self.join()
        self._write_edf()

    def _write_edf(self):
        data = np.array(self.samples).T
        dt   = np.median(np.diff(self.times))
        fs   = int(round(1.0 / dt))

        n_ch = data.shape[0]
        headers = []
        for ch in range(n_ch):
            headers.append({
                'label':        f'ch{ch}',
                'dimension':    '',
                'sample_rate':  fs,
                'physical_min': float(data[ch].min()),
                'physical_max': float(data[ch].max()),
                'digital_min':  -32768,
                'digital_max':  32767,
                'transducer':   '',
                'prefilter':    ''
            })

        with pyedflib.EdfWriter(self.out_edf, n_ch,
                                file_type=pyedflib.FILETYPE_EDFPLUS) as writer:
            writer.setSignalHeaders(headers)
            writer.writeSamples(data)