import logging
import threading
import time
import numpy as np
import soundfile as sf
import whisper
from vad import vad

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%I:%M:%S'
)

logging.info('Loading models...')
options = whisper.DecodingOptions(language='en')
model_transcription = whisper.load_model('base', device='cuda')
logging.info('Models loaded.')


def transcribe_pad_frames(frames):
    """Note: It's best to do everything at 16000 sample rate."""
    start_time = time.time()
    audio_padded = whisper.pad_or_trim(frames)
    mel = whisper.log_mel_spectrogram(audio_padded).to('cuda')
    options = whisper.DecodingOptions(language='en')
    model_transcription = whisper.load_model('base', device='cuda')
    result = whisper.decode(model_transcription, mel, options)
    end_time = time.time()
    delta = end_time - start_time
    delta = round(delta, 2)
    logging.info(f'Transcription time:\t {delta}')
    if end_time - start_time > 2:
        logging.warning(f'Transcription took more than 2 seconds: {end_time - start_time}, text: {result.text}')
    logging.debug(f'Transcription result:\t {result.text}')
    no_speech_prob = result.no_speech_prob
    logging.debug(f'No_speech_prob:\t {no_speech_prob}')
    logging.info(f'Result.text:\t {result.text[-30:]}')
    return result


def detect_hallucination(text: str, seconds: float):
    """Use seconds because the count should scale with the length of the text."""
    if seconds < 1:
        seconds = 1
    middle = text[(len(text)-3)//2:(len(text)+3)//2]
    # Count how often middle appears in text.
    count = text.count(middle)
    if count > seconds * 2:
        logging.info(f'Hallucination because of middle: {middle}, seconds: {seconds}, count: {count}')
        return True
    # No one can say more than 40 characters per second.
    if len(text) > seconds * 40:
        logging.info(f'Hallucination because of length: {text}, seconds: {seconds}, len: {len(text)}')
        return True
    return False


def continuously_transcribe_clips(clip_queue, stop_event):
    logging.info('Starting continuous transcription thread.')
    all_audio = []
    while not stop_event.is_set():
        new_clips = [clip_queue.get()]
        logging.debug('Got latest clip from queue.')
        for _ in range(clip_queue.qsize()):
            new_clips.append(clip_queue.get())
        for clip in new_clips:
            audio = clip.audio_frames
            audio = np.concatenate([np.frombuffer(frame, dtype=np.int16) for frame in audio])
            all_audio.append(audio)
        all_audio_array = np.concatenate(all_audio)
        result = transcribe_pad_frames(all_audio_array)
        nsp = result.no_speech_prob
        if nsp > 0.3:
            logging.warning(f'No_speech_prob: {nsp}, text: {result.text}')
            continue
        if detect_hallucination(result.text, len(all_audio_array)/10):
            logging.warning(f'Got hallucination: {result.text}')
            continue
        set_latest_transcription(result.text)


latest_transcription = ''
latest_transcription_lock = threading.Lock()


def set_latest_transcription(text):
    global latest_transcription
    with latest_transcription_lock:
        latest_transcription = text

def get_latest_transcription():
    global latest_transcription
    with latest_transcription_lock:
        return latest_transcription
