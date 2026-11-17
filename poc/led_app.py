"""A tiny "factory app" that controls the LED device.

It only knows a host and a port, so it can be pointed at the real device or at
the twin without any code change. That is the whole point of the twin.

Run:  python led_app.py --port 9001   (device)
      python led_app.py --port 9002   (twin)
"""

import argparse

from common import DeviceClient

SCENARIO = ["STATUS", "ON", "STATUS", "ON", "STATUS", "ON", "STATUS", "OFF", "RESET", "STATUS"]


def run_scenario(host, port, scenario=SCENARIO):
    client = DeviceClient(host, port)
    try:
        client.reset()
        return [(cmd, client.send(cmd)) for cmd in scenario]
    finally:
        client.close()


def main():
    ap = argparse.ArgumentParser(description="Factory app that talks to the LED device")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9001)
    args = ap.parse_args()
    for cmd, out in run_scenario(args.host, args.port):
        print(f"{cmd:<7} -> {out}")


if __name__ == "__main__":
    main()
