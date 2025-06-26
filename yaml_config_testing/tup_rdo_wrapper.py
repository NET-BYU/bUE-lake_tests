import yaml
import time
from tup_rdo import tup_rdo
import RPi.GPIO as GPIO
import signal

# Load all parameter sets from YAML
with open('auto_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

parameter_sets = config['parameter_sets']

# prepare gpio

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(26, GPIO.OUT)

GPIO.output(26, GPIO.HIGH)
time.sleep(0.5)


for idx, params in enumerate(parameter_sets):
    print(f"\nRunning configuration {idx+1}: {params}")
    tb = tup_rdo(
        message_str=params.get('message_str', 'TEST'),
        mult_amp=params.get('mult_amp', 0.5),
        rx_mix_freq=params.get('rx_mix_freq', -1000),
        tx_mix_freq=params.get('tx_mix_freq', 1000),
        tx_rx_bw=params.get('tx_rx_bw', 8000),
        tx_cr=params.get('tx_cr', 1),
        tx_rx_sf=params.get('tx_rx_sf', 7),
        tx_rx_sync_word=params.get('tx_rx_sync_word', [18])
    )
    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    timeout = 10  # seconds
    start_time = time.time()
    try:
        print('Running for up to 10 seconds. Press Ctrl+C to quit early.')
        while True:
            if time.time() - start_time > timeout:
                print('Timeout reached, stopping...')
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('Keyboard interrupt received, stopping...')
        pass
    tb.stop()
    tb.wait()

    # explicitly delete the top block to free resources and make way for next object
    del tb
    time.sleep(1)

GPIO.cleanup()
print("Audio device closed, GPIO cleaned up")