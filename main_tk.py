import sys
import time
from datetime import datetime
from enum import Enum, auto

from loguru import logger
from rich.console import Console

from base_station_main import Base_Station_Main
from tker import BaseStationDashboard

class Command(Enum):
    REFRESH = 0
    TEST = auto()
    DISTANCE = auto()
    DISCONNECT = auto()
    CANCEL = auto()
    EXIT = auto()

console = Console()

def send_test(base_station, bue_test, start_time, bue_params):
    """Send test command to selected bUEs."""
    # Convert datetime to Unix timestamp
    import time as time_module
    from datetime import datetime, date

    if isinstance(start_time, datetime):
        time_part = start_time.time()
    else:
        time_part = start_time
    
    # Combine today's date with the selected time
    today = date.today()
    full_datetime = datetime.combine(today, time_part)
    unix_timestamp = int(full_datetime.timestamp())
    
    for bue in bue_test.keys():
        if not hasattr(base_station, 'testing_bues'):
            base_station.testing_bues = []
        base_station.ota.send_ota_message(bue, f"TEST-{bue_test[int(bue)]}-{unix_timestamp}-{bue_params[bue]}")



if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    logger.info(f"This marks the start of the base station service at {start_time}")

    try:
        base_station = Base_Station_Main(yaml_str="config_base.yaml")
        base_station.tick_enabled = True

        # dashboard = BaseStationDashboard(base_station)
        # dashboard.mainloop()

        # from gui import Gui
        from agent_gui import Gui
        GUI = Gui(base_station)
        GUI.mainloop()

        while not base_station.EXIT:
            time.sleep(0.2)

        base_station.__del__()

    except KeyboardInterrupt:
        logger.info("Exiting the Base Station service")
        if 'base_station' in locals() and base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        sys.exit(0)