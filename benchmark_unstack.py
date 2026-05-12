import time
import requests
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util

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

def run_server():
    server = HTTPServer(('localhost', 8283), MockImmichHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Load timelapse_stacking.py module
import sys
sys.path.append(os.path.abspath("python/immich-api"))
import timelapse_stacking

# Override settings
timelapse_stacking.BASE_URL = "http://localhost:8283"
timelapse_stacking.LOG_PATH = "timelapse_stacking_last_run.json"

# Create fake log
run_log = [
    {"stack_id": f"stack_{i}", "asset_ids": [], "date": "2023-01-01", "frames": 10}
    for i in range(100)
]
with open(timelapse_stacking.LOG_PATH, "w") as f:
    json.dump(run_log, f)

# Original time
start = time.time()
timelapse_stacking.unstack_last_run()
end = time.time()

print(f"Time taken: {end - start:.2f} seconds")

# Clean up log
if os.path.exists(timelapse_stacking.LOG_PATH):
    os.remove(timelapse_stacking.LOG_PATH)
