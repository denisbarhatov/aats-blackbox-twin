"""The learning engine: Angluin's L* algorithm, adapted to Mealy machines.

The learner knows only:
  - how to reach the device (host, port),
  - which commands it is allowed to send (the alphabet),
  - that RESET brings the device back to its start state.

It does NOT know the device's states. It finds them by experiment:
  1. Membership queries: reset, send a sequence, record the answers.
  2. Observation table: rows = sequences that reach some state (S),
     columns = test sequences (E). Two rows with different answers must be
     two different states.
  3. When the table is "closed", build a hypothesis model.
  4. Equivalence check: run many random sequences on the device and on the
     hypothesis. A mismatch is a counterexample; its suffixes become new
     columns and learning continues.

Run alone:  python learner.py --port 9001 --out out/model.json
"""

import argparse
import random
import time

from common import DeviceClient
from model import MealyModel

DEFAULT_ALPHABET = ["ON", "OFF", "STATUS", "PING"]


class MembershipOracle:
    """Answers "what does the device reply to this sequence?" with a cache."""

    def __init__(self, client):
        self.client = client
        self.cache = {(): ()}
        self.device_runs = 0

    def query(self, word):
        word = tuple(word)
        if word in self.cache:
            return self.cache[word]
        outs = self.client.run(word)
        self.device_runs += 1
        # The device is deterministic from RESET, so every prefix is known too.
        for i in range(1, len(word) + 1):
            self.cache.setdefault(word[:i], outs[:i])
        return outs


def find_counterexample(hyp, mq, alphabet, rng, n_tests, max_len):
    for _ in range(n_tests):
        word = tuple(rng.choice(alphabet) for _ in range(rng.randint(1, max_len)))
        real, guess = mq.query(word), hyp.run(word)
        if real != guess:
            for i, (r, g) in enumerate(zip(real, guess)):
                if r != g:
                    return word[: i + 1]
    return None


def learn(client, alphabet=DEFAULT_ALPHABET, rng=None, log=print,
          eq_tests=200, eq_max_len=12, max_rounds=20):
    rng = rng or random.Random(0)
    started = time.time()
    mq = MembershipOracle(client)
    reset_out = client.reset()
    A = list(alphabet)
    S = [()]                    # access sequences, one per discovered state
    E = [(a,) for a in A]       # distinguishing test sequences

    def cell(prefix, suffix):
        return mq.query(prefix + suffix)[len(prefix):]

    def row(prefix):
        return tuple(cell(prefix, e) for e in E)

    def close_table():
        changed = True
        while changed:
            changed = False
            known = {row(s) for s in S}
            for s in list(S):
                for a in A:
                    if row(s + (a,)) not in known:
                        S.append(s + (a,))
                        log(f"    new state found: reached by [{' '.join(s + (a,))}]")
                        changed = True
                        break
                if changed:
                    break

    def build_hypothesis():
        names = {}
        for s in S:
            names.setdefault(row(s), f"s{len(names)}")
        trans = {}
        for s in S:
            st = names[row(s)]
            trans[st] = {a: [cell(s, (a,))[0], names[row(s + (a,))]] for a in A}
        # Display only: label each state by its STATUS answer, if STATUS exists.
        hints = {st: trans[st]["STATUS"][0] for st in trans} if "STATUS" in A else {}
        access = {names[row(s)]: list(s) for s in S}
        return MealyModel("s0", trans, A, "RESET", reset_out, hints), access

    rounds, counterexamples, eq_runs = 0, [], 0
    while True:
        rounds += 1
        log(f"  round {rounds}: filling the observation table")
        close_table()
        hyp, access = build_hypothesis()
        log(f"  round {rounds}: hypothesis has {len(hyp.states)} states, "
            f"checking it with {eq_tests} random sequences")
        before = mq.device_runs
        cex = find_counterexample(hyp, mq, A, rng, eq_tests, eq_max_len)
        eq_runs += mq.device_runs - before
        if cex is None:
            log(f"  round {rounds}: no counterexample found -> model accepted")
            break
        counterexamples.append(list(cex))
        log(f"  round {rounds}: counterexample [{' '.join(cex)}] -> refining")
        for i in range(len(cex)):
            if cex[i:] not in E:
                E.append(cex[i:])
        if rounds >= max_rounds:
            log("  stopped: too many rounds")
            break

    stats = {
        "states": len(hyp.states),
        "rounds": rounds,
        "counterexamples": counterexamples,
        "device_runs": mq.device_runs,
        "device_runs_table": mq.device_runs - eq_runs,
        "device_runs_check": eq_runs,
        "commands_sent": client.commands_sent,
        "seconds": round(time.time() - started, 2),
        "access_sequences": access,
        "table_rows": len(S),
        "table_columns": len(E),
    }
    return hyp, stats, set(mq.cache)


def main():
    ap = argparse.ArgumentParser(description="Learn a device's behavior over TCP")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9001)
    ap.add_argument("--alphabet", default=",".join(DEFAULT_ALPHABET))
    ap.add_argument("--out", default="model.json")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    client = DeviceClient(args.host, args.port)
    model, stats, _ = learn(client, args.alphabet.split(","), random.Random(args.seed))
    model.save(args.out)
    print(f"saved {args.out}: {stats['states']} states, {stats['device_runs']} device runs")


if __name__ == "__main__":
    main()
