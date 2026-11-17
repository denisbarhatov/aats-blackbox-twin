"""The "black box": a simulated ESP32 LED controller.

The learner never imports this file. It only talks to it over TCP, exactly
like it would talk to the real ESP32. The table below is the hidden truth we
use afterwards to check whether the learner found the right behavior.

Run:  python device_sim.py --port 9001
"""

import argparse
import threading
import time

from common import serve_forever

# state -> command -> (response, next state)
HIDDEN_TABLE = {
    "OFF": {
        "ON": ("OK", "ON"),
        "OFF": ("OK", "OFF"),
        "STATUS": ("LED_OFF", "OFF"),
        "PING": ("PONG", "OFF"),
    },
    "ON": {
        "ON": ("WARN", "WARN"),        # second ON in a row: overheating warning
        "OFF": ("OK", "OFF"),
        "STATUS": ("LED_ON", "ON"),
        "PING": ("PONG", "ON"),
    },
    "WARN": {
        "ON": ("ERR", "FAULT"),        # third ON in a row: the device locks up
        "OFF": ("OK", "OFF"),
        "STATUS": ("LED_ON", "WARN"),  # looks exactly like ON from the outside
        "PING": ("PONG", "WARN"),
    },
    "FAULT": {
        "ON": ("ERR", "FAULT"),
        "OFF": ("ERR", "FAULT"),
        "STATUS": ("FAULT", "FAULT"),
        "PING": ("ERR", "FAULT"),
    },
}
START_STATE = "OFF"


class HiddenDevice:
    def __init__(self, latency_ms=0, verbose=False):
        self.state = START_STATE
        self.latency = latency_ms / 1000.0
        self.verbose = verbose
        self.lock = threading.Lock()

    def step(self, cmd):
        if self.latency:
            time.sleep(self.latency)
        with self.lock:
            if cmd == "RESET":
                self.state = START_STATE
                out = "RESET_OK"
            elif cmd in HIDDEN_TABLE[self.state]:
                out, self.state = HIDDEN_TABLE[self.state][cmd]
            else:
                out = "ERR_UNKNOWN"
            if self.verbose:
                print(f"  {cmd:<7} -> {out:<9} (now {self.state})", flush=True)
            return out


def main():
    ap = argparse.ArgumentParser(description="Hidden ESP32 LED device simulator")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9001)
    ap.add_argument("--latency-ms", type=int, default=0, help="fake network delay")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    serve_forever(HiddenDevice(args.latency_ms, args.verbose), args.host, args.port, "device")


if __name__ == "__main__":
    main()
