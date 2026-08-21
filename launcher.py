import os
import sys
import time
import socket
import threading
import webbrowser
import urllib.request
from pathlib import Path

# Redirect stdout/stderr if None (PyInstaller windowed mode noconsole)
class NullWriter:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

# Setup environment for Django
if getattr(sys, 'frozen', False):
    # PyInstaller bundle path
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from core.wsgi import application
from wsgiref.simple_server import make_server, WSGIRequestHandler


class QuietWSGIRequestHandler(WSGIRequestHandler):
    """Custom request handler that silences console logging when running windowed."""
    def log_message(self, format, *args):
        pass


def is_port_in_use(port, host='127.0.0.1'):
    """Checks if a local TCP port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port=8000, max_attempts=10):
    """Finds an available local port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p):
            return p
    return start_port


def wait_for_server(url, timeout=15):
    """Polls the local server until it responds to HTTP requests."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status in (200, 301, 302, 404):
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def run_django_server(host, port):
    """Runs Django WSGI server directly using wsgiref."""
    try:
        httpd = make_server(host, port, application, handler_class=QuietWSGIRequestHandler)
        httpd.serve_forever()
    except Exception as e:
        sys.stderr.write(f"Server error: {e}\n")


def main():
    host = '127.0.0.1'
    port = 8000

    if is_port_in_use(port):
        port = find_available_port(start_port=8001)

    url = f"http://{host}:{port}"

    # Start WSGI server in a background daemon thread
    server_thread = threading.Thread(
        target=run_django_server,
        args=(host, port),
        daemon=True
    )
    server_thread.start()

    # Wait for server readiness and open default browser
    if wait_for_server(url):
        webbrowser.open(url)
    else:
        webbrowser.open(url)

    # Keep main thread running while daemon WSGI server serves requests
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
