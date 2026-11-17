"""The digital twin: a TCP server that behaves according to model.json.

It speaks the same protocol as the device, so any client can be pointed at
the twin instead of the device just by changing the port.

Run:  python twin.py --model out/model.json --port 9002
      python twin.py --model out/model.json --port 9002 --fault-rate 0.2
"""

import argparse
import random
import threading

from common import serve_forever
from model import MealyModel


class TwinDevice:
    def __init__(self, model, fault_rate=0.0, seed=None, verbose=False):
        self.model = model
        self.state = model.initial
        self.fault_rate = fault_rate
        self.rng = random.Random(seed)
        self.verbose = verbose
        self.lock = threading.Lock()

    def step(self, cmd):
        with self.lock:
            if cmd == self.model.reset_cmd:
                self.state = self.model.initial
                out = self.model.reset_out
            elif self.fault_rate and self.rng.random() < self.fault_rate:
                out = "ERR_INJECTED"   # fault simulation: only on the twin
            else:
                out, self.state = self.model.step(self.state, cmd)
            if self.verbose:
                print(f"  {cmd:<7} -> {out:<12} (twin state {self.state})", flush=True)
            return out


def main():
    ap = argparse.ArgumentParser(description="Run the digital twin")
    ap.add_argument("--model", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9002)
    ap.add_argument("--fault-rate", type=float, default=0.0,
                    help="share of commands answered with ERR_INJECTED (0-1)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    model = MealyModel.load(args.model)
    serve_forever(TwinDevice(model, args.fault_rate, verbose=args.verbose),
                  args.host, args.port, "twin")


if __name__ == "__main__":
    main()
