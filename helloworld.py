import sys
import time

if __name__ == "__main__":

    for i in range(int(sys.argv[1])):
        print(f"{sys.argv[2]}", flush=True)
        time.sleep(10)