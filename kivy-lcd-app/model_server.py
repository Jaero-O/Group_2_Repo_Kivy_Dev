"""
model_server.py
===============
Persistent model server — runs once in Python 3.10 as a background process.
Loads U2Net (rembg) and ONNX classifier into memory ONCE, then listens on a
Unix socket for scan requests from the Kivy app.

Start this from your launch script BEFORE starting the Kivy app:
    /path/to/python3.10 model_server.py --model /path/to/model.onnx

Protocol (newline-delimited JSON):
  Request:  {"action": "classify", "image_path": "/abs/path/to/leaf.png"}
  Request:  {"action": "remove_bg", "input_path": "/abs/path/in.png", "output_path": "/abs/path/out.png"}
  Request:  {"action": "ping"}
  Request:  {"action": "shutdown"}
  Response: {"status": "ok", ...result fields...}
  Response: {"status": "error", "message": "..."}
"""

import os
import sys
import json
import socket
import argparse
import traceback
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps

# Suppress noisy logs
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "4"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

SOCKET_PATH = "/tmp/mangofy_model_server.sock"

# ============================================================
# MODEL LOADER
# ============================================================
class ModelServer:
    def __init__(self, model_path: str):
        print("[ModelServer] Starting up...", flush=True)

        print("[ModelServer] Loading U2Net (rembg) — this takes ~10s first time...", flush=True)
        from rembg.bg import remove as rembg_remove
        from rembg.session_factory import new_session
        self._rembg_remove = rembg_remove
        self.u2net_session = new_session(model_name="u2net")
        print("[ModelServer] ✓ U2Net ready", flush=True)

        print(f"[ModelServer] Loading ONNX model: {model_path}", flush=True)
        import onnxruntime as ort
        from torchvision import transforms

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.ort_session = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"]
        )
        self.input_name = self.ort_session.get_inputs()[0].name

        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225])
        ])
        print("[ModelServer] ✓ ONNX classifier ready", flush=True)
        print("[ModelServer] ✓ All models loaded. Listening for requests...", flush=True)

    # ----------------------------------------------------------
    # ACTION: remove_bg
    # ----------------------------------------------------------
    def remove_bg(self, input_path: str, output_path: str) -> dict:
        img_pil = Image.open(input_path)
        img_no_bg = self._rembg_remove(img_pil, session=self.u2net_session)
        img_no_bg = img_no_bg.convert("RGBA")
        background = Image.new("RGB", img_no_bg.size, (255, 255, 255))
        background.paste(img_no_bg, mask=img_no_bg.split()[3])
        background.save(output_path)
        return {"status": "ok", "output_path": output_path}

    # ----------------------------------------------------------
    # ACTION: classify
    # ----------------------------------------------------------
    def classify(self, image_path: str) -> dict:
        CLASS_NAMES = [
            "Anthracnose", "Bacterial Canker", "Cutting Weevil",
            "Die Back", "Gall Midge", "Healthy",
            "Powdery Mildew", "Sooty Mould"
        ]
        img = Image.open(image_path).convert("RGB")
        input_tensor = self.preprocess(img).unsqueeze(0).numpy()
        outputs = self.ort_session.run(None, {self.input_name: input_tensor})
        logits = outputs[0][0]
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        best_idx = int(np.argmax(probs))
        return {
            "status": "ok",
            "class": CLASS_NAMES[best_idx],
            "class_index": best_idx,
            "confidence": float(probs[best_idx]),
            "probabilities": {
                CLASS_NAMES[i]: float(probs[i]) for i in range(len(CLASS_NAMES))
            }
        }

# ============================================================
# SOCKET SERVER
# ============================================================
def handle_client(conn, server: ModelServer):
    """Handle one request/response on an accepted connection."""
    try:
        data = b""
        while not data.endswith(b"\n"):
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk

        if not data.strip():
            return False  # empty / disconnected

        request = json.loads(data.decode("utf-8").strip())
        action = request.get("action")

        if action == "ping":
            response = {"status": "ok", "message": "pong"}

        elif action == "remove_bg":
            response = server.remove_bg(
                request["input_path"],
                request["output_path"]
            )

        elif action == "classify":
            response = server.classify(request["image_path"])

        elif action == "shutdown":
            response = {"status": "ok", "message": "shutting down"}
            conn.sendall((json.dumps(response) + "\n").encode())
            conn.close()
            return True  # Signal to stop server loop

        else:
            response = {"status": "error", "message": f"Unknown action: {action}"}

        conn.sendall((json.dumps(response) + "\n").encode())

    except Exception as e:
        err = {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
        try:
            conn.sendall((json.dumps(err) + "\n").encode())
        except:
            pass
    finally:
        conn.close()

    return False  # Keep running


def run_server(model_path: str):
    server = ModelServer(model_path)

    # Clean up stale socket
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o777)
    sock.listen(5)

    print(f"[ModelServer] Listening on {SOCKET_PATH}", flush=True)

    # Write a ready file so the Kivy app knows models are loaded
    ready_path = SOCKET_PATH + ".ready"
    Path(ready_path).write_text("ready")

    try:
        while True:
            conn, _ = sock.accept()
            should_stop = handle_client(conn, server)
            if should_stop:
                print("[ModelServer] Shutdown requested.", flush=True)
                break
    finally:
        sock.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        if os.path.exists(ready_path):
            os.unlink(ready_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to .onnx model file")
    args = parser.parse_args()
    run_server(args.model)
