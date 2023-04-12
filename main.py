import logging
import threading
import time
import queue
import pyautogui
from pynput import mouse
import pygame # for sound effects
from record import continuous_record_microphone
from transcription_utils import continuously_transcribe_clips, set_latest_transcription, get_latest_transcription
#import transcription_utils


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%I:%M:%S')

# Initialize pygame mixer
pygame.init()
start_sound = pygame.mixer.Sound('/usr/share/sounds/sound-icons/percussion-12.wav')
start_sound.set_volume(0.1)
end_sound = pygame.mixer.Sound('/usr/share/sounds/sound-icons/percussion-50.wav')
end_sound.set_volume(0.1)

# Create threading events and queue
stop_everything = threading.Event()
clip_queue = queue.Queue()
latest_transcription_lock = threading.Lock()
latest_transcription = ''
last_seen_transcription = ''
mouse_block_flag = threading.Event()
mouse_block_flag.set()

def on_click(x, y, button, pressed):
    if pressed and button == mouse.Button.middle:
        if mouse_block_flag.is_set():
            start_sound.play()
            print('Middle mouse button pressed')
            # type period
            mouse_block_flag.clear()
        else:
            stop_everything.set()
            

def continuously_monitor_mouse():
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()


def main():
    # Start mouse monitor thread
    mouse_monitor_thread = threading.Thread(target=continuously_monitor_mouse)
    mouse_monitor_thread.start()

    # Play end sound
    end_sound.play()

    # Run initial recording thread
    initial_recording_thread = threading.Thread(target=continuous_record_microphone, args=(clip_queue, stop_everything))
    initial_recording_thread.start()
    time.sleep(0.3)
    stop_everything.set()
    initial_recording_thread.join()

    while True:
        # Wait for middle mouse click
        while mouse_block_flag.is_set():
            time.sleep(0.02)

        # Play start sound and reset transcription variables
        start_sound.play()
        stop_everything.clear()
        last_seen_transcription = ''
        set_latest_transcription('')

        # Start recording thread
        recording_thread = threading.Thread(target=continuous_record_microphone, args=(clip_queue, stop_everything))
        recording_thread.start()

        # Start transcription thread
        transcription_thread = threading.Thread(target=continuously_transcribe_clips, args=(clip_queue, stop_everything))
        transcription_thread.start()

        # Wait for recording to finish
        recording_thread.join()

        # Stop transcription thread and clear queue
        stop_everything.set()
        transcription_thread.join()
        while not clip_queue.empty():
            clip_queue.get()

        # Print latest transcription
        new_transcription = get_latest_transcription()
        if new_transcription != last_seen_transcription and new_transcription != '':
            i = 0
            while i < len(last_seen_transcription) and i < len(new_transcription) and last_seen_transcription[i] == new_transcription[i]:
                i += 1

            # Backtrack and delete incorrect characters from the old transcription
            number_of_backspaces = len(last_seen_transcription) - i
            pyautogui.write(['backspace'] * number_of_backspaces)

            # Type only the new parts of the new transcription
            pyautogui.typewrite(new_transcription[i:])
            print(f'typing: {new_transcription[i:]}')
            last_seen_transcription = new_transcription

if __name__ == '__main__':
    main()