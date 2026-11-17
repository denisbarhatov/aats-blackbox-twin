"""Differential testing: send the same NEW sequences to the device and to a
candidate (twin or baseline) and measure how often the answers match.
"""

# Hand-picked scenarios that need the hidden states to get right.
SCENARIOS = [
    ("ON", "ON", "STATUS"),
    ("ON", "ON", "ON", "STATUS"),
    ("ON", "ON", "ON", "OFF", "PING"),
    ("ON", "OFF", "ON", "ON", "OFF", "ON"),
    ("ON", "ON", "OFF", "ON", "ON", "ON", "STATUS", "PING"),
]


def make_tests(alphabet, rng, n, exclude, min_len=3, max_len=15):
    """Random sequences the learner never sent, plus the scenarios above."""
    tests = [s for s in SCENARIOS if all(c in alphabet for c in s)]
    seen = set(tests) | set(exclude)
    attempts = 0
    while len(tests) < n and attempts < n * 50:
        attempts += 1
        word = tuple(rng.choice(alphabet) for _ in range(rng.randint(min_len, max_len)))
        if word not in seen:
            seen.add(word)
            tests.append(word)
    return tests


def evaluate(run, tests, truth, keep_failures=6):
    seq_ok = step_ok = step_total = 0
    failures = []
    for word, expected in zip(tests, truth):
        got = run(word)
        same = sum(1 for a, b in zip(expected, got) if a == b)
        step_ok += same
        step_total += len(word)
        if got == expected:
            seq_ok += 1
        elif len(failures) < keep_failures:
            failures.append({"input": list(word), "expected": list(expected), "got": list(got)})
    return {
        "seq_ok": seq_ok,
        "seq_total": len(tests),
        "seq_pct": round(100.0 * seq_ok / max(1, len(tests)), 1),
        "step_ok": step_ok,
        "step_total": step_total,
        "step_pct": round(100.0 * step_ok / max(1, step_total), 1),
        "failures": failures,
    }


def coverage(model, tests):
    """Which learned transitions the test set actually exercised."""
    used = set()
    for word in tests:
        state = model.initial
        for cmd in word:
            used.add((state, cmd))
            _, state = model.step(state, cmd)
    total = sum(len(t) for t in model.transitions.values())
    return {"covered": len(used), "total": total,
            "pct": round(100.0 * len(used) / max(1, total), 1)}
