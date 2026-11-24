# How to work with BlackBox Twin

This guide explains how to install, run, test and extend the project. For *what* the project is and *why* it works, read [docs/BlackBox_Twin_Project_Report.docx](docs/BlackBox_Twin_Project_Report.docx).

## Contents

1. [What you need](#1-what-you-need)
2. [Get the code](#2-get-the-code)
3. [Run the full demo](#3-run-the-full-demo)
4. [Run the automated test](#4-run-the-automated-test)
5. [Run each part by hand](#5-run-each-part-by-hand)
6. [Try your own hidden device](#6-try-your-own-hidden-device)
7. [Project layout](#7-project-layout)
8. [Troubleshooting](#8-troubleshooting)
9. [Next step: AWS IoT Core](#9-next-step-aws-iot-core)

---

## 1. What you need

| Tool | Version | Check with |
|---|---|---|
| Python | 3.10 or newer | `python --version` |
| Git | any | `git --version` |
| A web browser | any | to open the report |

No `pip install` is needed. The POC uses only the Python standard library.

On Windows, if `python` is not found, try `py` instead (for example `py run_demo.py`).

## 2. Get the code

```bash
git clone https://github.com/denisbarhatov/aats-blackbox-twin.git
```
```bash
cd aats-blackbox-twin/poc
```

## 3. Run the full demo

```bash
python run_demo.py
```

For a live presentation, stop between steps and press Enter to continue:

```bash
python run_demo.py --pause
```

### What happens

| Step | What you see |
|---|---|
| 1. Start the hidden device | The simulated ESP32 starts as a separate process on port 9001 |
| 2. Learn | The learner finds the states one by one: `[ON]`, `[ON ON]`, `[ON ON ON]` |
| 3. Twin | The model is saved to `out/model.json` and the twin starts on port 9002 |
| 4. Validate | 300 new sequences: twin vs device vs Record & Replay |
| 5. Swap | The same app talks to the device, then to the twin, side by side |
| 6. Report | `out/report.html` is written |

### Results to expect

```text
learned 4 states ... using 203 experiments
twin            : 100.0% sequences
record & replay :  27.3% sequences
```

### Output files (in `poc/out/`)

| File | What it is |
|---|---|
| `report.html` | Open in a browser: state graph, results, failure examples. The graph needs internet; the tables work offline |
| `model.json` | The learned model: states, transitions, answers |
| `results.json` | All numbers from the run |

`poc/out/` is regenerated on every run and is not committed to Git.

### Demo options

| Option | Default | Meaning |
|---|---|---|
| `--pause` | off | Wait for Enter between steps |
| `--tests N` | 300 | How many new sequences to validate with |
| `--seed N` | 7 | Random seed (same seed = same run) |
| `--latency-ms N` | 0 | Fake network delay on the device, to make learning visible |
| `--device-port N` | 9001 | Port of the hidden device |
| `--twin-port N` | 9002 | Port of the twin |
| `--out DIR` | `poc/out` | Where to write the results |

## 4. Run the automated test

From the `poc` folder:

```bash
python -m unittest test_poc -v
```

It learns the hidden device, checks that 4 states were found, that the twin matches 100% of new sequences, and that Record & Replay scores lower. Expected output ends with `OK`.

## 5. Run each part by hand

This shows that the parts are separate programs that only talk over the network. Open **four terminals**, all in the `poc` folder.

**Terminal 1: the hidden device** (`--verbose` prints every command it receives)

```bash
python device_sim.py --port 9001 --verbose
```

**Terminal 2: learn it** (creates `out/model.json`)

```bash
python learner.py --port 9001 --out out/model.json
```

**Terminal 3: start the twin from the learned model**

```bash
python twin.py --model out/model.json --port 9002 --verbose
```

**Terminal 4: the factory app, first against the device, then against the twin**

```bash
python led_app.py --port 9001
```
```bash
python led_app.py --port 9002
```

Both runs should print the same answers.

**Fault simulation:** restart the twin so that 20% of commands fail on purpose. This never touches the real device.

```bash
python twin.py --model out/model.json --port 9002 --fault-rate 0.2
```

Stop any server with `Ctrl+C`.

## 6. Try your own hidden device

This is the "generality test": a different device should be learned **without changing the learner**.

1. Open `poc/device_sim.py`.
2. Change `HIDDEN_TABLE`. Each state maps each command to `(answer, next state)`. For example, make the device lock after **two** `ON`s instead of three, or add a new state.
3. Run `python run_demo.py` again.

The learner, twin and validator are not changed. The report shows the new state graph.

Rules:
- Every state must define all commands in the alphabet (`ON`, `OFF`, `STATUS`, `PING`).
- If you add a **new command**, also add it to `DEFAULT_ALPHABET` in `learner.py`. That list is the "allowed commands" the learner is told about.
- `RESET` must always return to the start state.

## 7. Project layout

```text
aats-blackbox-twin/
├── README.md                  Project overview
├── INSTRUCTIONS.md            This file
├── BLACKBOX_TWIN_CONTEXT.md   Full project context (idea, risks, open questions)
├── docs/
│   ├── BlackBox_Twin_Project_Report.docx   What we built, what works, how it works
│   ├── SIMPLE_EXPLANATION.md                Plain-language explanation (Hebrew)
│   └── POC_PLAN.md                          ESP32 + AWS IoT Core plan (Hebrew)
├── poc/
│   ├── run_demo.py            One command: runs everything
│   ├── device_sim.py          The hidden device (black box)
│   ├── learner.py             L* learning engine
│   ├── model.py               Learned model + model.json format
│   ├── twin.py                The twin server
│   ├── baseline.py            Record & Replay baseline
│   ├── validator.py           Differential testing
│   ├── led_app.py             Factory app (device or twin)
│   ├── report.py              HTML report
│   └── test_poc.py            Automated test
└── presentation/
    ├── BlackBox_Twin_POC.pdf  The presentation
    ├── BlackBox_Twin_POC.html Same, as a web page
    └── source/                Slide sources and speaker notes
```

### How the parts connect

```text
device_sim.py  ◄──TCP──  learner.py  ──►  out/model.json  ──►  twin.py  ◄──TCP──  led_app.py
     ▲                                                            ▲
     └────────────────────── validator.py ────────────────────────┘
```

The protocol is one line of text per command and one line per answer, for example `ON` → `OK`. Every experiment starts with `RESET`.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Use `py` (Windows) or `python3` (macOS / Linux) |
| `Address already in use` or `nothing is listening on 127.0.0.1:9001` | Another program uses the port. Run with `--device-port 9101 --twin-port 9102` |
| A previous demo is still running | Close its terminal, or end the leftover `python` processes |
| The report shows tables but no state graph | The graph library loads from the internet. Tables work offline |

## 9. Next step: AWS IoT Core

The MVP moves the device connection to **AWS IoT Core** with **MQTT**. Only the transport changes; the learner, twin logic and validator stay the same. Full explanation: section 9 of the project report and [docs/POC_PLAN.md](docs/POC_PLAN.md).

### The command contract

| Topic | Direction | Message |
|---|---|---|
| `bbt/esp32-01/cmd` | cloud → device | `{"id": 17, "cmd": "ON"}` |
| `bbt/esp32-01/resp` | device → cloud | `{"id": 17, "out": "WARN"}` |

The `id` links each answer to its command.

### Setup in the AWS console

1. Pick one region (for example `eu-central-1`) and create a **budget alert** under Billing → Budgets.
2. **IoT Core → Manage → Things → Create things** → name `bbt-esp32-01` → **Auto-generate a new certificate**.
3. **Download all three files right away:** the device certificate, the private key and Amazon Root CA 1. The private key cannot be downloaded again.
4. **IoT Core → Security → Policies → Create** a policy that lets the device connect as `bbt-esp32-01`, subscribe to and receive `bbt/esp32-01/cmd`, and publish to `bbt/esp32-01/resp` (the full JSON is in section 3 of [docs/POC_PLAN.md](docs/POC_PLAN.md) and in the project report).
5. Attach the policy to the certificate.
6. Copy the endpoint from **IoT Core → Settings → Device data endpoint**.
7. Test with **IoT Core → MQTT test client**: subscribe to `bbt/esp32-01/#`, then publish `{"id": 1, "cmd": "ON"}` to `bbt/esp32-01/cmd`.

### Security

- **Never commit certificate or key files.** They are the device's password. `.gitignore` blocks `*.pem`, `*.key`, `*.crt` and a `certs/` folder; keep them there.
- This repository is public. Do not put AWS account IDs, endpoints or keys in committed files. Use environment variables or a local config file that is ignored.
