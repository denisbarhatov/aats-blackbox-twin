"""BlackBox Twin POC - the whole demo in one command.

    python run_demo.py            # run everything
    python run_demo.py --pause    # stop between steps (for a live presentation)

Steps:
  1. start the hidden device (a separate process, reachable only over TCP)
  2. learn its behavior with L*
  3. save model.json and start the twin from it
  4. compare twin and Record & Replay against the device on NEW sequences
  5. point the factory app at the device, then at the twin
  6. write out/report.html
"""

import argparse
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from baseline import RecordReplay, record_sessions  # noqa: E402
from common import DeviceClient, wait_for_port  # noqa: E402
from learner import DEFAULT_ALPHABET, learn  # noqa: E402
from led_app import run_scenario  # noqa: E402
from report import write_report  # noqa: E402
from validator import coverage, evaluate, make_tests  # noqa: E402

HOST = "127.0.0.1"


def start(script, *args):
    return subprocess.Popen([sys.executable, os.path.join(HERE, script), *args],
                            stdout=subprocess.DEVNULL)


def title(n, text, pause):
    if pause:
        input("\n[Enter] to continue...")
    print(f"\n=== [{n}/6] {text} " + "=" * max(0, 56 - len(text)))


def main():
    ap = argparse.ArgumentParser(description="BlackBox Twin POC demo")
    ap.add_argument("--device-port", type=int, default=9001)
    ap.add_argument("--twin-port", type=int, default=9002)
    ap.add_argument("--tests", type=int, default=300, help="new sequences to validate with")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--latency-ms", type=int, default=0, help="fake network delay on the device")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--pause", action="store_true", help="wait for Enter between steps")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    model_path = os.path.join(args.out, "model.json")
    procs = []

    print("BlackBox Twin - Proof of Concept")
    print("Learn a device from the outside, build a twin, prove it matches.")
    try:
        title(1, "Start the hidden device (black box)", args.pause)
        procs.append(start("device_sim.py", "--port", str(args.device_port),
                           "--latency-ms", str(args.latency_ms)))
        wait_for_port(HOST, args.device_port)
        print(f"  device is running on {HOST}:{args.device_port} (separate process)")
        print(f"  the learner knows only: the address, the allowed commands "
              f"{DEFAULT_ALPHABET} and RESET")

        title(2, "Learn the behavior (L* active learning)", args.pause)
        client = DeviceClient(HOST, args.device_port)
        model, stats, words_seen = learn(client, DEFAULT_ALPHABET, random.Random(args.seed))
        print(f"\n  learned {stats['states']} states in {stats['seconds']}s "
              f"using {stats['device_runs']} experiments ({stats['commands_sent']} commands)")
        for st in model.states:
            row = model.transitions[st]
            moves = ", ".join(f"{c}/{o}->{n}" for c, (o, n) in row.items())
            print(f"  {st} [{model.hints.get(st, '')}]: {moves}")

        title(3, "Save the model and start the twin", args.pause)
        model.save(model_path)
        print(f"  model saved: {model_path}")
        procs.append(start("twin.py", "--model", model_path, "--port", str(args.twin_port)))
        wait_for_port(HOST, args.twin_port)
        print(f"  twin is running on {HOST}:{args.twin_port} (loaded from model.json)")

        title(4, "Validate on NEW sequences: device vs twin vs baseline", args.pause)
        rng = random.Random(args.seed + 1000)
        n_record = stats["device_runs"]  # same data budget as the learner
        traces = record_sessions(client, DEFAULT_ALPHABET, rng, n_record)
        baseline = RecordReplay(traces)
        print(f"  Record & Replay baseline built from {n_record} recorded sessions")
        tests = make_tests(DEFAULT_ALPHABET, rng, args.tests, exclude=words_seen)
        truth = [client.run(w) for w in tests]
        twin_client = DeviceClient(HOST, args.twin_port)
        twin_res = evaluate(twin_client.run, tests, truth)
        base_res = evaluate(baseline.run, tests, truth)
        cov = coverage(model, tests)
        print(f"  {len(tests)} sequences the learner never sent (length 3-15)")
        print(f"  twin            : {twin_res['seq_pct']:5.1f}% sequences, "
              f"{twin_res['step_pct']:5.1f}% single answers")
        print(f"  record & replay : {base_res['seq_pct']:5.1f}% sequences, "
              f"{base_res['step_pct']:5.1f}% single answers")
        print(f"  transitions covered by tests: {cov['covered']}/{cov['total']}")
        if base_res["failures"]:
            f = base_res["failures"][0]
            print(f"  example where replay fails: {' '.join(f['input'])}")
            print(f"    device: {' '.join(f['expected'])}")
            print(f"    replay: {' '.join(f['got'])}")
        twin_client.close()
        client.close()

        title(5, "Swap: the factory app talks to the device, then the twin", args.pause)
        dev_run = run_scenario(HOST, args.device_port)
        twin_run = run_scenario(HOST, args.twin_port)
        print(f"  {'command':<8} {'device':<10} {'twin':<10}")
        for (cmd, a), (_, b) in zip(dev_run, twin_run):
            print(f"  {cmd:<8} {a:<10} {b:<10} {'ok' if a == b else 'DIFF'}")

        title(6, "Write the report", args.pause)
        swap = {"device": dev_run, "twin": twin_run,
                "device_port": args.device_port, "twin_port": args.twin_port}
        report_path = os.path.join(args.out, "report.html")
        write_report(report_path, model, stats, twin_res, base_res, cov, swap, n_record)
        with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as f:
            json.dump({"learning": stats, "twin": twin_res, "baseline": base_res,
                       "coverage": cov}, f, indent=2)
        print(f"  report: {report_path}")
        print("\nDone.")
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
