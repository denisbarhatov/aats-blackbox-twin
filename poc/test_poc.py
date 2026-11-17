"""End-to-end check: learn the hidden device and confirm the twin matches it.

Run:  python -m unittest test_poc   (from the poc folder)
"""

import os
import random
import socket
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import DeviceClient, _Handler, _Server  # noqa: E402
from device_sim import HIDDEN_TABLE, HiddenDevice  # noqa: E402
from learner import DEFAULT_ALPHABET, learn  # noqa: E402
from validator import evaluate, make_tests  # noqa: E402
from baseline import RecordReplay, record_sessions  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.server = _Server(("127.0.0.1", cls.port), _Handler)
        cls.server.device = HiddenDevice()
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_learns_hidden_machine_and_beats_baseline(self):
        client = DeviceClient("127.0.0.1", self.port)
        model, stats, seen = learn(client, DEFAULT_ALPHABET, random.Random(1), log=lambda *_: None)
        self.assertEqual(stats["states"], len(HIDDEN_TABLE))

        rng = random.Random(2)
        tests = make_tests(DEFAULT_ALPHABET, rng, 200, exclude=seen)
        truth = [client.run(w) for w in tests]
        twin = evaluate(model.run, tests, truth)
        self.assertEqual(twin["seq_pct"], 100.0)

        baseline = RecordReplay(record_sessions(client, DEFAULT_ALPHABET, rng, stats["device_runs"]))
        base = evaluate(baseline.run, tests, truth)
        self.assertLess(base["seq_pct"], twin["seq_pct"])
        client.close()


if __name__ == "__main__":
    unittest.main()
