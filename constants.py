from enum import Enum, auto


class State(Enum):
    INIT = auto()
    CONNECT_OTA = auto()
    IDLE = auto()
    WAIT_FOR_START = auto()
    UTW_TEST = auto()
    TEST_CLEANUP = auto()