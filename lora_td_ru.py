import yaml
import time
from tdo_rup import tdo_rup
import RPi.GPIO as GPIO
import signal
import os
import sys

with open('auto_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

parameter_sets = config['parameter_sets']

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(26, GPIO.OUT)

GPIO.output(26, GPIO.HIGH)
time.sleep(0.5)

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ru_wav_recordings'))
os.makedirs(output_dir, exist_ok=True)

created_wav_files = []

def cleanup_and_exit(signum=None, frame=None):
    print("\nCtrl+C detected. Cleaning up WAV files...")
    for wav_file in created_wav_files:
        if os.path.exists(wav_file):
            try:
                os.remove(wav_file)
                print(f"Deleted: {wav_file}")
            except Exception as e:
                print(f"Could not delete {wav_file}: {e}")
    GPIO.cleanup()
    print("GPIO cleaned up. Exiting.")
    sys.exit(1)

signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

for idx, params in enumerate(parameter_sets):
    param_str = "_".join(f"{k}-{str(v).replace(' ', '')}" for k, v in params.items())
    wav_filename = f"ru_{idx+1}_{param_str}.wav"
    wav_path = os.path.join(output_dir, wav_filename)

    print(f"\nRunning configuration {idx+1}: {params}")
    print(f"Saving WAV to: {wav_path}")

    tb = tdo_rup(
        message_str=params.get('message_str', 'TEST'),
        mult_amp=params.get('mult_amp', 0.5),
        rx_mix_freq=params.get('rx_mix_freq', -1000),
        tx_mix_freq=params.get('tx_mix_freq', 1000),
        tx_cr=params.get('tx_cr', 1),
        tx_rx_bw=params.get('tx_rx_bw', 8000),
        tx_rx_sf=params.get('tx_rx_sf', 7),
        tx_rx_sync_word=params.get('tx_rx_sync_word', [18]),
        wav_file_path=wav_path
    )

    created_wav_files.append(wav_path)

    tb.start()

    timeout = 30  # seconds
    start_time = time.time()
    try:
        print('Running for up to 10 seconds. Press Ctrl+C to quit early.')
        while True:
            if time.time() - start_time > timeout:
                print('Timeout reached, stopping...')
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        cleanup_and_exit()
    tb.stop()
    tb.wait()
    del tb
    time.sleep(1)

GPIO.cleanup()
print("Audio device closed, GPIO cleaned up")