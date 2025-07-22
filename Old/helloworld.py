import sys
import time
import signal
import os

pid = os.getpid()
termination_file = f"/tmp/terminate_{pid}.flag"

# Global flag for graceful termination



if __name__ == "__main__":
    iterations = int(sys.argv[1])
    message = sys.argv[2]
    try:
        for i in range(iterations):
            print(f"rx msg: {message}", flush=True)
            time.sleep(10)
    
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    finally:
        print("Finally!")
