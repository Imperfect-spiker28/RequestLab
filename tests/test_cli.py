from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from requestlab.cli import main


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def test_cli_run_json_output(tmp_path: Path, capsys) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OkHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        suite_path = tmp_path / "suite.json"
        suite_path.write_text(
            json.dumps(
                {
                    "base_url": f"http://127.0.0.1:{port}",
                    "cases": [{"name": "OK", "method": "GET", "path": "/", "expect": {"status": 200, "json": {"ok": True}}}],
                }
            ),
            encoding="utf-8",
        )
        code = main(["run", str(suite_path), "--json"])
        assert code == 0
        report = json.loads(capsys.readouterr().out)
        assert report["ok"] is True
        assert report["passed"] == 1
    finally:
        server.shutdown()
        server.server_close()
