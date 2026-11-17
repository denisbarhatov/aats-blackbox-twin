"""The learned behavior model (a Mealy machine) and its JSON file format."""

import json

UNKNOWN_OUT = "ERR_UNKNOWN"


class MealyModel:
    def __init__(self, initial, transitions, alphabet, reset_cmd="RESET",
                 reset_out="RESET_OK", hints=None):
        self.initial = initial
        # state -> command -> [response, next state]
        self.transitions = transitions
        self.alphabet = list(alphabet)
        self.reset_cmd = reset_cmd
        self.reset_out = reset_out
        self.hints = hints or {}

    @property
    def states(self):
        return list(self.transitions)

    def step(self, state, cmd):
        if cmd not in self.transitions[state]:
            return UNKNOWN_OUT, state
        out, nxt = self.transitions[state][cmd]
        return out, nxt

    def run(self, word):
        state, outs = self.initial, []
        for cmd in word:
            out, state = self.step(state, cmd)
            outs.append(out)
        return tuple(outs)

    def to_dict(self):
        return {
            "format": "blackbox-twin/mealy-v1",
            "initial": self.initial,
            "alphabet": self.alphabet,
            "reset": {"cmd": self.reset_cmd, "out": self.reset_out},
            "states": self.states,
            "hints": self.hints,
            "transitions": self.transitions,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d["initial"], d["transitions"], d["alphabet"],
                   d["reset"]["cmd"], d["reset"]["out"], d.get("hints"))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
