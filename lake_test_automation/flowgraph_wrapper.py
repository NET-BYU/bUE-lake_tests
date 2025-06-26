import yaml
from lora_tu_rd import lora_tu_rd  # Import the GRC-generated class

def format_params(params):
    # Example: ensure sync_word is always a list
    for section in ['tx', 'rx']:
        if not isinstance(params[section]['sync_word'], list):
            params[section]['sync_word'] = [params[section]['sync_word']]
    return params

with open('auto_config.yaml') as f:
    config = yaml.safe_load(f)
params = format_params(config['parameters'])

tb = lora_tu_rd(
    tx_bw=params['tx']['bw'],
    tx_cr=params['tx']['cr'],
    tx_sf=params['tx']['sf'],
    tx_sync_word=params['tx']['sync_word'],
    rx_bw=params['rx']['bw'],
    rx_cr=params['rx']['cr'],
    rx_sf=params['rx']['sf'],
    rx_sync_word=params['rx']['sync_word'],
    # ...add other parameters as needed
)

tb.start()
try:
    # Run for 10 seconds
    import time
    time.sleep(10)
finally:
    tb.stop()
    tb.wait()