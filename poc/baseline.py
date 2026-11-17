"""Baseline to beat: simple Record & Replay.

It records normal sessions with the device and, for each command, replays
the answer it saw most often. It has no idea of states. This is roughly what
a basic recording mock does, and it is what our learned twin is compared to.
"""

from collections import Counter, defaultdict

from model import UNKNOWN_OUT


def record_sessions(client, alphabet, rng, n_sessions, max_len=8):
    traces = []
    for _ in range(n_sessions):
        word = tuple(rng.choice(alphabet) for _ in range(rng.randint(1, max_len)))
        traces.append((word, client.run(word)))
    return traces


class RecordReplay:
    def __init__(self, traces):
        seen = defaultdict(Counter)
        for word, outs in traces:
            for cmd, out in zip(word, outs):
                seen[cmd][out] += 1
        self.table = {cmd: c.most_common(1)[0][0] for cmd, c in seen.items()}

    def run(self, word):
        return tuple(self.table.get(cmd, UNKNOWN_OUT) for cmd in word)
