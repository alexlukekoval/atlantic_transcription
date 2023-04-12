import logging
import threading
import time
import pyaudio


class Clip:
    def __init__(self, audio_frames, time):
        self.audio_frames = audio_frames
        self.time = time

def continuous_record_microphone(clip_queue, stop_event):
    logging.info('recording microphone...')
    sample_rate = 16000
    chunk_size = 100
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=sample_rate, input=True, frames_per_buffer=chunk_size)

    while not stop_event.is_set():
        frames = []
        start_time = time.time()
        # want clips 100ms long
        while (time.time() - start_time) < 0.1:
            data = stream.read(chunk_size)
            frames.append(data)
        logging.debug(f'time to record: {time.time() - start_time}')
        clip = Clip(frames, time.time())
        clip_queue.put(clip)
        logging.debug('put clip in queue')

