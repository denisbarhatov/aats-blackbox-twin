"""Shared pieces: a line-based TCP protocol, a small server helper and a client.

Protocol: the client sends one command per line ("ON\n"), the server answers
one line ("OK\n"). "RESET" always brings the device back to its start state.
"""

import socket
import socketserver
import sys
import time

ENCODING = "ascii"


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        device = self.server.device
        for raw in self.rfile:
            cmd = raw.decode(ENCODING, "replace").strip().upper()
            if not cmd:
                continue
            out = device.step(cmd)
            self.wfile.write((out + "\n").encode(ENCODING))


class _Server(socketserver.ThreadingTCPServer):
    # On Windows SO_REUSEADDR lets two servers share a port, so keep it off there.
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


def serve_forever(device, host, port, name):
    with _Server((host, port), _Handler) as srv:
        srv.device = device
        print(f"[{name}] listening on {host}:{port}", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


class DeviceClient:
    """Talks to a device (real, simulated or twin) over TCP."""

    def __init__(self, host, port, timeout=2.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.rfile = self.sock.makefile("rb")
        self.commands_sent = 0

    def send(self, cmd):
        self.sock.sendall((cmd + "\n").encode(ENCODING))
        line = self.rfile.readline()
        if not line:
            raise ConnectionError("device closed the connection")
        self.commands_sent += 1
        return line.decode(ENCODING, "replace").strip()

    def reset(self):
        return self.send("RESET")

    def run(self, word):
        """Reset, then send every command in `word`. Returns the outputs."""
        self.reset()
        return tuple(self.send(c) for c in word)

    def close(self):
        try:
            self.rfile.close()
            self.sock.close()
        except OSError:
            pass


def wait_for_port(host, port, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"nothing is listening on {host}:{port}")
