from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from requestlab.runner import interpolate_env, run_suite


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            body = json.dumps({"status": "ok", "meta": {"version": 1}}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw) if raw else {}
        auth = self.headers.get("Authorization", "")
        resp = json.dumps({"echo": data, "authorized": auth == "Bearer tok-123"}).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, format: str, *args) -> None:
        return


def test_interpolate_env_recursive() -> None:
    resolved = interpolate_env(
        {"url": "${HOST}/api", "headers": ["Bearer ${TOKEN}"]},
        env={"HOST": "http://localhost:9000", "TOKEN": "abc"},
    )
    assert resolved["url"] == "http://localhost:9000/api"
    assert resolved["headers"] == ["Bearer abc"]


def test_run_suite_against_live_local_server() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        suite = {
            "base_url": f"http://127.0.0.1:{port}",
            "cases": [
                {
                    "name": "Health check",
                    "method": "GET",
                    "path": "/health",
                    "expect": {
                        "status": 200,
                        "max_ms": 2000,
                        "json": {"status": "ok", "meta.version": 1},
                    },
                },
                {
                    "name": "Echo POST with env token",
                    "method": "POST",
                    "path": "/echo",
                    "headers": {"Authorization": "Bearer ${API_TOKEN}"},
                    "body": {"ping": True},
                    "expect": {"status": 201, "json": {"authorized": True, "echo.ping": True}},
                },
            ],
        }
        results = run_suite(suite, env={"API_TOKEN": "tok-123"})
        assert len(results) == 2
        assert all(r.passed for r in results)
    finally:
        server.shutdown()
        server.server_close()
