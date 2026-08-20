import time
import requests
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

try:
    import dotenv
except ImportError:
    from unittest.mock import MagicMock
    sys.modules['dotenv'] = MagicMock()

import timelapse_stacking

# Setup a dummy server to mock Immich API
class MockImmichHandler(BaseHTTPRequestHandler):
    def do_DELETE(self):
        time.sleep(0.01) # Simulate network/processing delay
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/albums':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b"[]")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress HTTP server logging during benchmark

def run_server():
    server = HTTPServer(('localhost', 8283), MockImmichHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Override settings
timelapse_stacking.BASE_URL = "http://localhost:8283"
timelapse_stacking.LOG_PATH = str(current_dir / "timelapse_stacking_benchmark_run.json")

# Create fake log
run_log = [
    {"stack_id": f"stack_{i}", "asset_ids": [], "date": "2023-01-01", "frames": 10}
    for i in range(100)
]
with open(timelapse_stacking.LOG_PATH, "w") as f:
    json.dump(run_log, f)

try:
    start = time.time()
    timelapse_stacking.unstack_last_run()
    end = time.time()
    print(f"Time taken: {end - start:.2f} seconds")
finally:
    if os.path.exists(timelapse_stacking.LOG_PATH):
        os.remove(timelapse_stacking.LOG_PATH)
