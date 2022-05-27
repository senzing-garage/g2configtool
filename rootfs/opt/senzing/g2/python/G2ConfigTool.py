#! /usr/bin/env python3

import signal
import sys
import time


def sigterm_handler(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, sigterm_handler)
signal.signal(signal.SIGINT, sigterm_handler)


def main():
    sleep_time = 3600
    while True:
        print("WARNING: /opt/senzing not attached.")
        time.sleep(sleep_time)


if __name__ == '__main__':
    main()
