"""
model_client.py
===============
Drop-in client for the Kivy app (any Python version).
Talks to model_server.py over a Unix socket.

Usage in scan.py / anywhere in Kivy:
    from model_client import ModelClient

    client = ModelClient()
    result = client.classify("/path/to/leaf.png")
    result = client.remove_bg("/path/to/input.png", "/path/to/output.png")
"""

import json
import socket
import os
import time
from pathlib import Path

SOCKET_PATH = "/tmp/mangofy_model_server.sock"
READY_PATH  = SOCKET_PATH + ".ready"


class ModelClientError(Exception):
    pass


class ModelClient:
    def __init__(self, socket_path: str = SOCKET_PATH, timeout: float = 120.0):
        self.socket_path = socket_path
        self.timeout = timeout

    # ----------------------------------------------------------
    # Internal: send one request, get one response
    # ----------------------------------------------------------
    def _send(self, request: dict, timeout: float = None) -> dict:
        """
        Send a request and return the response.
        timeout overrides the instance default for this call only.
        """
        if not os.path.exists(self.socket_path):
            raise ModelClientError(
                f"Model server socket not found at {self.socket_path}. "
                "Is model_server.py running?"
            )

        effective_timeout = timeout if timeout is not None else self.timeout

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(effective_timeout)
            sock.connect(self.socket_path)
            sock.sendall((json.dumps(request) + "\n").encode("utf-8"))

            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            sock.close()

            response = json.loads(data.decode("utf-8").strip())
            if response.get("status") == "error":
                raise ModelClientError(response.get("message", "Unknown server error"))
            return response

        except ModelClientError:
            raise
        except socket.timeout:
            raise ModelClientError(
                f"Request timed out after {effective_timeout}s. "
                "Server may be busy or unresponsive."
            )
        except Exception as e:
            raise ModelClientError(f"Socket communication failed: {e}") from e

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    def ping(self) -> bool:
        """Returns True if the server is alive."""
        try:
            r = self._send({"action": "ping"}, timeout=5.0)
            return r.get("message") == "pong"
        except ModelClientError:
            return False

    def remove_bg(self, input_path: str, output_path: str,
                  timeout: float = 120.0) -> str:
        """
        Remove background from input_path, save result to output_path.
        Returns output_path on success.
        timeout: how long to wait (default 120s — U2Net is slow on first run).
        """
        r = self._send({
            "action":      "remove_bg",
            "input_path":  input_path,
            "output_path": output_path
        }, timeout=timeout)
        return r["output_path"]

    def classify(self, image_path: str, timeout: float = 30.0) -> dict:
        """
        Classify a leaf image.
        Returns dict: {class, class_index, confidence, probabilities}
        """
        r = self._send({
            "action":     "classify",
            "image_path": image_path
        }, timeout=timeout)
        r.pop("status", None)
        return r

    def shutdown_server(self):
        """Gracefully shut down the model server."""
        try:
            self._send({"action": "shutdown"}, timeout=5.0)
        except:
            pass

    # ----------------------------------------------------------
    # Convenience: wait for server to be ready
    # ----------------------------------------------------------
    @staticmethod
    def wait_until_ready(timeout: float = 120.0, poll_interval: float = 1.0) -> bool:
        """
        Block until the model server is ready (or timeout).
        Returns True if ready, False if timed out.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if Path(READY_PATH).exists():
                return True
            time.sleep(poll_interval)
        return False
