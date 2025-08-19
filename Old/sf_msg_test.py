import sys
import time
import signal
import os

pid = os.getpid()
termination_file = f"/tmp/terminate_{pid}.flag"

# Global flag for graceful termination


if __name__ == "__main__":
    sf = int(sys.argv[1])
    message = sys.argv[2]
    try:
        print(f"Spreading Factor: {sf}")
        print(f"Message: {message}")

    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    finally:
        print("Finally!")
